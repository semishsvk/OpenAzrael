from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.openazrael_adapters.physical_pppv import (
    adapt_physical_traversal_contract,
)
from tools.remaster_framework.validation import (
    RuntimeEvidence,
    build_evaluation_report,
)


SCHEMA = "openazrael.v117.pppv_bridge"
VERSION = 1


def _runtime_evidence(payload: dict[str, Any]) -> list[RuntimeEvidence]:
    bundle = payload.get("pppv_evidence", {})
    if not isinstance(bundle, dict):
        return []
    rows = bundle.get("events", [])
    if not isinstance(rows, list):
        return []
    return [
        RuntimeEvidence.from_dict(row)
        for row in rows
        if isinstance(row, dict)
    ]


def _scenario_evidence(
    scenario,
    evidence: list[RuntimeEvidence],
) -> list[RuntimeEvidence]:
    action_ids = {action.action_id for action in scenario.actions}

    if scenario.scenario_id == "openazrael.r1.floor_traversal":
        return [
            item
            for item in evidence
            if str(item.payload.get("action_id", "")) in action_ids
        ]

    meshes = {
        str(action.parameters.get("mesh", ""))
        for action in scenario.actions
        if action.parameters.get("mesh")
    }
    if meshes:
        return [
            item
            for item in evidence
            if (
                str(item.payload.get("mesh", "")) in meshes
                or (
                    item.kind == "player_action"
                    and str(item.payload.get("action_id", "")) in action_ids
                    and str(item.payload.get("mesh", "")) in meshes
                )
            )
        ]

    return evidence


def evaluate_v117_bridge(
    runtime_payload: dict[str, Any],
    contract_payload: dict[str, Any],
) -> dict[str, Any]:
    scenarios = adapt_physical_traversal_contract(contract_payload)
    evidence = _runtime_evidence(runtime_payload)

    scenario_reports = []
    for scenario in scenarios:
        scenario_evidence = _scenario_evidence(scenario, evidence)
        report = build_evaluation_report(
            scenario,
            scenario_evidence,
            {},
            {},
        )
        scenario_reports.append({
            "scenario_id": scenario.scenario_id,
            "status": report["status"],
            "errors": report["errors"],
            "evidence_count": report["evidence_count"],
            "execution_profile": "v117_real_geometry_input",
            "guarded_replay": False,
        })

    legacy_status = str(runtime_payload.get("status", "UNKNOWN")).upper()
    generic_pass = bool(scenario_reports) and all(
        row["status"] == "PASS"
        for row in scenario_reports
    )
    status = (
        "BRIDGE_PASS"
        if legacy_status == "PASS" and generic_pass
        else "BRIDGE_FAIL"
    )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "legacy_runtime_status": legacy_status,
        "generic_scenarios": scenario_reports,
        "execution_profile": (
            "legacy_v117_input_motion_with_direct_test_setup_orientation"
        ),
        "final_pppv_oracle": False,
        "scenario_evidence_isolated": True,
        "boundary": (
            "This bridge proves that the v117 real-geometry, real-Input "
            "measurements satisfy the generic physical-traversal contracts "
            "with evidence isolated per scenario. The legacy runner still "
            "places/orients the player directly for test setup, so these rows "
            "are explicitly marked unguarded_replay and do not replace the "
            "guarded chained PPPV oracle."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate v117 runtime evidence against generic PPPV scenarios."
    )
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate_v117_bridge(
        _load(args.runtime),
        _load(args.contract),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "BRIDGE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
