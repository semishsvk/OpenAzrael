from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


COVERAGE_SCHEMA = "remaster.validation_coverage"
COVERAGE_VERSION = 1


def _required_targets(reference_graph: dict[str, Any]) -> list[str]:
    targets = []
    for node in reference_graph.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("kind") == "gameplay_graph":
            node_id = str(node.get("node_id", ""))
            if node_id:
                targets.append(node_id)
    return sorted(set(targets), key=str.casefold)


def _scenario_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if bundle.get("schema") == "openazrael.pppv_scenario_bundle":
        rows = bundle.get("scenarios", [])
    elif bundle.get("schema") == "remaster.validation_scenario":
        rows = [bundle]
    else:
        rows = bundle.get("scenarios", [])
    return [row for row in rows if isinstance(row, dict)]


def audit_validation_coverage(
    reference_graph: dict[str, Any],
    scenario_bundle: dict[str, Any],
) -> dict[str, Any]:
    required = _required_targets(reference_graph)
    scenarios = _scenario_rows(scenario_bundle)

    covered_by: dict[str, list[str]] = {}
    declared_targets: set[str] = set()
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id", ""))
        metadata = scenario.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        targets = metadata.get("coverage_targets", [])
        if not isinstance(targets, list):
            targets = []
        for raw_target in targets:
            target = str(raw_target)
            if not target:
                continue
            declared_targets.add(target)
            covered_by.setdefault(target, []).append(scenario_id)

    required_set = set(required)
    covered_required = sorted(
        [target for target in required if target in covered_by],
        key=str.casefold,
    )
    uncovered = sorted(required_set - set(covered_required), key=str.casefold)
    extra = sorted(declared_targets - required_set, key=str.casefold)

    ratio = (
        float(len(covered_required)) / float(len(required))
        if required
        else 1.0
    )
    return {
        "schema": COVERAGE_SCHEMA,
        "version": COVERAGE_VERSION,
        "required_target_count": len(required),
        "covered_target_count": len(covered_required),
        "coverage_ratio": ratio,
        "required_targets": required,
        "covered_targets": [
            {
                "target": target,
                "scenarios": sorted(covered_by[target], key=str.casefold),
            }
            for target in covered_required
        ],
        "uncovered_targets": uncovered,
        "declared_targets_not_in_reference_graph": extra,
        "status": "COMPLETE" if not uncovered else "INCOMPLETE",
        "boundary": (
            "Coverage proves that every required reference-graph target has at "
            "least one declared PPPV scenario. It does not prove those runtime "
            "scenarios pass."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit PPPV scenario coverage against a reference graph."
    )
    parser.add_argument("--reference-graph", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit non-zero when any required gameplay target is uncovered.",
    )
    args = parser.parse_args()

    report = audit_validation_coverage(
        _load(args.reference_graph),
        _load(args.scenarios),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if args.require_complete and report["status"] != "COMPLETE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
