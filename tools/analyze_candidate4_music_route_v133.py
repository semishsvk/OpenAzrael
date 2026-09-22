#!/usr/bin/env python3
"""Source-safe Candidate 4 MUSIC.DAT/XMI route analyzer (v133).

Reads the user's local official demo corpus and emits metadata only. Raw MUSIC.DAT
text, XMI bytes and R.EXE bytes are never copied into Git or into the report.

The analyzer intentionally refuses to infer room semantics from bare integers.
A room->music binding is promoted only when the MUSIC.DAT row contains an
explicit accepted-demo room token/alias and exactly one canonical XMI identity.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
IR=ROOT/"data/audio/legacy_world_ir.json"
EXPECTED_REXE_SHA256="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
DEFAULT_OUT=ROOT/".tmp/kg001/candidate4_music_route_v133.json"

ROOM_ALIASES={
    "R1":{"R1","ROOM0","ROOM 0","ENTRYCORRIDOR","ENTRY CORRIDOR","ENTCORI"},
    "R7":{"R7","ROOM1","ROOM 1","WELLROOM","WELL ROOM"},
    "R8":{"R8","ROOM2","ROOM 2","BAPTISTRY","BAPTISTERY","BAPTISTRYROOM"},
}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def locate(base: Path,name: str) -> Path|None:
    candidates=[base/name,base/name.upper(),base/name.lower(),base/"GAME"/"AZRAEL"/name]
    for p in candidates:
        if p.is_file(): return p
    target=name.upper()
    for p in base.rglob("*"):
        if p.is_file() and p.name.upper()==target: return p
    return None

def normalized_text(data: bytes) -> str:
    for enc in ("utf-8","cp437","latin-1"):
        try:return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode("latin-1","replace")

def room_hits(line_upper: str) -> list[str]:
    compact=re.sub(r"[^A-Z0-9]+","",line_upper)
    hits=[]
    for room,aliases in ROOM_ALIASES.items():
        matched=False
        for alias in aliases:
            au=alias.upper()
            if " " in au:
                if au in line_upper: matched=True; break
            elif au in line_upper or re.sub(r"[^A-Z0-9]+","",au) in compact:
                matched=True; break
        if matched:hits.append(room)
    return sorted(set(hits))

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demo_dir",type=Path)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args()
    demo=args.demo_dir.resolve()
    out=args.out.resolve()
    out.parent.mkdir(parents=True,exist_ok=True)

    ir=json.loads(IR.read_text(encoding="utf-8"))
    music=ir.get("audio",{}).get("music_assets",[])
    if len(music)!=24:
        raise SystemExit("canonical XMI inventory drift")
    canonical={row["filename"].upper():row for row in music}
    by_stem={Path(name).stem.upper():name for name in canonical}

    music_dat=locate(demo,"MUSIC.DAT")
    rexe=locate(demo,"R.EXE")
    missing=[]
    if not music_dat: missing.append("MUSIC.DAT")
    if not rexe: missing.append("R.EXE")
    if missing:
        payload={"schema":"openazrael.kg001.candidate4_music_route","version":133,
                 "status":"HOLD","resolution":"UNKNOWN",
                 "reason":"REQUIRED_FORENSIC_SOURCE_MISSING","missing":missing}
        out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,indent=2)); return 2

    rexe_sha=sha256(rexe)
    if rexe_sha!=EXPECTED_REXE_SHA256:
        payload={"schema":"openazrael.kg001.candidate4_music_route","version":133,
                 "status":"FAIL","resolution":"UNKNOWN",
                 "reason":"BOUND_DEMO_REXE_HASH_MISMATCH",
                 "expected_rexe_sha256":EXPECTED_REXE_SHA256,
                 "observed_rexe_sha256":rexe_sha}
        out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,indent=2)); return 1

    xmi_rows=[]
    missing_xmi=[]
    bad_xmi=[]
    for name,row in canonical.items():
        p=locate(demo,name)
        if not p:
            missing_xmi.append(name); continue
        observed=sha256(p)
        if observed!=row.get("sha256"):
            bad_xmi.append({"filename":name,"expected_sha256":row.get("sha256"),"observed_sha256":observed})
        xmi_rows.append({"filename":name,"bytes":p.stat().st_size,"sha256":observed})
    if missing_xmi or bad_xmi:
        payload={"schema":"openazrael.kg001.candidate4_music_route","version":133,
                 "status":"FAIL","resolution":"UNKNOWN",
                 "reason":"CANONICAL_XMI_CORPUS_INVALID",
                 "missing_xmi":missing_xmi,"fingerprint_failures":bad_xmi,
                 "verified_xmi_count":len(xmi_rows)-len(bad_xmi)}
        out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,indent=2)); return 1

    raw=music_dat.read_bytes()
    text=normalized_text(raw)
    nonempty=[line for line in text.splitlines() if line.strip()]
    rows=[]
    recognized=set()
    for line_no,line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        upper=line.upper()
        names=set()
        tokens=re.findall(r"[A-Z0-9_]+(?:\.XMI)?",upper)
        for token in tokens:
            if token in canonical:
                names.add(token)
            elif token.endswith(".XMI") and Path(token).stem.upper() in by_stem:
                names.add(by_stem[Path(token).stem.upper()])
            elif token in by_stem:
                names.add(by_stem[token])
        rooms=room_hits(upper)
        integers=[int(x,0) for x in re.findall(r"(?<![A-Z0-9_])(?:0X[0-9A-F]+|[-+]?\d+)(?![A-Z0-9_])",upper)]
        if names or rooms or integers:
            recognized.update(names)
            rows.append({
                "line":line_no,
                "line_sha256":hashlib.sha256(line.strip().encode("utf-8","replace")).hexdigest(),
                "xmi":sorted(names),
                "explicit_demo_rooms":rooms,
                "integers":integers,
                "token_count":len(tokens),
            })

    explicit=[]
    ambiguous=[]
    for row in rows:
        if row["explicit_demo_rooms"] or row["xmi"]:
            if len(row["explicit_demo_rooms"])==1 and len(row["xmi"])==1:
                explicit.append({"room":row["explicit_demo_rooms"][0],"xmi":row["xmi"][0],"line":row["line"]})
            elif row["explicit_demo_rooms"] or row["xmi"]:
                ambiguous.append({"line":row["line"],
                                  "room_count":len(row["explicit_demo_rooms"]),
                                  "xmi_count":len(row["xmi"])})

    by_room={room:sorted({m["xmi"] for m in explicit if m["room"]==room}) for room in ("R1","R7","R8")}
    route_music=sorted({x for vals in by_room.values() for x in vals})

    # Fail closed: absence of explicit room aliases does NOT prove that music is unused.
    if route_music:
        status="PASS"; resolution="REQUIRES_RUNTIME_MUSIC"
        reason="EXPLICIT_ACCEPTED_ROUTE_MUSIC_BINDINGS_RECOVERED"
    else:
        status="HOLD"; resolution="UNKNOWN"
        reason="MUSIC_TABLE_PRESENT_BUT_ACCEPTED_ROUTE_BINDING_NOT_EXPLICIT"

    payload={
        "schema":"openazrael.kg001.candidate4_music_route",
        "version":133,
        "status":status,
        "resolution":resolution,
        "reason":reason,
        "source":{
            "music_dat_sha256":sha256(music_dat),
            "music_dat_bytes":len(raw),
            "nonempty_line_count":len(nonempty),
            "bound_rexe_sha256":rexe_sha,
        },
        "canonical_xmi":{
            "expected_count":24,
            "verified_count":len(xmi_rows),
            "recognized_in_music_dat_count":len(recognized),
            "recognized_in_music_dat":sorted(recognized),
        },
        "accepted_demo_route":{
            "rooms":["R1","R7","R8"],
            "explicit_bindings":explicit,
            "music_by_room":by_room,
            "required_xmi":route_music,
            "ambiguous_rows":ambiguous,
        },
        "source_safe":True,
        "raw_music_dat_emitted":False,
        "raw_xmi_emitted":False,
        "policy":"Bare numeric fields are metadata only and are never interpreted as room IDs without independent evidence.",
    }
    out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return 0 if status=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
