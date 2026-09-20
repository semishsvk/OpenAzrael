#!/usr/bin/env python3
"""Promote compact KG-001 Candidate evidence only after a successful run.

This helper deliberately mutates tracked data/tests evidence. It must therefore
run after fresh-checkout cleanliness has already been observed and, for packaged
test-build workflows, after the Windows export/startup smoke has completed.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE=ROOT/".tmp/kg001"

MAPPING={
    "kg001_v109_runtime.json":"data/tests/kg001_headless_runtime_v109.json",
    "kg001_v110_runtime.json":"data/tests/kg001_room_trigger_runtime_v110.json",
    "kg001_v111_runtime.json":"data/tests/kg001_full_demo_runtime_v111.json",
    "kg001_audio_v116_runtime.json":"data/tests/kg001_audio_runtime_v116.json",
    "kg001_source_validation_v112.json":"data/tests/kg001_source_validation_v112.json",
    "kg001_fresh_checkout.json":"data/tests/kg001_fresh_checkout.json",
    "kg001_visual_capture_v117.json":"data/tests/kg001_visual_capture_runtime_v117.json",
    "kg001_candidate2_asset_set_v118.json":"data/tests/kg001_candidate2_asset_set_runtime_v118.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def promote_results(evidence_dir: Path=DEFAULT_EVIDENCE) -> dict:
    candidate_path=evidence_dir/"kg001_candidate_v112.json"
    fresh_path=evidence_dir/"kg001_fresh_checkout.json"
    if not candidate_path.is_file() or not fresh_path.is_file():
        raise RuntimeError("candidate/fresh evidence missing; refusing promotion")

    candidate=load_json(candidate_path)
    fresh=load_json(fresh_path)
    if candidate.get("status")!="PASS":
        raise RuntimeError(
            f"candidate status is not PASS: {candidate.get('status')}"
        )
    if fresh.get("status")!="PASS":
        raise RuntimeError(
            f"fresh-checkout status is not PASS: {fresh.get('status')}"
        )
    if candidate.get("candidate2_asset_set")!="PASS":
        raise RuntimeError("complete Candidate 2 asset-set evidence is not PASS")
    if candidate.get("candidate2_asset_local_status")!="COMPLETE":
        raise RuntimeError("Candidate 2 local asset set is not COMPLETE")

    visual_requested=bool(candidate.get("visual_capture_requested"))
    if visual_requested and candidate.get("visual_capture")!="PASS":
        raise RuntimeError(
            "visual capture was requested but did not record PASS"
        )

    copied=[]
    skipped=[]
    for source_name,dest_rel in MAPPING.items():
        source=evidence_dir/source_name
        destination=ROOT/dest_rel
        if not source.is_file():
            if source_name=="kg001_visual_capture_v117.json" and not visual_requested:
                skipped.append(source_name)
                continue
            raise RuntimeError(
                f"required promotion evidence missing: {source_name}"
            )
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        copied.append({
            "source":str(source.relative_to(ROOT)).replace("\\","/"),
            "destination":dest_rel,
        })

    return {
        "schema":"openazrael.kg001.evidence_promotion",
        "version":118,
        "status":"PASS",
        "candidate_status":"PASS",
        "fresh_checkout_status":"PASS",
        "visual_capture_requested":visual_requested,
        "visual_capture_status":candidate.get("visual_capture"),
        "candidate2_asset_set":"PASS",
        "copied":copied,
        "skipped":skipped,
        "note":(
            "Promotion intentionally occurs after fresh-checkout cleanliness "
            "evidence and may make the tracked checkout dirty."
        ),
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir",type=Path,default=DEFAULT_EVIDENCE)
    args=ap.parse_args()
    try:
        result=promote_results(args.evidence_dir)
    except Exception as exc:
        print(
            json.dumps({
                "schema":"openazrael.kg001.evidence_promotion",
                "version":118,
                "status":"FAIL",
                "error":str(exc),
            },indent=2)
        )
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
