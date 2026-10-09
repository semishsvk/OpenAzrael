#!/usr/bin/env python3
"""Source-safe Candidate 4 MUSIC.DAT/XMI route analyzer (v133).

Reads the user's local official demo corpus and emits metadata only. Raw MUSIC.DAT
text, XMI bytes and R.EXE bytes are never copied into Git or into the report.

Textual room/XMI bindings are accepted when explicit.  The bound 1996 demo uses
an older numeric MUSIC.DAT form, so numeric promotion is allowed only when the
exact bound R.EXE independently proves both pair-loader semantics and the XMI
slot table.  A bare integer by itself is never treated as a room or track.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, re, struct, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools.audit_file_open_families_v103 import build_objects, early_string

IR=ROOT/"data/audio/legacy_world_ir.json"
EXPECTED_REXE_SHA256="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
DEFAULT_OUT=ROOT/".tmp/kg001/candidate4_music_route_v133.json"

ROOM_ALIASES={
    "R1":{"R1","ROOM0","ROOM 0","ENTRYCORRIDOR","ENTRY CORRIDOR","ENTCORI"},
    "R7":{"R7","ROOM1","ROOM 1","WELLROOM","WELL ROOM"},
    "R8":{"R8","ROOM2","ROOM 2","BAPTISTRY","BAPTISTERY","BAPTISTRYROOM"},
}
# These are not inferred from MUSIC.DAT. They are the numeric suffixes of the
# accepted source room identities R1/R7/R8 and are used only after R.EXE proves
# that MUSIC.DAT's first numeric token is the table key.
ACCEPTED_ROOM_NUMBERS={"R1":1,"R7":7,"R8":8}

# Exact general-MIDI slot order initialized by the bound R.EXE. FM variants are
# an alternate device profile; Candidate 4's SoundFont renderer uses the GM XMI
# identities. DEATH/BLANK remain explicit slots even though the accepted route
# does not select them.
GENERAL_MIDI_SLOTS={
    0:"AWEMYST.XMI", 1:"CATHEDRL.XMI", 2:"EGYPTIAN.XMI",
    3:"FIGHT2.XMI", 4:"GHOSTS.XMI", 5:"GRAIL.XMI",
    6:"INGAME.XMI", 7:"INGAME2.XMI", 8:"KREEPY2.XMI",
    9:"KREEPY3.XMI", 10:"PEACEFUL.XMI", 11:"DEATH.XMI",
    12:"BLANK.XMI",
}
GENERAL_MIDI_STRING_IMM={
    0:0x3AB,1:0x3B7,2:0x3C4,3:0x3D1,4:0x3DC,5:0x3E7,
    6:0x3F1,7:0x3FC,8:0x408,9:0x414,10:0x420,11:0x4B9,12:0x4C3,
}
SLOT_BASE=0x121DC
SLOT_STRIDE=12
PAIR_FORMAT_IMM=0x4D9
END_TOKEN_IMM=0x4E1


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


def call_target(buf: bytes,site: int) -> int|None:
    if site<0 or site+5>len(buf) or buf[site]!=0xE8:
        return None
    rel=int.from_bytes(buf[site+1:site+5],"little",signed=True)
    return site+5+rel


def bound_rexe_music_model(raw: bytes) -> dict:
    """Prove the numeric pair loader and GM selector table from exact R.EXE."""
    objects=build_objects(raw)
    if not objects:
        return {"status":"FAIL","reason":"R_EXE_OBJECT_LAYOUT_UNAVAILABLE"}
    o1v=objects[0]["virtual"]
    o1p=objects[0]["page_span"]

    checks={
        "music_dat_open_call": call_target(o1v,0x0EF4)==0x26004,
        "pair_format_string": early_string(o1p,PAIR_FORMAT_IMM)==" %s %s ",
        "end_token_string": early_string(o1p,END_TOKEN_IMM)=="END",
        # second token -> helper result in EDX, first token -> same helper result
        # in EAX, then byte store [table_base + EAX] = DL.
        "numeric_pair_assignment": o1v[0x0F2D:0x0F4B]==bytes.fromhex(
            "8d857affffffe83f7e020089c28d855affffffe8327e0200889078210100"
        ),
    }

    slot_checks={}
    # slots 0..9 are regular 15-byte init blocks.
    for slot in range(10):
        off=0x0D76+slot*0x0F
        imm=GENERAL_MIDI_STRING_IMM[slot]
        addr=SLOT_BASE+slot*SLOT_STRIDE
        prefix=(b"\xBA"+struct.pack("<I",imm)+b"\xB8"+struct.pack("<I",addr))
        slot_checks[str(slot)]=(
            o1v[off:off+10]==prefix
            and early_string(o1p,imm).upper()==GENERAL_MIDI_SLOTS[slot]
        )
    # PEACEFUL's string load is before a branch which converges on slot 10.
    slot_checks["10"]=(
        o1v[0x0E0C:0x0E11]==b"\xBA"+struct.pack("<I",GENERAL_MIDI_STRING_IMM[10])
        and o1v[0x0EB1:0x0EB6]==b"\xB8"+struct.pack("<I",SLOT_BASE+10*SLOT_STRIDE)
        and early_string(o1p,GENERAL_MIDI_STRING_IMM[10]).upper()==GENERAL_MIDI_SLOTS[10]
    )
    # DEATH and BLANK are shared special slots after both device branches.
    slot_checks["11"]=(
        o1v[0x0EBB:0x0EC5]==(
            b"\xBA"+struct.pack("<I",GENERAL_MIDI_STRING_IMM[11])+
            b"\xB8"+struct.pack("<I",SLOT_BASE+11*SLOT_STRIDE)
        )
        and early_string(o1p,GENERAL_MIDI_STRING_IMM[11]).upper()==GENERAL_MIDI_SLOTS[11]
    )
    slot_checks["12"]=(
        o1v[0x0ECA:0x0ED4]==(
            b"\xBA"+struct.pack("<I",GENERAL_MIDI_STRING_IMM[12])+
            b"\xB8"+struct.pack("<I",SLOT_BASE+12*SLOT_STRIDE)
        )
        and early_string(o1p,GENERAL_MIDI_STRING_IMM[12]).upper()==GENERAL_MIDI_SLOTS[12]
    )
    checks["general_midi_slot_table"]=all(slot_checks.values())
    failed=[name for name,ok in checks.items() if not ok]
    return {
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed":failed,
        "pair_semantics":"selector_by_key[first_numeric_token]=second_numeric_token",
        "selector_profile":"GENERAL_MIDI_XMI",
        "slot_count":len(GENERAL_MIDI_SLOTS),
        "slots":{str(k):v for k,v in GENERAL_MIDI_SLOTS.items()},
        "evidence_offsets":{
            "music_dat_fopen_call":"0x0ef4",
            "pair_assignment":"0x0f2d-0x0f4a",
            "gm_slot_init":"0x0d76-0x0ed9",
        },
    }


def parse_numeric_music_table(text: str) -> dict:
    pairs: dict[int,int]={}
    conflicts=[]
    malformed=[]
    ended=False
    parsed_rows=0
    for line_no,line in enumerate(text.splitlines(),1):
        stripped=line.strip().strip("\x1a").strip()
        if not stripped:
            continue
        if stripped.upper()=="END":
            ended=True
            break
        match=re.fullmatch(r"(\d+)\s+(\d+)",stripped)
        if not match:
            malformed.append(line_no)
            continue
        key=int(match.group(1)); selector=int(match.group(2)); parsed_rows+=1
        if key in pairs and pairs[key]!=selector:
            conflicts.append({"key":key,"first":pairs[key],"second":selector,"line":line_no})
        else:
            pairs[key]=selector
    return {
        "status":"PASS" if ended and not conflicts and not malformed else "FAIL",
        "ended":ended,
        "parsed_row_count":parsed_rows,
        "unique_key_count":len(pairs),
        "conflicts":conflicts,
        "malformed_lines":malformed,
        "pairs":pairs,
    }


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

    rexe_raw=rexe.read_bytes()
    rexe_sha=hashlib.sha256(rexe_raw).hexdigest()
    if rexe_sha!=EXPECTED_REXE_SHA256:
        payload={"schema":"openazrael.kg001.candidate4_music_route","version":133,
                 "status":"FAIL","resolution":"UNKNOWN",
                 "reason":"BOUND_DEMO_REXE_HASH_MISMATCH",
                 "expected_rexe_sha256":EXPECTED_REXE_SHA256,
                 "observed_rexe_sha256":rexe_sha}
        out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,indent=2)); return 1

    xmi_rows=[]; missing_xmi=[]; bad_xmi=[]
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

    raw=music_dat.read_bytes(); text=normalized_text(raw)
    nonempty=[line for line in text.splitlines() if line.strip()]

    # First preserve the explicit textual path for any future source variant.
    rows=[]; recognized=set()
    for line_no,line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        upper=line.upper(); names=set()
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
                "xmi":sorted(names),"explicit_demo_rooms":rooms,
                "integers":integers,"token_count":len(tokens),
            })

    explicit=[]; ambiguous=[]
    for row in rows:
        if row["explicit_demo_rooms"] or row["xmi"]:
            if len(row["explicit_demo_rooms"])==1 and len(row["xmi"])==1:
                explicit.append({"room":row["explicit_demo_rooms"][0],"xmi":row["xmi"][0],"line":row["line"]})
            else:
                ambiguous.append({"line":row["line"],
                                  "room_count":len(row["explicit_demo_rooms"]),
                                  "xmi_count":len(row["xmi"])})

    by_room={room:sorted({m["xmi"] for m in explicit if m["room"]==room}) for room in ("R1","R7","R8")}
    binding_source="EXPLICIT_TEXT"
    forensic=bound_rexe_music_model(rexe_raw)
    numeric=parse_numeric_music_table(text)
    numeric_bindings=[]

    explicit_complete=all(len(by_room[room])==1 for room in ("R1","R7","R8"))
    explicit_ambiguous=any(row.get("room_count",0)>0 for row in ambiguous)
    if not explicit_complete and not explicit_ambiguous and forensic.get("status")=="PASS" and numeric.get("status")=="PASS":
        candidate_by_room={}
        numeric_ok=True
        for room,key in ACCEPTED_ROOM_NUMBERS.items():
            selector=numeric["pairs"].get(key)
            xmi=GENERAL_MIDI_SLOTS.get(selector) if selector is not None else None
            if xmi is None or xmi not in canonical:
                numeric_ok=False; break
            candidate_by_room[room]=[xmi]
            numeric_bindings.append({
                "room":room,
                "legacy_room_number":key,
                "selector":selector,
                "xmi":xmi,
            })
        if numeric_ok:
            by_room=candidate_by_room
            binding_source="BOUND_REXE_NUMERIC_TABLE"

    route_music=sorted({x for vals in by_room.values() for x in vals})
    route_complete=all(len(by_room[room])==1 for room in ("R1","R7","R8"))
    route_ambiguous=explicit_ambiguous
    if route_complete and not route_ambiguous:
        status="PASS"; resolution="REQUIRES_RUNTIME_MUSIC"
        reason=(
            "COMPLETE_EXPLICIT_ACCEPTED_ROUTE_MUSIC_BINDINGS_RECOVERED"
            if binding_source=="EXPLICIT_TEXT"
            else "COMPLETE_BOUND_REXE_NUMERIC_ROUTE_BINDINGS_RECOVERED"
        )
    else:
        status="HOLD"; resolution="UNKNOWN"
        reason="MUSIC_TABLE_ROUTE_MAPPING_INCOMPLETE_OR_AMBIGUOUS"

    numeric_summary={k:v for k,v in numeric.items() if k!="pairs"}
    payload={
        "schema":"openazrael.kg001.candidate4_music_route","version":133,
        "status":status,"resolution":resolution,"reason":reason,
        "source":{
            "music_dat_sha256":sha256(music_dat),"music_dat_bytes":len(raw),
            "nonempty_line_count":len(nonempty),"bound_rexe_sha256":rexe_sha,
        },
        "canonical_xmi":{
            "expected_count":24,"verified_count":len(xmi_rows),
            "recognized_in_music_dat_count":len(recognized),
            "recognized_in_music_dat":sorted(recognized),
        },
        "accepted_demo_route":{
            "rooms":["R1","R7","R8"],"binding_source":binding_source,
            "explicit_bindings":explicit,"forensic_numeric_bindings":numeric_bindings,
            "music_by_room":by_room,"required_xmi":route_music,
            "complete_one_binding_per_room":route_complete,"ambiguous_rows":ambiguous,
        },
        "forensic_numeric_table":{
            "status":"PASS" if forensic.get("status")=="PASS" and numeric.get("status")=="PASS" else "FAIL",
            "bound_rexe_model":forensic,
            "music_dat_structure":numeric_summary,
            "accepted_room_numeric_identity":ACCEPTED_ROOM_NUMBERS,
            "promotion_rule":"NUMERIC_BINDING_REQUIRES_EXACT_BOUND_REXE_PAIR_AND_SLOT_SIGNATURES",
        },
        "source_safe":True,"raw_music_dat_emitted":False,"raw_xmi_emitted":False,
        "policy":(
            "Bare numeric promotion is forbidden. Numeric route binding is allowed only "
            "when the exact bound R.EXE proves MUSIC.DAT pair semantics and XMI slot "
            "order, and the table key matches an accepted source room identity R<n>."
        ),
    }
    out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return 0 if status=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
