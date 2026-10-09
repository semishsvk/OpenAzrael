from __future__ import annotations

import unittest

from tools.remaster_framework.playthrough import (
    PlaythroughStep,
    StepKind,
    StepStatus,
    build_playthrough_plan,
    validate_checkpoint_roundtrip,
)


class PlaythroughPlanTests(unittest.TestCase):
    def test_blocked_step_keeps_plan_authoring_required(self) -> None:
        plan = build_playthrough_plan(
            project="Test",
            plan_id="demo",
            steps=[
                PlaythroughStep(
                    step_id="scenario",
                    kind=StepKind.SCENARIO,
                    status=StepStatus.AUTHORING_REQUIRED,
                    room="R1",
                    metadata={"desired_scenario_id": "missing"},
                )
            ],
        )
        self.assertEqual(plan["status"], "AUTHORING_REQUIRED")
        self.assertEqual(plan["blocked_steps"], ["scenario"])
        self.assertEqual(len(plan["plan_sha256"]), 64)

    def test_ready_transition_requires_full_edge_identity(self) -> None:
        with self.assertRaises(ValueError):
            build_playthrough_plan(
                project="Test",
                plan_id="bad",
                steps=[
                    PlaythroughStep(
                        step_id="transition",
                        kind=StepKind.TRANSITION,
                        status=StepStatus.READY,
                        source_room="R1",
                        destination_room="R7",
                    )
                ],
            )

    def test_save_load_roundtrip_uses_hash_identity(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            validate_checkpoint_roundtrip(
                before_save_sha256=digest,
                after_restore_sha256=digest,
                expected_sha256=digest,
            ),
            [],
        )
        self.assertTrue(
            validate_checkpoint_roundtrip(
                before_save_sha256=digest,
                after_restore_sha256="b" * 64,
            )
        )


if __name__ == "__main__":
    unittest.main()
