#!/usr/bin/env python3
"""Source-safe census for original Azrael's Tear character animation inputs.

The tool never copies original payloads into Git. It scans a locally supplied
demo directory, records hashes/shape only, and identifies candidates for the
HIGH-confidence ICharacterAnim path recovered from R.EXE.

This is deliberately discovery-only: finding a candidate does not promote an
unknown file format to a decoded animation clip.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, re, sys

TEXTLIKE_EXTS={".ani",".anm",".dat",".txt",".cfg"}
CHAR_EXTS={".ani"}
ROOM_EXTS={".anm"}

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def ascii_tokens(blob: bytes) -> set[str]:
    return {m.decode("ascii","ignore") for m in re.findall(rb"[ -~]{3,64}",blob)}

def row(root: Path,p: Path) -> dict:
    b=p.read_bytes()
    lower_name=p.name.lower()
    tokens=ascii_tokens(b)
    tokens_lower={t.lower() for t in tokens}
    printable=sum(1 for x in b if x in (9,10,13) or 32<=x<=126)
    return {
        "path":str(p.relative_to(root)).replace("\\","/"),
        "name":p.name,
        "suffix":p.suffix.lower(),
        "bytes":len(b),
        "sha256":sha256(p),
        "textlike_ratio":round(printable/max(1,len(b)),6),
        "filename_mentions_niamh":"niamh" in lower_name,
        "payload_mentions_niamh":any("niamh" in t for t in tokens_lower),
        "payload_mentions_conv":any("conv" in t for t in tokens_lower),
        "room_animation_name":bool(re.fullmatch(r"ranim\d+\.anm",lower_name)),
    }

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demo_dir",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    root=a.demo_dir.expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"schema":"openazrael.character_animation_source_audit","version":138,
                          "status":"FAIL","reason":"DEMO_DIR_NOT_FOUND","demo_dir":str(root)},indent=2))
        return 1

    files=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        suffix=p.suffix.lower()
        lname=p.name.lower()
        if suffix in TEXTLIKE_EXTS or "niamh" in lname or "anim" in lname:
            try: files.append(row(root,p))
            except OSError: pass

    ani=[r for r in files if r["suffix"] in CHAR_EXTS]
    room=[r for r in files if r["suffix"] in ROOM_EXTS and r["room_animation_name"]]
    candidates=[
        r for r in ani
        if r["filename_mentions_niamh"] or (r["payload_mentions_niamh"] and r["payload_mentions_conv"])
    ]
    niamh_dat=[r for r in files if r["name"].lower()=="niamh.dat"]
    characte=[r for r in files if r["name"].lower()=="characte.dat"]

    # Known demo hashes are provenance anchors only. They do not identify the
    # character ANI format themselves.
    known={
        "CHARACTE.DAT":"5a1a67f5cfba790a543c7548e86f4d03c219e98cc20e5827927ddb7326fa8088",
        "NIAMH.DAT":"e3f0b14b64682f0e621f7f52fb998ccf8ddba4febd0ac0df4aa201f371939f71",
    }
    anchor_ok=(
        len(characte)==1 and characte[0]["sha256"]==known["CHARACTE.DAT"]
        and len(niamh_dat)==1 and niamh_dat[0]["sha256"]==known["NIAMH.DAT"]
    )

    if not anchor_ok:
        status="FAIL_CHARACTER_ANCHOR_MISMATCH"
    elif len(candidates)==1:
        status="PASS_SOURCE_CANDIDATE_UNDECODED"
    elif len(candidates)==0:
        status="HOLD_CHARACTER_ANI_NOT_IDENTIFIED"
    else:
        status="HOLD_AMBIGUOUS_CHARACTER_ANI"

    out={
        "schema":"openazrael.character_animation_source_audit",
        "version":138,
        "status":status,
        "source_safe":True,
        "character_anchor_hashes_match":anchor_ok,
        "character_ani_count":len(ani),
        "room_ranim_count":len(room),
        "niamh_candidate_count":len(candidates),
        "niamh_candidates":candidates,
        "policy":{
            "candidate_is_not_decoded_clip":True,
            "do_not_guess_format":True,
            "do_not_copy_original_payload_into_repo":True,
            "runtime_promotion_requires_parser_and_godot_playback_pass":True,
        },
        "evidence":[
            "R.EXE has HIGH-confidence ICharacterAnim loader paths at 0xED94 and 0x10C7A.",
            "R.EXE separately reads RANIM%d.ANM as room-animation data; room ANM must not be silently substituted for character ANI.",
            "CHARACTE.DAT and NIAMH.DAT hashes bind this audit to the canonical demo character corpus.",
        ],
    }
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))
    return 1 if status.startswith("FAIL") else 0

if __name__=="__main__":
    raise SystemExit(main())
