#!/usr/bin/env python3
"""Convert Miles XMIDI (XMI) to deterministic Standard MIDI Format 0.

OpenAzrael-authored implementation for local user-owned source assets.
No original XMI payload is tracked. Timing uses the XMIDI fixed 120 Hz clock:
60 PPQN at 500000 us/quarter. XMI note durations become explicit Note Offs.
AIL-only CC 110..120 are not forwarded to a normal MIDI synth; loop markers
(116/117) are retained as metadata for the rendered-audio layer.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json

PPQN=60
TEMPO_US_PER_QUARTER=500000
AIL_CC_MIN=110
AIL_CC_MAX=120

def read_vlq(data: bytes,pos: int) -> tuple[int,int]:
    value=0
    for _ in range(5):
        if pos>=len(data): raise ValueError("truncated VLQ")
        b=data[pos];pos+=1
        value=(value<<7)|(b&0x7F)
        if b<0x80:return value,pos
    raise ValueError("VLQ too long")

def write_vlq(value: int) -> bytes:
    if value<0:raise ValueError("negative VLQ")
    parts=[value&0x7F];value>>=7
    while value:
        parts.append(0x80|(value&0x7F));value>>=7
    return bytes(reversed(parts))

def extract_evnt(data: bytes) -> bytes:
    pos=data.find(b"EVNT")
    if pos<0 or pos+8>len(data):raise ValueError("EVNT chunk missing")
    size=int.from_bytes(data[pos+4:pos+8],"big")
    payload=data[pos+8:pos+8+size]
    if len(payload)!=size:raise ValueError("EVNT chunk truncated")
    return payload

def parse_xmi_events(data: bytes):
    evnt=extract_evnt(data)
    pos=0;tick=0;order=0
    events=[];loop_starts={};loops=[];counts={}
    def add(at,kind,*args):
        nonlocal order
        events.append((at,order,kind,args));order+=1
        counts[kind]=counts.get(kind,0)+1
    while pos<len(evnt):
        delay=0
        while pos<len(evnt) and evnt[pos]<0x80:
            delay+=evnt[pos];pos+=1
        tick+=delay
        if pos>=len(evnt):break
        status=evnt[pos];pos+=1
        high=status&0xF0;channel=status&0x0F
        if high in (0x80,0x90,0xA0,0xB0,0xE0):
            if pos+2>len(evnt):raise ValueError("truncated channel event")
            p1,p2=evnt[pos],evnt[pos+1];pos+=2
            if high==0x90 and p2:
                duration,pos=read_vlq(evnt,pos)
                add(tick,"note_on",channel,p1,p2)
                add(tick+duration,"note_off",channel,p1,0)
            elif high==0x90:
                add(tick,"note_off",channel,p1,0)
            elif high==0x80:
                add(tick,"note_off",channel,p1,p2)
            elif high==0xA0:
                add(tick,"poly_pressure",channel,p1,p2)
            elif high==0xB0:
                if AIL_CC_MIN<=p1<=AIL_CC_MAX:
                    counts["ail_cc_stripped"]=counts.get("ail_cc_stripped",0)+1
                    if p1==116:
                        loop_starts[channel]=(tick,p2)
                    elif p1==117 and channel in loop_starts:
                        start,repeat=loop_starts[channel]
                        loops.append({
                            "channel":channel,"start_tick":start,"end_tick":tick,
                            "repeat":repeat,"next_value":p2,
                        })
                else:
                    add(tick,"control_change",channel,p1,p2)
            elif high==0xE0:
                add(tick,"pitch_bend",channel,p1|(p2<<7))
        elif high in (0xC0,0xD0):
            if pos>=len(evnt):raise ValueError("truncated one-byte channel event")
            p1=evnt[pos];pos+=1
            add(tick,"program_change" if high==0xC0 else "channel_pressure",channel,p1)
        elif status==0xFF:
            if pos>=len(evnt):raise ValueError("truncated meta event")
            meta_type=evnt[pos];pos+=1
            length,pos=read_vlq(evnt,pos)
            payload=evnt[pos:pos+length];pos+=length
            if len(payload)!=length:raise ValueError("truncated meta payload")
            if meta_type==0x2F:break
            # XMIDI timing is fixed at 120 Hz; embedded tempo is vestigial.
            if meta_type!=0x51:add(tick,"meta",meta_type,payload)
        elif status in (0xF0,0xF7):
            length,pos=read_vlq(evnt,pos)
            payload=evnt[pos:pos+length];pos+=length
            if len(payload)!=length:raise ValueError("truncated sysex payload")
            add(tick,"sysex",status,payload)
        else:
            raise ValueError(f"unsupported XMIDI status 0x{status:02X}")

    priority={"note_off":0}
    events.sort(key=lambda row:(row[0],priority.get(row[2],1),row[1]))
    end_tick=max([tick]+[row[0] for row in events])
    report={
        "event_counts":counts,
        "end_tick":end_tick,
        "duration_seconds":end_tick/120.0,
        "loop_markers":loops,
        "loop_start_tick":min((r["start_tick"] for r in loops),default=None),
        "loop_end_tick":max((r["end_tick"] for r in loops),default=None),
    }
    return events,report

def event_to_midi(kind,args):
    if kind=="note_on":
        c,n,v=args;return bytes([0x90|c,n,v])
    if kind=="note_off":
        c,n,v=args;return bytes([0x80|c,n,v])
    if kind=="poly_pressure":
        c,n,v=args;return bytes([0xA0|c,n,v])
    if kind=="control_change":
        c,k,v=args;return bytes([0xB0|c,k,v])
    if kind=="program_change":
        c,p=args;return bytes([0xC0|c,p])
    if kind=="channel_pressure":
        c,p=args;return bytes([0xD0|c,p])
    if kind=="pitch_bend":
        c,v=args;return bytes([0xE0|c,v&0x7F,(v>>7)&0x7F])
    if kind=="meta":
        typ,payload=args;return b"\xFF"+bytes([typ])+write_vlq(len(payload))+payload
    if kind=="sysex":
        status,payload=args;return bytes([status])+write_vlq(len(payload))+payload
    raise ValueError(kind)

def convert_xmi_bytes(data: bytes):
    events,report=parse_xmi_events(data)
    track=bytearray()
    # Fixed 120 Hz clock.
    timeline=[(0,-1,"fixed_tempo",(b"\x07\xA1\x20",))]+events
    timeline.sort(key=lambda row:(row[0],row[1] if isinstance(row[1],int) else 0))
    last=0
    for tick,order,kind,args in timeline:
        track+=write_vlq(tick-last)
        if kind=="fixed_tempo":
            track+=b"\xFF\x51\x03"+args[0]
        else:
            track+=event_to_midi(kind,args)
        last=tick
    track+=write_vlq(max(0,report["end_tick"]-last))+b"\xFF\x2F\x00"
    header=b"MThd"+(6).to_bytes(4,"big")+(0).to_bytes(2,"big")+(1).to_bytes(2,"big")+PPQN.to_bytes(2,"big")
    midi=header+b"MTrk"+len(track).to_bytes(4,"big")+bytes(track)
    report=dict(report)
    report.update({
        "schema":"openazrael.xmi_to_midi",
        "version":134,
        "status":"PASS",
        "midi_format":0,
        "ppqn":PPQN,
        "tempo_us_per_quarter":TEMPO_US_PER_QUARTER,
        "clock_hz":120,
        "midi_bytes":len(midi),
        "midi_sha256":hashlib.sha256(midi).hexdigest(),
    })
    return midi,report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xmi",type=Path);ap.add_argument("midi",type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    midi,report=convert_xmi_bytes(args.xmi.read_bytes())
    args.midi.parent.mkdir(parents=True,exist_ok=True);args.midi.write_bytes(midi)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
