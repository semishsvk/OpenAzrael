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


RUNTIME_BUNDLE_SCHEMA = "remaster.runtime_validation_bundle"


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _evidence_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("events", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("evidence JSON must be a list or an object with events")
    if not isinstance(rows, list):
        raise ValueError("evidence events must be a list")
    return [item for item in rows if isinstance(item, dict)]


def evaluate_runtime_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != RUNTIME_BUNDLE_SCHEMA:
        raise ValueError("unsupported runtime validation bundle schema")

    scenario_payload = payload.get("scenario")
    if not isinstance(scenario_payload, dict):
        raise ValueError("runtime bundle scenario must be an object")
    scenario = ValidationScenario.from_dict(scenario_payload)

    evidence_payload = payload.get("evidence", {})
    evidence = [
        RuntimeEvidence.from_dict(item)
        for item in _evidence_rows(evidence_payload)
    ]

    before_state = payload.get("before_state")
    after_state = payload.get("after_state")
    if not isinstance(before_state, dict) or not isinstance(after_state, dict):
        raise ValueError("runtime bundle before_state/after_state must be objects")

    report = build_evaluation_report(
        scenario,
        evidence,
        before_state,
        after_state,
    )
    execution_status = str(payload.get("status", ""))
    execution_failures = payload.get("failures", [])
    if execution_status != "EXECUTION_PASS":
        report["errors"] = list(report["errors"]) + [
            f"runtime execution status: {execution_status or 'UNKNOWN'}"
        ]
        if isinstance(execution_failures, list):
            report["errors"].extend(
                f"runtime execution failure: {item}"
                for item in execution_failures
            )
        report["status"] = "FAIL"

    report["runtime_execution_status"] = execution_status
    report["runtime_execution_failures"] = (
        list(execution_failures)
        if isinstance(execution_failures, list)
        else []
    )
    return report


def _evaluate_split_inputs(args: argparse.Namespace) -> dict[str, Any]:
    required = {
        "--scenario": args.scenario,
        "--evidence": args.evidence,
        "--before-state": args.before_state,
        "--after-state": args.after_state,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(
            "split-input mode requires " + ", ".join(required.keys())
        )

    scenario = ValidationScenario.from_dict(_load_object(args.scenario))
    evidence_payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    evidence = [
        RuntimeEvidence.from_dict(item)
        for item in _evidence_rows(evidence_payload)
    ]
    before_state = _load_object(args.before_state)
    after_state = _load_object(args.after_state)
    return build_evaluation_report(
        scenario,
        evidence,
        before_state,
        after_state,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate reusable PPPV scenarios against runtime evidence."
    )
    parser.add_argument("--runtime-bundle", type=Path)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--before-state", type=Path)
    parser.add_argument("--after-state", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.runtime_bundle is not None:
        if any(
            value is not None
            for value in (
                args.scenario,
                args.evidence,
                args.before_state,
                args.after_state,
            )
        ):
            parser.error(
                "--runtime-bundle cannot be combined with split-input arguments"
            )
        report = evaluate_runtime_bundle(_load_object(args.runtime_bundle))
    else:
        try:
            report = _evaluate_split_inputs(args)
        except ValueError as exc:
            parser.error(str(exc))

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
