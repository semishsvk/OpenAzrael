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
from tools.openazrael_adapters.r7_pppv import build_r7_switchboard_scenarios
from tools.openazrael_adapters.r8_pppv import build_r8_interaction_scenarios
from tools.openazrael_adapters.transition_pppv import build_transition_scenarios
from tools.openazrael_adapters.demo_playthrough_plan import (
    build_openazrael_demo_playthrough_plan,
)
from tools.remaster_framework.build_provenance import (
    build_provenance,
    sha256_file,
)
from tools.remaster_framework.coverage import audit_validation_coverage
from tools.remaster_framework.evaluate_playthrough import (
    evaluate_playthrough_bundle,
)
from tools.remaster_framework.playthrough_consistency import (
    audit_playthrough_consistency,
)
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
    scenarios.extend(build_r7_switchboard_scenarios())
    scenarios.extend(build_r8_interaction_scenarios())
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

    contract_path = root / "data/kg001_acceptance_contract.json"

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

    playthrough_plan = build_openazrael_demo_playthrough_plan(scenarios)
    playthrough_plan_path = evidence / "pppv_playthrough_plan.json"
    _write(playthrough_plan_path, playthrough_plan)
    playthrough_consistency = audit_playthrough_consistency(
        playthrough_plan,
        scenarios,
    )
    playthrough_consistency_path = (
        evidence / "pppv_playthrough_consistency.json"
    )
    _write(playthrough_consistency_path, playthrough_consistency)

    pppv_suite_path = evidence / "kg001_pppv_scenario_suite.json"
    pppv_suite_integrity_path = evidence / "pppv_scenario_suite_integrity.json"
    if pppv_suite_path.is_file():
        suite_payload = _load(pppv_suite_path)
        expected_bundle_sha256 = sha256_file(scenario_bundle_output)
        actual_bundle_sha256 = str(
            suite_payload.get("scenario_bundle_sha256", "")
        )
        expected_ids = sorted(
            str(row.get("scenario_id", ""))
            for row in scenarios.get("scenarios", [])
            if isinstance(row, dict) and row.get("scenario_id")
        )
        suite_rows = suite_payload.get("scenarios", {})
        actual_ids = (
            sorted(str(value) for value in suite_rows.keys())
            if isinstance(suite_rows, dict)
            else []
        )
        expected_transition_ids = sorted(
            value
            for value in expected_ids
            if value.startswith("openazrael.transition.")
        )
        expected_bridge_ids = sorted(
            str(row.get("scenario_id", ""))
            for row in scenarios.get("scenarios", [])
            if (
                isinstance(row, dict)
                and row.get("scenario_id")
                and isinstance(row.get("metadata"), dict)
                and row["metadata"].get("execution_profile")
                == "v117_real_geometry_input"
            )
        )
        expected_guarded_ids = sorted(
            value for value in expected_ids if value not in expected_bridge_ids
        )
        actual_transition_ids = sorted(
            str(value)
            for value in suite_payload.get("transition_scenario_ids", [])
        )
        integrity_errors: list[str] = []
        if actual_bundle_sha256 != expected_bundle_sha256:
            integrity_errors.append(
                "scenario bundle SHA-256 mismatch: "
                f"{actual_bundle_sha256} != {expected_bundle_sha256}"
            )
        if actual_ids != expected_ids:
            integrity_errors.append(
                "executed scenario ID set does not match current bundle"
            )
        if int(suite_payload.get("scenario_count", -1)) != len(expected_ids):
            integrity_errors.append(
                "scenario_count does not match current bundle"
            )
        if actual_transition_ids != expected_transition_ids:
            integrity_errors.append(
                "executed transition scenario set does not match current bundle"
            )

        actual_bridge_ids = sorted(
            scenario_id
            for scenario_id, row in (
                suite_rows.items() if isinstance(suite_rows, dict) else []
            )
            if (
                isinstance(row, dict)
                and row.get("execution_profile") == "v117_real_geometry_input"
            )
        )
        actual_guarded_ids = sorted(
            scenario_id
            for scenario_id, row in (
                suite_rows.items() if isinstance(suite_rows, dict) else []
            )
            if (
                isinstance(row, dict)
                and row.get("execution_profile") == "guarded_generic_runtime"
                and row.get("guarded_replay") is True
            )
        )
        if actual_bridge_ids != expected_bridge_ids:
            integrity_errors.append(
                "v117 bridge scenario set does not match declared profiles"
            )
        if actual_guarded_ids != expected_guarded_ids:
            integrity_errors.append(
                "guarded scenario set does not match declared profiles"
            )
        if suite_payload.get("all_transition_scenarios_guarded") is not True:
            integrity_errors.append(
                "not all transition scenarios used guarded replay"
            )
        if suite_payload.get("all_authored_scenarios_executed") is not True:
            integrity_errors.append(
                "suite did not execute every authored scenario"
            )
        if int(suite_payload.get("passed", -1)) != len(expected_ids):
            integrity_errors.append(
                "suite passed count does not match current scenario count"
            )
        if int(suite_payload.get("failed", -1)) != 0:
            integrity_errors.append(
                "suite reports one or more failed scenarios"
            )
        if int(suite_payload.get("guarded_scenario_count", -1)) != len(
            expected_guarded_ids
        ):
            integrity_errors.append(
                "guarded scenario count does not match declared profiles"
            )
        if int(suite_payload.get("v117_bridge_scenario_count", -1)) != len(
            expected_bridge_ids
        ):
            integrity_errors.append(
                "v117 bridge scenario count does not match declared profiles"
            )
        if int(suite_payload.get("transition_scenario_count", -1)) != len(
            expected_transition_ids
        ):
            integrity_errors.append(
                "transition scenario count does not match current bundle"
            )
        if isinstance(suite_rows, dict):
            non_passing_ids = sorted(
                str(scenario_id)
                for scenario_id, row in suite_rows.items()
                if not isinstance(row, dict) or row.get("status") != "PASS"
            )
        else:
            non_passing_ids = expected_ids
        if non_passing_ids:
            integrity_errors.append(
                "suite contains non-PASS scenario rows: "
                + ", ".join(non_passing_ids)
            )

        suite_integrity = {
            "schema": "openazrael.kg001.pppv_scenario_suite_integrity",
            "version": 1,
            "status": "PASS" if not integrity_errors else "FAIL",
            "scenario_bundle_sha256": expected_bundle_sha256,
            "runtime_scenario_bundle_sha256": actual_bundle_sha256,
            "expected_scenario_count": len(expected_ids),
            "executed_scenario_count": len(actual_ids),
            "expected_scenario_ids": expected_ids,
            "executed_scenario_ids": actual_ids,
            "expected_transition_scenario_ids": expected_transition_ids,
            "executed_transition_scenario_ids": actual_transition_ids,
            "expected_v117_bridge_scenario_ids": expected_bridge_ids,
            "executed_v117_bridge_scenario_ids": actual_bridge_ids,
            "expected_guarded_scenario_ids": expected_guarded_ids,
            "executed_guarded_scenario_ids": actual_guarded_ids,
            "non_passing_scenario_ids": non_passing_ids,
            "errors": integrity_errors,
        }
        _write(pppv_suite_integrity_path, suite_integrity)
    else:
        pppv_suite_integrity_path.unlink(missing_ok=True)

    playthrough_runtime_path = evidence / "kg001_pppv_playthrough.json"
    playthrough_evaluation_path: Path | None = None
    playthrough_runtime_status = "NOT_AVAILABLE"
    playthrough_evaluation_status = "NOT_AVAILABLE"
    if playthrough_runtime_path.is_file():
        runtime_payload = _load(playthrough_runtime_path)
        runtime_plan = runtime_payload.get("plan")
        if not isinstance(runtime_plan, dict):
            raise ValueError(
                "PPPV playthrough runtime is missing embedded plan"
            )
        runtime_plan_sha256 = str(runtime_plan.get("plan_sha256", ""))
        expected_plan_sha256 = str(playthrough_plan.get("plan_sha256", ""))
        if runtime_plan_sha256 != expected_plan_sha256:
            raise ValueError(
                "PPPV playthrough runtime plan hash does not match "
                "the current candidate plan"
            )
        playthrough_runtime_status = str(
            runtime_payload.get("status", "UNKNOWN")
        )
        playthrough_evaluation = evaluate_playthrough_bundle(runtime_payload)
        playthrough_evaluation_path = (
            evidence / "kg001_pppv_playthrough_evaluation.json"
        )
        _write(playthrough_evaluation_path, playthrough_evaluation)
        playthrough_evaluation_status = str(
            playthrough_evaluation.get("status", "UNKNOWN")
        )

    determinism_path = evidence / "kg001_pppv_determinism.json"
    determinism_integrity_path = evidence / "pppv_determinism_integrity.json"
    repeat2_evaluation_path = (
        evidence / "kg001_pppv_playthrough_repeat2_evaluation.json"
    )
    determinism_integrity_status = "NOT_AVAILABLE"

    if determinism_path.is_file():
        determinism_payload = _load(determinism_path)
        determinism_errors: list[str] = []
        expected_plan_sha256 = str(playthrough_plan.get("plan_sha256", ""))
        expected_plan_document_sha256 = sha256_file(playthrough_plan_path)
        expected_scenario_bundle_sha256 = sha256_file(
            scenario_bundle_output
        )

        if str(determinism_payload.get("status", "")) != "PASS":
            determinism_errors.append(
                "determinism summary status is not PASS"
            )
        if int(determinism_payload.get("repeat_count", 0)) < 2:
            determinism_errors.append(
                "determinism summary requires at least two runs"
            )
        if determinism_payload.get("all_runs_pass") is not True:
            determinism_errors.append(
                "not all determinism runs passed"
            )
        if determinism_payload.get("semantic_replay_match") is not True:
            determinism_errors.append(
                "semantic replay fingerprints do not match"
            )
        if determinism_payload.get("final_state_match") is not True:
            determinism_errors.append(
                "final state hashes do not match"
            )
        if (
            str(determinism_payload.get("plan_sha256", ""))
            != expected_plan_sha256
        ):
            determinism_errors.append(
                "determinism plan SHA-256 does not match current plan"
            )
        if (
            str(determinism_payload.get("plan_document_sha256", ""))
            != expected_plan_document_sha256
        ):
            determinism_errors.append(
                "determinism plan document SHA-256 mismatch"
            )
        if (
            str(determinism_payload.get("scenario_bundle_sha256", ""))
            != expected_scenario_bundle_sha256
        ):
            determinism_errors.append(
                "determinism scenario bundle SHA-256 mismatch"
            )

        canonical_evaluation_file = (
            evidence / "kg001_pppv_playthrough_evaluation.json"
        )
        evaluation_rows: list[dict[str, Any]] = []
        for label, evaluation_file in (
            ("run1", canonical_evaluation_file),
            ("run2", repeat2_evaluation_path),
        ):
            if not evaluation_file.is_file():
                determinism_errors.append(
                    f"{label} playthrough evaluation is missing"
                )
                continue
            evaluation_payload = _load(evaluation_file)
            evaluation_rows.append({
                "label": label,
                "path": evaluation_file.name,
                "status": str(evaluation_payload.get("status", "")),
                "plan_sha256": str(
                    evaluation_payload.get("plan_sha256", "")
                ),
                "semantic_replay_sha256": str(
                    evaluation_payload.get("semantic_replay_sha256", "")
                ),
                "final_state_sha256": str(
                    evaluation_payload.get("final_state_sha256", "")
                ),
            })
            if str(evaluation_payload.get("status", "")) != "PASS":
                determinism_errors.append(
                    f"{label} playthrough evaluation is not PASS"
                )
            if (
                str(evaluation_payload.get("plan_sha256", ""))
                != expected_plan_sha256
            ):
                determinism_errors.append(
                    f"{label} evaluation plan SHA-256 mismatch"
                )

        if len(evaluation_rows) == 2:
            semantic_hashes = [
                row["semantic_replay_sha256"] for row in evaluation_rows
            ]
            final_hashes = [
                row["final_state_sha256"] for row in evaluation_rows
            ]
            if not all(semantic_hashes):
                determinism_errors.append(
                    "evaluation semantic replay SHA-256 is missing"
                )
            elif len(set(semantic_hashes)) != 1:
                determinism_errors.append(
                    "independent evaluation semantic replay hashes differ"
                )
            if not all(final_hashes):
                determinism_errors.append(
                    "evaluation final state SHA-256 is missing"
                )
            elif len(set(final_hashes)) != 1:
                determinism_errors.append(
                    "independent evaluation final state hashes differ"
                )

            summary_semantic = determinism_payload.get(
                "semantic_replay_sha256", []
            )
            if (
                not isinstance(summary_semantic, list)
                or summary_semantic != semantic_hashes
            ):
                determinism_errors.append(
                    "determinism summary semantic replay hashes "
                    "do not match evaluation artifacts"
                )

            summary_final = determinism_payload.get(
                "final_state_sha256", []
            )
            if (
                not isinstance(summary_final, list)
                or summary_final != final_hashes
            ):
                determinism_errors.append(
                    "determinism summary final state hashes "
                    "do not match evaluation artifacts"
                )

        determinism_integrity_status = (
            "PASS" if not determinism_errors else "FAIL"
        )
        determinism_integrity = {
            "schema": "openazrael.kg001.pppv_determinism_integrity",
            "version": 1,
            "status": determinism_integrity_status,
            "expected_plan_sha256": expected_plan_sha256,
            "expected_plan_document_sha256": (
                expected_plan_document_sha256
            ),
            "expected_scenario_bundle_sha256": (
                expected_scenario_bundle_sha256
            ),
            "summary_plan_sha256": str(
                determinism_payload.get("plan_sha256", "")
            ),
            "summary_plan_document_sha256": str(
                determinism_payload.get("plan_document_sha256", "")
            ),
            "summary_scenario_bundle_sha256": str(
                determinism_payload.get("scenario_bundle_sha256", "")
            ),
            "evaluations": evaluation_rows,
            "errors": determinism_errors,
        }
        _write(determinism_integrity_path, determinism_integrity)
    else:
        determinism_integrity_path.unlink(missing_ok=True)

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

    gate_results = build_gate_results(
        root,
        evidence,
        commit_sha=commit_sha,
        manual_path=manual_path,
    )
    gate_results_path = evidence / "kg001_release_gate_results.json"
    _write(gate_results_path, gate_results)

    release_summary = aggregate_release(
        _load(contract_path),
        gate_results,
    )
    release_summary_path = evidence / "release_gate_summary.json"
    _write(release_summary_path, release_summary)

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
    inputs["pppv_playthrough_plan"] = sha256_file(playthrough_plan_path)
    inputs["pppv_playthrough_consistency"] = sha256_file(
        playthrough_consistency_path
    )
    if playthrough_runtime_path.is_file():
        inputs["pppv_playthrough_runtime"] = sha256_file(
            playthrough_runtime_path
        )
    if playthrough_evaluation_path is not None:
        inputs["pppv_playthrough_evaluation"] = sha256_file(
            playthrough_evaluation_path
        )
    if v117_bridge_path is not None:
        inputs["v117_pppv_bridge"] = sha256_file(v117_bridge_path)
    well_pppv_path = evidence / "kg001_well_tongs_pppv.json"
    if well_pppv_path.is_file():
        inputs["well_tongs_real_input_pppv"] = sha256_file(well_pppv_path)
    if pppv_suite_path.is_file():
        inputs["pppv_scenario_suite"] = sha256_file(pppv_suite_path)
    if pppv_suite_integrity_path.is_file():
        inputs["pppv_scenario_suite_integrity"] = sha256_file(
            pppv_suite_integrity_path
        )
    if determinism_path.is_file():
        inputs["pppv_determinism"] = sha256_file(determinism_path)
    if determinism_integrity_path.is_file():
        inputs["pppv_determinism_integrity"] = sha256_file(
            determinism_integrity_path
        )
    if repeat2_evaluation_path.is_file():
        inputs["pppv_playthrough_repeat2_evaluation"] = sha256_file(
            repeat2_evaluation_path
        )

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
            "pppv_playthrough_plan_status": playthrough_plan["status"],
            "pppv_playthrough_consistency_status": (
                playthrough_consistency["status"]
            ),
            "pppv_scenario_suite_status": (
                str(_load(pppv_suite_path).get("status", "UNKNOWN"))
                if pppv_suite_path.is_file()
                else "NOT_AVAILABLE"
            ),
            "pppv_scenario_suite_integrity_status": (
                str(_load(pppv_suite_integrity_path).get("status", "UNKNOWN"))
                if pppv_suite_integrity_path.is_file()
                else "NOT_AVAILABLE"
            ),
            "pppv_playthrough_runtime_status": playthrough_runtime_status,
            "pppv_playthrough_evaluation_status": (
                playthrough_evaluation_status
            ),
            "pppv_determinism_status": (
                str(_load(determinism_path).get("status", "UNKNOWN"))
                if determinism_path.is_file()
                else "NOT_AVAILABLE"
            ),
            "pppv_determinism_integrity_status": (
                determinism_integrity_status
            ),
        },
    )
    provenance_path = evidence / "build_provenance.json"
    _write(provenance_path, provenance)

    artifacts = {
        "gate_results": gate_results_path.name,
        "release_gate_summary": release_summary_path.name,
        "pppv_scenarios": scenario_bundle_output.name,
        "pppv_coverage": pppv_coverage_path.name,
        "pppv_playthrough_plan": playthrough_plan_path.name,
        "pppv_playthrough_consistency": playthrough_consistency_path.name,
        "build_provenance": provenance_path.name,
    }
    if playthrough_runtime_path.is_file():
        artifacts["pppv_playthrough_runtime"] = playthrough_runtime_path.name
    if playthrough_evaluation_path is not None:
        artifacts["pppv_playthrough_evaluation"] = (
            playthrough_evaluation_path.name
        )
    if v117_bridge_path is not None:
        artifacts["v117_pppv_bridge"] = v117_bridge_path.name
    if well_pppv_path.is_file():
        artifacts["well_tongs_real_input_pppv"] = well_pppv_path.name
    if pppv_suite_path.is_file():
        artifacts["pppv_scenario_suite"] = pppv_suite_path.name
    if pppv_suite_integrity_path.is_file():
        artifacts["pppv_scenario_suite_integrity"] = (
            pppv_suite_integrity_path.name
        )
    if determinism_path.is_file():
        artifacts["pppv_determinism"] = determinism_path.name
    if determinism_integrity_path.is_file():
        artifacts["pppv_determinism_integrity"] = (
            determinism_integrity_path.name
        )
    if repeat2_evaluation_path.is_file():
        artifacts["pppv_playthrough_repeat2_evaluation"] = (
            repeat2_evaluation_path.name
        )

    bundle = {
        "schema": "openazrael.kg001.framework_bundle",
        "version": 1,
        "commit_sha": commit_sha,
        "release_status": release_summary["status"],
        "pppv_coverage_status": pppv_coverage["status"],
        "pppv_playthrough_plan_status": playthrough_plan["status"],
        "pppv_playthrough_consistency_status": (
            playthrough_consistency["status"]
        ),
        "pppv_scenario_suite_status": (
            str(_load(pppv_suite_path).get("status", "UNKNOWN"))
            if pppv_suite_path.is_file()
            else "NOT_AVAILABLE"
        ),
        "pppv_scenario_suite_integrity_status": (
            str(_load(pppv_suite_integrity_path).get("status", "UNKNOWN"))
            if pppv_suite_integrity_path.is_file()
            else "NOT_AVAILABLE"
        ),
        "pppv_playthrough_runtime_status": playthrough_runtime_status,
        "pppv_playthrough_evaluation_status": (
            playthrough_evaluation_status
        ),
        "pppv_determinism_status": (
            str(_load(determinism_path).get("status", "UNKNOWN"))
            if determinism_path.is_file()
            else "NOT_AVAILABLE"
        ),
        "pppv_determinism_integrity_status": (
            determinism_integrity_status
        ),
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
