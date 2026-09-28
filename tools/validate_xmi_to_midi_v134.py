#!/usr/bin/env python3
"""Source-only tests for OpenAzrael XMIDI conversion."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("xmi",ROOT/"tools/xmi_to_midi_v134.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def chunk(tag,payload):return tag+len(payload).to_bytes(4,"big")+payload+(b"\0" if len(payload)&1 else b"")
def vlq(v):
    return m.write_vlq(v)
# Synthetic source-safe EVNT: program, note with duration, delay, loop markers, EOT.
ev=bytearray()
ev+=bytes([0xC0,5])
ev+=bytes([0x90,60,100])+vlq(120)
ev+=bytes([30,0xB0,116,0])
ev+=bytes([60,0xB0,117,65])
ev+=bytes([0xFF,0x2F,0])
xmi=b"FORM"+(14).to_bytes(4,"big")+b"XDIR"+b"INFO"+(2).to_bytes(4,"big")+b"\x01\x00"
xmi+=b"CAT "+(4+12+len(ev)).to_bytes(4,"big")+b"XMID"+b"FORM"+(4+8+len(ev)).to_bytes(4,"big")+b"XMID"+chunk(b"EVNT",bytes(ev))
midi,report=m.convert_xmi_bytes(xmi)
checks={
 "midi_header":midi.startswith(b"MThd"),
 "format0":midi[8:10]==b"\x00\x00",
 "ppqn60":midi[12:14]==b"\x00\x3C",
 "fixed_tempo":b"\xFF\x51\x03\x07\xA1\x20" in midi,
 "note_on":b"\x90\x3C\x64" in midi,
 "note_off":b"\x80\x3C\x00" in midi,
 "loop_captured":len(report["loop_markers"])==1 and report["loop_start_tick"]==30 and report["loop_end_tick"]==90,
 "ail_loop_cc_not_forwarded":bytes([0xB0,116,0]) not in midi and bytes([0xB0,117,65]) not in midi,
 "duration_120hz":abs(report["duration_seconds"]-1.0)<1e-12,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.xmi_to_midi_validation","version":134,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
