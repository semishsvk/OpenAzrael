#!/usr/bin/env python3
"""OpenAzrael legacy world/audio exporter v21.

Exports engine-neutral IR from original Azrael's Tear demo data.  The exporter
preserves original coordinates and provenance.  It deliberately does NOT guess
the final Godot coordinate transform; that is a separate calibrated transform.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, wave
from pathlib import Path

ROOMS = {
    0: {"openazrael_room": "R1", "name": "Entry Corridor"},
    1: {"openazrael_room": "R7", "name": "WellRoom"},
    2: {"openazrael_room": "R8", "name": "Baptistry"},
}
SAMPLE_RE = re.compile(r"^\s*SAMPLE\s+([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\s+(.+?\.wav)\s*$", re.I)

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def wav_meta(path: Path):
    with wave.open(str(path),'rb') as w:
        return {"channels":w.getnchannels(),"sample_rate":w.getframerate(),"sample_width_bits":w.getsampwidth()*8,
                "frames":w.getnframes(),"duration_seconds":w.getnframes()/float(w.getframerate())}

def parse_amb(path: Path, room_id: int):
    raw=path.read_bytes().replace(b'\x1a',b'').decode('latin1',errors='replace')
    out=[]
    for ln,line in enumerate(raw.splitlines(),1):
        m=SAMPLE_RE.match(line)
        if not m: continue
        x,y,z=map(float,m.group(1,2,3)); fn=m.group(4).strip()
        out.append({
            "emitter_id":f"OA_AMB_R{room_id}_{len(out)+1:03d}",
            "room_id":room_id,
            "room":ROOMS.get(room_id,{}),
            "sample":fn.upper(),
            "legacy_position":[x,y,z],
            "coordinate_space":"AZRAEL_WORLD_XYZ",
            "playback_class":"POSITIONAL_AMBIENT",
            "source":{"file":path.name,"line":ln,"record":line.strip()},
            "provenance":"ORIGINAL_EXPLICIT","confidence":"VERIFIED",
            "godot_position":None,
            "transform_status":"PENDING_CALIBRATION"
        })
    return out

def parse_npc(path: Path):
    # NPC*.DAT is textual in the demo. Parse the stable name + position + direction prefix.
    text=path.read_bytes().replace(b'\x1a',b'').decode('latin1',errors='replace')
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    if not lines: return []
    try: count=int(lines[0])
    except ValueError: return []
    out=[]; i=1
    float3=re.compile(r'^([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)$')
    while i+2 < len(lines) and len(out)<count:
        name=lines[i]; mp=float3.match(lines[i+1]); md=float3.match(lines[i+2])
        if mp and md:
            pos=list(map(float,mp.groups())); direction=list(map(float,md.groups()))
            out.append({"name":name,"legacy_position":pos,"legacy_direction":direction,
                        "coordinate_space":"AZRAEL_WORLD_XYZ","source":{"file":path.name,"line":i+1},
                        "provenance":"ORIGINAL_EXPLICIT","confidence":"VERIFIED",
                        "godot_position":None,"godot_direction":None,"transform_status":"PENDING_CALIBRATION"})
            # Find next plausible name+two float3 rows rather than assuming variable tail size.
            i += 3
            while i+2 < len(lines):
                if float3.match(lines[i+1]) and float3.match(lines[i+2]): break
                i += 1
        else: i += 1
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('legacy_dir',type=Path,help='Extracted ATDEMO directory')
    ap.add_argument('output_dir',type=Path)
    ap.add_argument('--copy-audio',action='store_true')
    a=ap.parse_args(); src=a.legacy_dir; out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
    emitters=[]
    for p in sorted(src.glob('AMB*.SND')):
        m=re.search(r'AMB(\d+)\.SND$',p.name,re.I)
        if m: emitters += parse_amb(p,int(m.group(1)))
    sounds=[]
    wavs={p.name.upper():p for p in src.glob('*.WAV')}
    for name,p in sorted(wavs.items()):
        rec={"sound_id":"OA_SND_"+p.stem.upper(),"filename":p.name,"sha256":sha256(p),**wav_meta(p),
             "provenance":"ORIGINAL_DEMO","source_path":p.name}
        rec["positional_ambient_references"]=[e["emitter_id"] for e in emitters if e["sample"]==name]
        sounds.append(rec)
    npcs=[]
    for p in sorted(src.glob('NPC*.DAT')):
        state=re.search(r'NPC(\d+)\.DAT$',p.name,re.I)
        for n in parse_npc(p): n["state_file_index"]=int(state.group(1)) if state else None; npcs.append(n)
    music=[{"filename":p.name,"sha256":sha256(p),"provenance":"ORIGINAL_DEMO"} for p in sorted(src.glob('*.XMI'),key=lambda p:p.name.casefold())]
    ir={
      "schema":"openazrael.legacy_world_ir","version":1,
      "exporter":"export_legacy_world_v21.py",
      "coordinate_model":{"source":"AZRAEL_WORLD_XYZ","y_axis":"VERTICAL_VERIFIED_FROM_NPC_DIRECTION_CORPUS",
          "godot_transform":{"status":"PENDING_CALIBRATION","policy":"PRESERVE_SOURCE_COORDINATES; DO_NOT_GUESS"}},
      "rooms":ROOMS,"audio":{"sounds":sounds,"ambient_emitters":emitters,"music_assets":music},
      "npc_state_instances":npcs,
      "counts":{"wav":len(sounds),"ambient_emitters":len(emitters),"xmi":len(music),"npc_instances":len(npcs)}
    }
    (out/'legacy_world_ir.json').write_text(json.dumps(ir,indent=2),encoding='utf8',newline='\n')
    for rid,r in ROOMS.items():
        room_ir={"schema":"openazrael.room_legacy_ir","version":1,"room_id":rid,**r,
                 "ambient_emitters":[e for e in emitters if e['room_id']==rid]}
        (out/f"{r['openazrael_room']}.legacy.json").write_text(json.dumps(room_ir,indent=2),encoding='utf8')
    if a.copy_audio:
        ad=out/'original_audio'; ad.mkdir(exist_ok=True)
        for p in list(src.glob('*.WAV'))+list(src.glob('*.SND'))+list(src.glob('*.XMI')): shutil.copy2(p,ad/p.name)
    print(json.dumps(ir['counts'],indent=2))

if __name__=='__main__': main()
