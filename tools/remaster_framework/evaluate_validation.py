from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .validation import (
    RuntimeEvidence,
    ValidationScenario,
    build_evaluation_report,
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a reusable PPPV scenario against runtime evidence."
    )
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--before-state", type=Path, required=True)
    parser.add_argument("--after-state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    scenario = ValidationScenario.from_dict(_load_object(args.scenario))
    evidence_payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    if isinstance(evidence_payload, dict):
        evidence_rows = evidence_payload.get("events", [])
    elif isinstance(evidence_payload, list):
        evidence_rows = evidence_payload
    else:
        raise ValueError("evidence JSON must be a list or an object with events")

    evidence = [
        RuntimeEvidence.from_dict(item)
        for item in evidence_rows
    ]
    before_state = _load_object(args.before_state)
    after_state = _load_object(args.after_state)
    report = build_evaluation_report(
        scenario,
        evidence,
        before_state,
        after_state,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
