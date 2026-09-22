#!/usr/bin/env python3
"""Fail-closed KG-001 Candidate 4 preflight.

Builds on the complete Candidate 3 asset-backed/runtime/PPPV/fidelity preflight,
then adds Candidate 4 complete-audio and release-contract requirements. A PASS
receipt is written only when every inherited gate and every Candidate 4 gate
passes at the exact same Git HEAD and runtime asset set.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/".tmp/kg001"
C3=TMP/"candidate3_preflight_receipt.json"
OUT=TMP/"candidate4_preflight_receipt.json"
AUDIO_RESULT=TMP/"candidate4_audio_v132_runtime.json"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def run(cmd):
    return subprocess.run(cmd,cwd=ROOT,text=True,encoding="utf-8",errors="replace",
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

def fail(reason,details=None):
    OUT.unlink(missing_ok=True)
    out={"schema":"openazrael.kg001.candidate4_preflight","version":132,
         "status":"FAIL","candidate":"KG-001 Candidate 4","export_allowed":False,
         "reason":reason}
    if details is not None: out["details"]=details
    print(json.dumps(out,indent=2))
    return 1

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot")
    ap.add_argument("--demo-dir",type=Path)
    args=ap.parse_args()
    OUT.unlink(missing_ok=True);AUDIO_RESULT.unlink(missing_ok=True)

    cmd=[sys.executable,"tools/run_candidate3_preflight.py"]
    if args.godot: cmd += ["--godot",args.godot]
    if args.demo_dir is not None: cmd += ["--demo-dir",str(args.demo_dir.resolve())]
    inherited=run(cmd)
    if inherited.returncode!=0 or not C3.is_file():
        return fail("INHERITED_RUNTIME_PREFLIGHT_FAILED",{"output_tail":inherited.stdout[-20000:]})
    c3=json.loads(C3.read_text(encoding="utf-8"))
    if c3.get("status")!="PASS" or c3.get("export_allowed") is not True:
        return fail("INHERITED_RUNTIME_PREFLIGHT_NOT_PASS")

    source_contract=run([sys.executable,"tools/validate_candidate4_release_contract_v132.py"])
    if source_contract.returncode!=0:
        return fail("CANDIDATE4_RELEASE_CONTRACT_FAILED",{"output":source_contract.stdout[-12000:]})

    audio=run([sys.executable,"tools/validate_candidate4_audio_corpus_v132.py"])
    try:
        audio_payload=json.loads(audio.stdout)
    except Exception:
        audio_payload={"status":"FAIL","raw":audio.stdout[-12000:]}
    AUDIO_RESULT.write_text(json.dumps(audio_payload,indent=2)+"\n",encoding="utf-8")
    if audio.returncode!=0 or audio_payload.get("status")!="PASS":
        return fail("CANDIDATE4_COMPLETE_AUDIO_FAILED",audio_payload)

    forensic_meta=c3.get("evidence",{}).get("room_forensic_v131",{})
    forensic_path=ROOT/str(forensic_meta.get("path",""))
    if not forensic_path.is_file() or sha256(forensic_path)!=forensic_meta.get("sha256"):
        return fail("ROOM_FORENSIC_V131_EVIDENCE_CHANGED")
    forensic=json.loads(forensic_path.read_text(encoding="utf-8"))
    if forensic.get("status")!="PASS" or any(
        forensic.get("rooms",{}).get(room,{}).get("status")!="PASS"
        for room in ("R1","R7","R8")
    ):
        return fail("ROOM_FORENSIC_V131_NOT_PASS",forensic)

    receipt=dict(c3)
    receipt.update({
        "schema":"openazrael.kg001.candidate4_preflight",
        "version":132,
        "candidate":"KG-001 Candidate 4",
        "status":"PASS",
        "export_allowed":True,
        "candidate3_preflight_receipt_sha256":sha256(C3),
        "candidate4_audio_v132":"PASS",
        "room_forensic_v131":"PASS",
    })
    receipt.setdefault("evidence",{})["candidate4_audio_v132"]={
        "path":str(AUDIO_RESULT.relative_to(ROOT)),
        "sha256":sha256(AUDIO_RESULT),
    }
    receipt["build_rule"]=(
        "Candidate 4 export is permitted only while exact Git HEAD, clean tree, Godot, "
        "all inherited runtime/PPPV/fidelity evidence, room-forensic v131, complete-audio "
        "v132 evidence and the exact runtime asset set remain identical to this receipt."
    )
    OUT.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
