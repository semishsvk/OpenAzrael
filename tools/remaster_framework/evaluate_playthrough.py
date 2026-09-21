from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evaluate_validation import evaluate_runtime_bundle
from .playthrough import validate_checkpoint_roundtrip


RUNTIME_SCHEMA = "remaster.runtime_playthrough_bundle"
EVALUATION_SCHEMA = "remaster.playthrough_evaluation"
EVALUATION_VERSION = 1


def evaluate_playthrough_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    step_reports: list[dict[str, Any]] = []

    if payload.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("unsupported runtime playthrough bundle schema")

    plan = payload.get("plan")
    if not isinstance(plan, dict):
        raise ValueError("playthrough plan must be an object")
    planned_steps = plan.get("steps", [])
    actual_steps = payload.get("steps", [])
    if not isinstance(planned_steps, list) or not isinstance(actual_steps, list):
        raise ValueError("playthrough steps must be lists")

    runtime_status = str(payload.get("status", ""))
    if runtime_status != "EXECUTION_PASS":
        errors.append(
            f"runtime execution status: {runtime_status or 'UNKNOWN'}"
        )
    runtime_failures = payload.get("failures", [])
    if isinstance(runtime_failures, list):
        errors.extend(
            f"runtime execution failure: {item}"
            for item in runtime_failures
        )

    if len(actual_steps) != len(planned_steps):
        errors.append(
            "playthrough step count mismatch: "
            f"{len(actual_steps)} != {len(planned_steps)}"
        )

    for index, planned in enumerate(planned_steps):
        if not isinstance(planned, dict):
            errors.append(f"plan step {index} is not an object")
            continue
        step_id = str(planned.get("step_id", ""))
        if index >= len(actual_steps):
            step_reports.append({
                "step_id": step_id,
                "status": "MISSING",
            })
            continue

        actual = actual_steps[index]
        if not isinstance(actual, dict):
            errors.append(f"{step_id}: runtime step is not an object")
            step_reports.append({
                "step_id": step_id,
                "status": "FAIL",
            })
            continue

        actual_step_id = str(actual.get("step_id", ""))
        if actual_step_id != step_id:
            errors.append(
                f"step order mismatch at {index}: "
                f"{actual_step_id!r} != {step_id!r}"
            )

        kind = str(planned.get("kind", ""))
        if kind == "checkpoint":
            checkpoint_errors: list[str] = []
            if str(actual.get("status", "")) != "PASS":
                checkpoint_errors.append(
                    f"{step_id}: checkpoint runtime status is "
                    f"{actual.get('status')!r}"
                )
            if actual.get("restore_ok") is not True:
                checkpoint_errors.append(
                    f"{step_id}: restore did not succeed"
                )

            before_hash = str(actual.get("before_state_sha256", ""))
            after_hash = str(actual.get("after_restore_sha256", ""))
            expected_hash = str(
                actual.get("expected_state_sha256", "")
            ) or None
            checkpoint_errors.extend(
                validate_checkpoint_roundtrip(
                    before_save_sha256=before_hash,
                    after_restore_sha256=after_hash,
                    expected_sha256=expected_hash,
                )
            )
            errors.extend(checkpoint_errors)
            step_reports.append({
                "step_id": step_id,
                "kind": kind,
                "status": "PASS" if not checkpoint_errors else "FAIL",
                "errors": checkpoint_errors,
                "before_state_sha256": before_hash,
                "after_restore_sha256": after_hash,
            })
            continue

        try:
            evaluation = evaluate_runtime_bundle(actual)
        except ValueError as exc:
            step_errors = [f"{step_id}: {exc}"]
            errors.extend(step_errors)
            step_reports.append({
                "step_id": step_id,
                "kind": kind,
                "status": "FAIL",
                "errors": step_errors,
            })
            continue

        if evaluation["status"] != "PASS":
            errors.extend(
                f"{step_id}: {message}"
                for message in evaluation["errors"]
            )
        step_reports.append({
            "step_id": step_id,
            "kind": kind,
            "scenario_id": evaluation["scenario_id"],
            "status": evaluation["status"],
            "errors": evaluation["errors"],
            "before_state_sha256": evaluation[
                "before_state_sha256"
            ],
            "after_state_sha256": evaluation[
                "after_state_sha256"
            ],
        })

    final_hash = str(payload.get("final_state_sha256", ""))
    expected_final = str(
        payload.get(
            "expected_final_state_sha256",
            plan.get("success_state_sha256", ""),
        )
    )
    if expected_final and final_hash != expected_final:
        errors.append(
            f"final state hash mismatch: {final_hash} != {expected_final}"
        )

    boundary = payload.get("runtime_boundary", {})
    if not isinstance(boundary, dict):
        boundary = {}
        errors.append("runtime_boundary must be an object")
    required_boundary = {
        "single_scene_instance": True,
        "state_reset_between_scenarios": False,
        "direct_interact_calls": False,
        "gameplay_teleport_during_actions": False,
    }
    for key, expected in required_boundary.items():
        if boundary.get(key) is not expected:
            errors.append(
                f"runtime boundary mismatch {key}: "
                f"{boundary.get(key)!r} != {expected!r}"
            )

    return {
        "schema": EVALUATION_SCHEMA,
        "version": EVALUATION_VERSION,
        "plan_id": plan.get("plan_id"),
        "plan_sha256": plan.get("plan_sha256"),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "runtime_execution_status": runtime_status,
        "step_count": len(step_reports),
        "steps": step_reports,
        "final_state_sha256": final_hash,
        "expected_final_state_sha256": expected_final,
        "runtime_boundary": boundary,
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a chained PPPV playthrough runtime bundle."
    )
    parser.add_argument("--runtime-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate_playthrough_bundle(_load(args.runtime_bundle))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
