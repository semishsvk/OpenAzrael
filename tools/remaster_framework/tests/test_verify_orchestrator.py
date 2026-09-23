from __future__ import annotations

import unittest

from tools.remaster_framework.verify_orchestrator import (
    GateSpec,
    can_reuse_pass,
    classify_readiness,
    gate_fingerprint,
    merge_changed_files,
    select_plan,
)


def gate(
    gate_id: str,
    *,
    triggers: tuple[str, ...] = (),
    always_fast: bool = False,
    verify: bool = False,
) -> GateSpec:
    return GateSpec(
        gate_id=gate_id,
        command=("<python>", f"tools/{gate_id}.py"),
        triggers=triggers,
        inputs=triggers or ("**",),
        always_fast=always_fast,
        verify=verify,
    )


class VerifyOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gates = (
            gate("safety", always_fast=True),
            gate("docs", triggers=("docs/**",)),
            gate("save", triggers=("scripts/legacy_save_system_v145.gd",)),
            gate("broad", verify=True),
            gate("release", verify=True),
        )

    def test_fast_docs_change_selects_targeted_gates_only(self) -> None:
        plan = select_plan(
            mode="fast",
            changed_files=["docs/PROJECT_STATE.md"],
            gates=self.gates,
            critical_patterns=("scripts/**", "tools/**", "data/**"),
            fallback_gate_id="broad",
        )
        self.assertEqual(plan.selected_gate_ids, ("safety", "docs"))
        self.assertFalse(plan.escalated_to_verify)

    def test_fast_known_critical_change_stays_targeted(self) -> None:
        plan = select_plan(
            mode="fast",
            changed_files=["scripts/legacy_save_system_v145.gd"],
            gates=self.gates,
            critical_patterns=("scripts/**", "tools/**", "data/**"),
            fallback_gate_id="broad",
        )
        self.assertEqual(plan.selected_gate_ids, ("safety", "save"))
        self.assertFalse(plan.escalated_to_verify)

    def test_unknown_critical_change_escalates(self) -> None:
        plan = select_plan(
            mode="fast",
            changed_files=["scripts/new_runtime_behavior.gd"],
            gates=self.gates,
            critical_patterns=("scripts/**", "tools/**", "data/**"),
            fallback_gate_id="broad",
        )
        self.assertEqual(plan.unmatched_critical_files, ("scripts/new_runtime_behavior.gd",))
        self.assertTrue(plan.escalated_to_verify)
        self.assertEqual(plan.selected_gate_ids, ("safety", "broad"))

    def test_verify_uses_only_declared_verify_gates(self) -> None:
        plan = select_plan(
            mode="verify",
            changed_files=["docs/PROJECT_STATE.md"],
            gates=self.gates,
            critical_patterns=("scripts/**",),
            fallback_gate_id="broad",
        )
        self.assertEqual(plan.selected_gate_ids, ("broad", "release"))
        self.assertEqual(plan.reason, "explicit_verify")

    def test_cache_reuse_requires_exact_passing_fingerprint(self) -> None:
        spec = self.gates[2]
        fp = gate_fingerprint(
            spec,
            input_identity={"scripts/legacy_save_system_v145.gd": {"sha256": "abc", "bytes": 1}},
            profile_sha256="profile",
            environment_identity={"python": "3.11"},
        )
        self.assertTrue(can_reuse_pass({"status": "PASS", "fingerprint": fp}, fingerprint=fp))
        self.assertFalse(can_reuse_pass({"status": "FAIL", "fingerprint": fp}, fingerprint=fp))
        self.assertFalse(can_reuse_pass({"status": "PASS", "fingerprint": "other"}, fingerprint=fp))

    def test_fingerprint_changes_with_input_identity(self) -> None:
        spec = self.gates[2]
        first = gate_fingerprint(
            spec,
            input_identity={"a": {"sha256": "1", "bytes": 1}},
            profile_sha256="profile",
            environment_identity={"python": "3.11"},
        )
        second = gate_fingerprint(
            spec,
            input_identity={"a": {"sha256": "2", "bytes": 1}},
            profile_sha256="profile",
            environment_identity={"python": "3.11"},
        )
        self.assertNotEqual(first, second)

    def test_merge_changed_files_preserves_worktree_only_changes(self) -> None:
        merged = merge_changed_files(
            ["docs/PROJECT_STATE.md"],
            ["scripts/new_untracked_runtime.gd"],
            ["docs/PROJECT_STATE.md"],
        )
        self.assertEqual(
            merged,
            ("docs/PROJECT_STATE.md", "scripts/new_untracked_runtime.gd"),
        )

    def test_dirty_verify_is_never_release_ready(self) -> None:
        self.assertEqual(
            classify_readiness(
                mode="verify",
                all_selected_pass=True,
                clean_worktree=False,
                exact_head_ci=True,
            ),
            "BLOCKED_DIRTY_WORKTREE",
        )

    def test_readiness_never_promotes_local_verify_to_exact_head_ci(self) -> None:
        self.assertEqual(
            classify_readiness(
                mode="verify",
                all_selected_pass=True,
                clean_worktree=True,
                exact_head_ci=False,
            ),
            "LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED",
        )
        self.assertEqual(
            classify_readiness(
                mode="verify",
                all_selected_pass=True,
                clean_worktree=True,
                exact_head_ci=True,
            ),
            "SOURCE_CHECKPOINT_READY_FOR_ASSET_PREFLIGHT",
        )


if __name__ == "__main__":
    unittest.main()
