#!/usr/bin/env python3
"""Candidate 4 complete-audio runtime gate.

Requires the full canonical 30-WAV demo corpus restored from fingerprint-verified
original demo files. Runtime files are bound to the local restore receipt.
Music/XMI handling is fail-closed until route evidence proves either runtime
support for the required music or that no XMI music is used on the accepted
Candidate 4 demo route.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json, sys

ROOT=Path(__file__).resolve().parents[1]
IR=ROOT/"data/audio/legacy_world_ir.json"
RESTORE=ROOT/".tmp/kg001/candidate4_audio_restore_v132.json"
MUSIC=ROOT/".tmp/kg001/candidate4_music_route_v133.json"\nMUSIC_RUNTIME=ROOT/".tmp/kg001/candidate4_music_runtime_v135.json"
AUDIO=ROOT/"assets/audio"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def fail(reason: str, details=None) -> int:
    out={"schema":"openazrael.kg001.candidate4_audio_validation","version":132,
         "status":"FAIL","reason":reason}
    if details is not None: out["details"]=details
    print(json.dumps(out,indent=2))
    return 1

def main() -> int:
    if not IR.is_file(): return fail("CANONICAL_AUDIO_IR_MISSING")
    ir=json.loads(IR.read_text(encoding="utf-8"))
    sounds=ir.get("audio",{}).get("sounds",[])
    music_assets=ir.get("audio",{}).get("music_assets",[])
    if len(sounds)!=30:
        return fail("CANONICAL_WAV_COUNT_DRIFT",{"expected":30,"actual":len(sounds)})
    if len(music_assets)!=24:
        return fail("CANONICAL_XMI_COUNT_DRIFT",{"expected":24,"actual":len(music_assets)})
    if not RESTORE.is_file():
        return fail("CANDIDATE4_AUDIO_RESTORE_RECEIPT_MISSING")
    receipt=json.loads(RESTORE.read_text(encoding="utf-8"))
    if receipt.get("status")!="PASS" or receipt.get("restored_wav_count")!=30:
        return fail("CANDIDATE4_AUDIO_RESTORE_INCOMPLETE",receipt)
    expected={row["filename"]:row for row in sounds}
    restored={row.get("filename"):row for row in receipt.get("files",[])}
    if set(restored)!=set(expected):
        return fail("RESTORE_WAV_NAME_SET_MISMATCH",{
            "missing":sorted(set(expected)-set(restored)),
            "extra":sorted(set(restored)-set(expected)),
        })
    current_names={p.name for p in AUDIO.iterdir() if p.is_file()} if AUDIO.is_dir() else set()
    missing_runtime=sorted(set(expected)-current_names)
    if missing_runtime:
        return fail("RUNTIME_WAV_CORPUS_INCOMPLETE",{"missing":missing_runtime})
    bad=[]
    for name,row in expected.items():
        rr=restored[name]
        runtime=AUDIO/name
        current_sha=sha256(runtime)
        if rr.get("source_sha256")!=row.get("sha256"):
            bad.append({"file":name,"error":"source_sha_mismatch"})
        if rr.get("expected_source_sha256")!=row.get("sha256"):
            bad.append({"file":name,"error":"expected_source_sha_mismatch"})
        if rr.get("runtime_sha256")!=current_sha:
            bad.append({"file":name,"error":"runtime_changed_after_restore"})
    if bad:
        return fail("RUNTIME_WAV_FINGERPRINT_FAILURE",{"failures":bad})
    if not MUSIC.is_file():
        return fail("MUSIC_ROUTE_EVIDENCE_MISSING",{
            "policy":"REQUIRE_RUNTIME_OR_PROVEN_NOT_USED_ON_ACCEPTED_DEMO_ROUTE",
            "canonical_xmi_count":24,
        })
    music=json.loads(MUSIC.read_text(encoding="utf-8"))
    if music.get("status")!="PASS":
        return fail("MUSIC_ROUTE_EVIDENCE_NOT_PASS",music)
    resolution=music.get("resolution")
    if resolution=="REQUIRES_RUNTIME_MUSIC":
        if not MUSIC_RUNTIME.is_file():
            return fail("MUSIC_RUNTIME_REQUIRED",{
                "required_xmi":music.get("accepted_demo_route",{}).get("required_xmi",[]),
                "expected_runtime_evidence":str(MUSIC_RUNTIME.relative_to(ROOT)),
            })
        runtime=json.loads(MUSIC_RUNTIME.read_text(encoding="utf-8"))
        route_required=set(x.upper() for x in music.get("accepted_demo_route",{}).get("required_xmi",[]))
        required=set(x for x in route_required if x!="BLANK.XMI")
        rendered=set(x.upper() for x in runtime.get("rendered_xmi",[]))
        canonical_music=set(row["filename"].upper() for row in music_assets)
        expected_rendered=canonical_music-{"BLANK.XMI"}
        if (
            runtime.get("status")!="PASS"
            or runtime.get("runtime_playback_test")!="PASS"
            or not route_required
            or not required.issubset(rendered)
            or runtime.get("all_canonical_rendered") is not True
            or rendered!=expected_rendered
        ):
            return fail("MUSIC_RUNTIME_PLAYBACK_NOT_PROVEN",{
                "route_required_xmi":sorted(route_required),
                "required_audible_xmi":sorted(required),
                "rendered_xmi":sorted(rendered),
                "expected_complete_rendered_xmi":sorted(expected_rendered),
                "runtime_status":runtime.get("status"),
                "runtime_playback_test":runtime.get("runtime_playback_test"),
                "all_canonical_rendered":runtime.get("all_canonical_rendered"),
            })
        resolution="RUNTIME_SUPPORTED"
    elif resolution!="NOT_USED_ON_ACCEPTED_DEMO_ROUTE":
        return fail("MUSIC_ROUTE_RESOLUTION_INVALID",{"resolution":resolution})
    out={
        "schema":"openazrael.kg001.candidate4_audio_validation",
        "version":132,
        "status":"PASS",
        "wav_corpus":"30/30",
        "runtime_wav_fingerprints":"PASS",
        "canonical_xmi_count":24,
        "music_route_resolution":resolution,
    }
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
