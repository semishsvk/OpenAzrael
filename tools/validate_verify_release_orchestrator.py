#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.remaster_framework.verify_orchestrator import GateSpec, select_plan

PROFILE = ROOT / "data/tests/openazrael_verify_release_profile_v1.json"
TOOL = ROOT / "tools/run_verify_release_orchestrator.py"
CORE = ROOT / "tools/remaster_framework/verify_orchestrator.py"
WORKFLOW = ROOT / ".github/workflows/openazrael-verify-release.yml"
MANIFEST = ROOT / "tools/remaster_framework/tool_manifest.json"
DOC = ROOT / "docs/VERIFY_RELEASE_ORCHESTRATOR.md"

required = (PROFILE, TOOL, CORE, WORKFLOW, MANIFEST, DOC)
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    print(json.dumps({
        "schema": "openazrael.verify_release_orchestrator_validation",
        "version": 1,
        "status": "FAIL",
        "failed": ["missing_files"],
        "missing": missing,
    }, indent=2))
    raise SystemExit(1)

profile = json.loads(PROFILE.read_text(encoding="utf-8"))
tool = TOOL.read_text(encoding="utf-8")
core = CORE.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
doc = DOC.read_text(encoding="utf-8")
gates = [GateSpec.from_dict(item) for item in profile.get("gates", [])]
gate_ids = [gate.gate_id for gate in gates]
by_id = {gate.gate_id: gate for gate in gates}

critical = tuple(profile.get("critical_patterns", []))
fallback = str(profile.get("fallback_gate_id", ""))

docs_plan = select_plan(
    mode="fast",
    changed_files=["docs/PROJECT_STATE.md"],
    gates=gates,
    critical_patterns=critical,
    fallback_gate_id=fallback,
)
save_plan = select_plan(
    mode="fast",
    changed_files=["scripts/legacy_save_system_v145.gd"],
    gates=gates,
    critical_patterns=critical,
    fallback_gate_id=fallback,
)
unknown_plan = select_plan(
    mode="fast",
    changed_files=["scripts/unknown_future_runtime_change.gd"],
    gates=gates,
    critical_patterns=critical,
    fallback_gate_id=fallback,
)
verify_plan = select_plan(
    mode="verify",
    changed_files=[],
    gates=gates,
    critical_patterns=critical,
    fallback_gate_id=fallback,
)

registered = {
    item.get("tool_id"): item
    for item in manifest.get("tools", [])
    if isinstance(item, dict)
}
entry = registered.get("verify_release_orchestrator", {})

required_verify = {
    "kg001_source_suite",
    "candidate4_release_contract",
    "candidate4_music_route",
    "xmi_converter",
    "candidate4_music_renderer",
    "proof_capture_v151",
    "release_py_compile",
}
checks = {
    "schema": profile.get("schema") == "openazrael.verify_release_profile" and profile.get("version") == 1,
    "source_safe_policy": (
        profile.get("policy", {}).get("candidate_build_created") is False
        and profile.get("policy", {}).get("commercial_assets_required") is False
    ),
    "unique_gate_ids": len(gate_ids) == len(set(gate_ids)) and bool(gate_ids),
    "fallback_exists_and_verifies": fallback in by_id and by_id[fallback].verify,
    "always_fast_safety": (
        "public_release_safety" in by_id
        and by_id["public_release_safety"].always_fast
        and by_id["public_release_safety"].command == ("<python>", "tools/validate_public_release_safety.py")
    ),
    "verify_set_complete": required_verify.issubset(set(verify_plan.selected_gate_ids)),
    "docs_fast_targeted": (
        "public_release_safety" in docs_plan.selected_gate_ids
        and "release_docs" in docs_plan.selected_gate_ids
        and not docs_plan.escalated_to_verify
    ),
    "save_fast_targeted": (
        "save_compat_v150" in save_plan.selected_gate_ids
        and not save_plan.escalated_to_verify
    ),
    "unknown_critical_escalates": (
        unknown_plan.escalated_to_verify
        and fallback in unknown_plan.selected_gate_ids
        and "scripts/unknown_future_runtime_change.gd" in unknown_plan.unmatched_critical_files
    ),
    "worktree_changes_are_planned_and_fingerprinted":all(token in tool for token in (
        "working_tree_changed_files",
        '"git", "diff", "--name-only", "--cached"',
        '"git", "ls-files", "--others", "--exclude-standard"',
        "merge_changed_files(tracked, worktree)",
        '"worktree_changed_files": worktree',
    )),
    "dependency_versions_in_cache_identity":all(token in tool for token in (
        'importlib.metadata.version',
        '"numpy"',
        '"Pillow"',
        '"trimesh"',
        '"soundfile"',
    )),
    "pass_only_exact_cache": (
        "PASS_ONLY_EXACT_GATE_FINGERPRINT" in tool
        and "can_reuse_pass" in tool
        and "profile_sha256" in core
        and "environment_identity" in core
    ),
    "local_verify_not_ci": "LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED" in core,
    "ci_exact_head_guard": all(token in tool for token in (
        "OPENAZRAEL_CI_EXPECTED_SHA",
        "OPENAZRAEL_CI_COMPLETE",
        "ci_expected_sha == head",
        "github_actions",
    )),
    "no_candidate_execution": all(
        command[:2] not in {
            ("<python>", "tools/run_candidate3_preflight.py"),
            ("<python>", "tools/run_candidate4_preflight.py"),
            ("<python>", "tools/export_candidate3.py"),
            ("<python>", "tools/export_candidate4.py"),
            ("<python>", "tools/freeze_candidate4_release.py"),
        }
        for command in (gate.command for gate in gates)
    ),
    "workflow_exact_checkout": all(token in workflow for token in (
        "expected_sha",
        "git rev-parse HEAD",
        "OPENAZRAEL_CI_EXPECTED_SHA",
    )),
    "workflow_two_python_passes": all(token in workflow for token in (
        'python-version: "3.11"',
        'python-version: "3.12"',
        "verify_py311.json",
        "verify_release_orchestrator.json",
        'OPENAZRAEL_CI_COMPLETE: "true"',
    )),
    "workflow_no_cache_verify": workflow.count("--mode verify") >= 2 and workflow.count("--no-cache") >= 2,
    "workflow_uploads_receipts": "actions/upload-artifact@v4" in workflow and "verify-release-" in workflow,
    "registered_in_framework": (
        entry.get("family") == "project_release"
        and entry.get("entrypoint") == "tools/run_verify_release_orchestrator.py"
        and entry.get("source_safe") is True
        and entry.get("mutates_runtime") is False
    ),
    "docs_boundaries": all(token in doc for token in (
        "FAST",
        "VERIFY",
        "Candidate build",
        "LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED",
        "SOURCE_CHECKPOINT_READY_FOR_ASSET_PREFLIGHT",
    )),
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "schema": "openazrael.verify_release_orchestrator_validation",
    "version": 1,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks": checks,
    "failed": failed,
}, indent=2))
raise SystemExit(1 if failed else 0)
