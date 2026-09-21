from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLAN_SCHEMA = "remaster.validation_plan"
PLAN_VERSION = 1


def _scenarios(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if bundle is None:
        return []
    if bundle.get("schema") == "remaster.validation_scenario":
        return [bundle]
    rows = bundle.get("scenarios", [])
    return [row for row in rows if isinstance(row, dict)]


def build_validation_plan(
    reference_graph: dict[str, Any],
    scenario_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nodes = {
        str(node.get("node_id")): node
        for node in reference_graph.get("nodes", [])
        if isinstance(node, dict) and node.get("node_id")
    }
    edges = [
        edge
        for edge in reference_graph.get("edges", [])
        if isinstance(edge, dict)
    ]

    covered_by: dict[str, list[str]] = {}
    for scenario in _scenarios(scenario_bundle):
        scenario_id = str(scenario.get("scenario_id", ""))
        metadata = scenario.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        for raw_target in metadata.get("coverage_targets", []):
            target = str(raw_target)
            if target:
                covered_by.setdefault(target, []).append(scenario_id)

    targets = []
    for node_id, node in sorted(nodes.items(), key=lambda item: item[0].casefold()):
        if node.get("kind") != "gameplay_graph":
            continue

        incoming = [
            edge for edge in edges
            if edge.get("target") == node_id
        ]
        outgoing = [
            edge for edge in edges
            if edge.get("source") == node_id
        ]

        rooms = sorted({
            str(edge.get("source"))
            for edge in incoming
            if edge.get("relation") == "owns_gameplay"
            and str(edge.get("source", "")).startswith("room:")
        })

        evidence_sources = sorted({
            str(edge.get("target"))
            for edge in outgoing
            if edge.get("relation") == "evidence_source"
        })

        state_effects = []
        audio_effects = []
        asset_effects = []
        for edge in outgoing:
            relation = str(edge.get("relation", ""))
            target = str(edge.get("target", ""))
            metadata = edge.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            row = {
                "target": target,
                "metadata": metadata,
            }
            if relation == "mutates_state":
                state_effects.append(row)
            elif relation == "plays_audio":
                audio_effects.append(row)
            elif relation == "references_asset":
                asset_effects.append(row)

        state_effects.sort(key=lambda row: row["target"].casefold())
        audio_effects.sort(key=lambda row: row["target"].casefold())
        asset_effects.sort(key=lambda row: row["target"].casefold())

        scenarios = sorted(covered_by.get(node_id, []), key=str.casefold)
        targets.append({
            "target_id": node_id,
            "label": node.get("label"),
            "rooms": rooms,
            "evidence_sources": evidence_sources,
            "expected_effects": {
                "state": state_effects,
                "audio": audio_effects,
                "assets": asset_effects,
            },
            "coverage_status": "COVERED" if scenarios else "UNMAPPED",
            "scenarios": scenarios,
            "authoring_requirements": [
                "identify physical player route and interaction target",
                "preserve original preconditions and inventory requirements",
                "capture trigger/interaction evidence",
                "capture every source-backed observable effect",
                "assert before/after logical state",
                "add negative/precondition scenario when meaningful",
            ],
        })

    uncovered_count = sum(
        1 for target in targets
        if target["coverage_status"] != "COVERED"
    )
    return {
        "schema": PLAN_SCHEMA,
        "version": PLAN_VERSION,
        "target_count": len(targets),
        "covered_count": len(targets) - uncovered_count,
        "unmapped_count": uncovered_count,
        "status": "COMPLETE" if uncovered_count == 0 else "AUTHORING_REQUIRED",
        "targets": targets,
        "boundary": (
            "This plan derives expected logical/audio effects from the reference "
            "graph. Physical routes and interaction semantics must be proven by "
            "game-specific evidence; they are never guessed."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a puzzle-by-puzzle PPPV authoring plan."
    )
    parser.add_argument("--reference-graph", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_validation_plan(
        _load(args.reference_graph),
        _load(args.scenarios) if args.scenarios is not None else None,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
