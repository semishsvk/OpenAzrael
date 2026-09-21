from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tools.openazrael_adapters.kg001_release_evidence import build_gate_results
from tools.openazrael_adapters.physical_pppv import (
    adapt_physical_traversal_contract,
)
from tools.openazrael_adapters.well_pppv import adapt_well_tongs_contract
from tools.openazrael_adapters.v117_pppv_bridge import evaluate_v117_bridge
from tools.openazrael_adapters.reference_graph import (
    build_openazrael_reference_graph,
)
from tools.openazrael_adapters.r1_pppv import build_r1_interaction_scenarios
from tools.openazrael_adapters.transition_pppv import build_transition_scenarios
from tools.remaster_framework.build_provenance import (
    build_provenance,
    sha256_file,
)
from tools.remaster_framework.coverage import audit_validation_coverage
from tools.remaster_framework.release import aggregate_release


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _project_version(project_godot: Path) -> str:
    text = project_godot.read_text(encoding="utf-8")
    match = re.search(r'^config/version="([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "UNKNOWN"


def _optional_hash(path: Path, inputs: dict[str, str], key: str) -> None:
    if path.is_file():
        inputs[key] = sha256_file(path)


def _default_scenario_bundle(root: Path) -> dict[str, Any]:
    scenarios = list(build_r1_interaction_scenarios())
    scenarios.extend(build_transition_scenarios())
    physical = root / "data/tests/kg001_physical_traversal_contract_v117.json"
    if physical.is_file():
        scenarios.extend(
            adapt_physical_traversal_contract(_load(physical))
        )
    well = root / "data/tests/kg001_well_tongs_animation_contract_v118.json"
    if well.is_file():
        scenarios.extend(adapt_well_tongs_contract(_load(well)))
    return {
        "schema": "openazrael.pppv_scenario_bundle",
        "version": 1,
        "scenario_count": len(scenarios),
        "scenarios": [scenario.to_dict() for scenario in scenarios],
    }


def build_candidate_framework_bundle(
    repo_root: Path,
    evidence_root: Path,
    *,
    commit_sha: str,
    godot_version: str,
    manual_path: Path | None = None,
    scenario_bundle_path: Path | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    evidence = evidence_root.resolve()
    evidence.mkdir(parents=True, exist_ok=True)

    gate_results = build_gate_results(
        root,
        evidence,
        commit_sha=commit_sha,
        manual_path=manual_path,
    )
    gate_results_path = evidence / "kg001_release_gate_results.json"
    _write(gate_results_path, gate_results)

    contract_path = root / "data/kg001_acceptance_contract.json"
    release_summary = aggregate_release(
        _load(contract_path),
        gate_results,
    )
    release_summary_path = evidence / "release_gate_summary.json"
    _write(release_summary_path, release_summary)

    reference_graph = build_openazrael_reference_graph(
        root / "data/xaf_trigger_evidence.json",
        root / "data/gameplay_event_graph_v87.json",
    ).to_dict()
    scenarios = (
        _load(scenario_bundle_path)
        if scenario_bundle_path is not None and scenario_bundle_path.is_file()
        else _default_scenario_bundle(root)
    )
    scenario_bundle_output = evidence / "pppv_scenarios.json"
    _write(scenario_bundle_output, scenarios)
    pppv_coverage = audit_validation_coverage(reference_graph, scenarios)
    pppv_coverage_path = evidence / "pppv_coverage.json"
    _write(pppv_coverage_path, pppv_coverage)

    v117_bridge_path: Path | None = None
    v117_runtime_path = evidence / "kg001_v117_runtime.json"
    if not v117_runtime_path.is_file():
        alternate = evidence / "kg001_physical_traversal_runtime_v117.json"
        if alternate.is_file():
            v117_runtime_path = alternate
    if v117_runtime_path.is_file():
        v117_runtime = _load(v117_runtime_path)
        runtime_evidence = v117_runtime.get("pppv_evidence")
        v117_contract_path = (
            root / "data/tests/kg001_physical_traversal_contract_v117.json"
        )
        if isinstance(runtime_evidence, dict) and v117_contract_path.is_file():
            v117_contract = _load(v117_contract_path)
            v117_bridge = evaluate_v117_bridge(
                v117_runtime,
                v117_contract,
            )
            v117_bridge_path = evidence / "v117_pppv_bridge.json"
            _write(v117_bridge_path, v117_bridge)

    inputs: dict[str, str] = {}
    _optional_hash(
        root / "data/backup/source_fingerprints.json",
        inputs,
        "source_fingerprints",
    )
    _optional_hash(
        root / "tools/remaster_framework/tool_manifest.json",
        inputs,
        "tool_registry",
    )
    _optional_hash(contract_path, inputs, "kg001_acceptance_contract")
    _optional_hash(
        evidence / "kg001_candidate_v112.json",
        inputs,
        "candidate_run",
    )
    inputs["release_gate_results"] = sha256_file(gate_results_path)
    inputs["release_gate_summary"] = sha256_file(release_summary_path)
    inputs["pppv_scenarios"] = sha256_file(scenario_bundle_output)
    inputs["pppv_coverage"] = sha256_file(pppv_coverage_path)
    if v117_bridge_path is not None:
        inputs["v117_pppv_bridge"] = sha256_file(v117_bridge_path)
    well_pppv_path = evidence / "kg001_well_tongs_pppv.json"
    if well_pppv_path.is_file():
        inputs["well_tongs_real_input_pppv"] = sha256_file(well_pppv_path)

    provenance = build_provenance(
        project="OpenAzrael",
        commit_sha=commit_sha,
        project_version=_project_version(root / "project.godot"),
        engine={
            "name": "Godot",
            "version": godot_version or "UNKNOWN",
        },
        inputs=inputs,
        metadata={
            "candidate": "KG-001 Candidate 1",
            "target_tag": "demo-known-good-001",
            "release_status": release_summary["status"],
            "pppv_coverage_status": pppv_coverage["status"],
        },
    )
    provenance_path = evidence / "build_provenance.json"
    _write(provenance_path, provenance)

    artifacts = {
        "gate_results": gate_results_path.name,
        "release_gate_summary": release_summary_path.name,
        "pppv_scenarios": scenario_bundle_output.name,
        "pppv_coverage": pppv_coverage_path.name,
        "build_provenance": provenance_path.name,
    }
    if v117_bridge_path is not None:
        artifacts["v117_pppv_bridge"] = v117_bridge_path.name
    if well_pppv_path.is_file():
        artifacts["well_tongs_real_input_pppv"] = well_pppv_path.name

    bundle = {
        "schema": "openazrael.kg001.framework_bundle",
        "version": 1,
        "commit_sha": commit_sha,
        "release_status": release_summary["status"],
        "pppv_coverage_status": pppv_coverage["status"],
        "well_tongs_real_input_pppv_status": (
            str(_load(well_pppv_path).get("status", ""))
            if well_pppv_path.is_file()
            else "NOT_AVAILABLE"
        ),
        "artifacts": artifacts,
        "known_good_eligible": (
            release_summary["status"] == "ELIGIBLE_FOR_KNOWN_GOOD"
        ),
    }
    _write(evidence / "kg001_framework_bundle.json", bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-safe KG-001 framework evidence bundle."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--godot-version", default="")
    parser.add_argument("--manual", type=Path)
    parser.add_argument("--pppv-scenarios", type=Path)
    args = parser.parse_args()

    bundle = build_candidate_framework_bundle(
        args.repo_root,
        args.evidence_root,
        commit_sha=args.commit_sha,
        godot_version=args.godot_version,
        manual_path=args.manual,
        scenario_bundle_path=args.pppv_scenarios,
    )
    print(json.dumps(bundle, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
