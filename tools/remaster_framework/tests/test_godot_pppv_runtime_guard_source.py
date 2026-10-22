from __future__ import annotations

import unittest
from pathlib import Path


class GodotPPPVRuntimeGuardSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[3]
        validation = root / "scripts" / "validation"
        self.guard = (validation / "pppv_runtime_guard.gd").read_text(
            encoding="utf-8"
        )
        self.driver = (validation / "pppv_player_driver.gd").read_text(
            encoding="utf-8"
        )
        self.navigator = (validation / "pppv_navigator.gd").read_text(
            encoding="utf-8"
        )
        self.executor = (validation / "pppv_action_executor.gd").read_text(
            encoding="utf-8"
        )
        self.scenario = (validation / "pppv_scenario_runner.gd").read_text(
            encoding="utf-8"
        )
        self.playthrough = (
            validation / "pppv_playthrough_runner.gd"
        ).read_text(encoding="utf-8")

    def test_guard_records_frame_level_avatar_and_world_state(self) -> None:
        self.assertIn("Engine.get_physics_frames()", self.guard)
        self.assertIn("player.is_on_floor()", self.guard)
        self.assertIn('"state_sha256"', self.guard)
        self.assertIn('"state_payload"', self.guard)
        self.assertIn('"trajectory"', self.guard)
        self.assertIn(
            '"schema": "remaster.synthetic_player_replay"',
            self.guard,
        )

    def test_guard_detects_floor_and_softlock_failures(self) -> None:
        self.assertIn('"floor_drop_per_frame"', self.guard)
        self.assertIn('"action_vertical_drop"', self.guard)
        self.assertIn('"unsupported_fall"', self.guard)
        self.assertIn('"softlock_watchdog"', self.guard)
        self.assertIn('"critical_runtime_violation"', self.guard)
        self.assertIn('"room_change_sample"', self.guard)
        self.assertIn('"continuity_reset": true', self.guard)

    def test_unsupported_fall_requires_missing_world_support(self) -> None:
        self.assertIn("func _support_below_player()", self.guard)
        self.assertIn("PhysicsRayQueryParameters3D.create", self.guard)
        self.assertIn("and not support_ok", self.guard)
        self.assertIn('"support_below"', self.guard)
        self.assertIn('"support_gap"', self.guard)

    def test_guard_checks_live_runtime_invariants(self) -> None:
        self.assertIn("player.global_position.is_finite()", self.guard)
        self.assertIn("player.global_rotation.is_finite()", self.guard)
        self.assertIn("player.velocity.is_finite()", self.guard)
        self.assertIn('"non_finite_player_state"', self.guard)
        self.assertIn('"current_room_node_invalid"', self.guard)
        self.assertIn('"movement_input_stuck_after_action"', self.guard)

    def test_transition_spawn_uses_production_continuity_and_support(self) -> None:
        self.assertIn("verify_transition_spawn", self.guard)
        self.assertIn('runtime_evidence.get("demo_transitions"', self.guard)
        self.assertIn('manager.has_method("portal_spawn_expectation")', self.guard)
        self.assertIn('"portal_spawn_expectation"', self.guard)
        self.assertIn('"continuity_logical_jump"', self.guard)
        self.assertIn('"continuity_fallback"', self.guard)
        self.assertIn("DEFAULT_MAX_TRANSITION_LOGICAL_JUMP := 8.0", self.guard)
        self.assertIn("initial_position_error", self.guard)
        self.assertIn("for support_frame in range(30)", self.guard)
        self.assertIn('"floor_support_required_frames": 30', self.guard)
        self.assertIn('"floor_probe_final"', self.guard)
        self.assertIn('"transition_spawn_check"', self.guard)
        self.assertIn('"transition_spawn_mismatch"', self.guard)
        self.assertIn("await runtime_guard.verify_transition_spawn", self.executor)

    def test_guard_observes_but_never_drives_production_player(self) -> None:
        self.assertNotIn("player.global_position =", self.guard)
        self.assertNotIn("player.position =", self.guard)
        self.assertNotIn("player.rotation.y =", self.guard)
        self.assertNotIn("player.velocity =", self.guard)
        self.assertNotIn("player.move_and_slide()", self.guard)

    def test_motion_helpers_sample_guard_each_physics_step(self) -> None:
        self.assertIn("runtime_guard.sample(action_id)", self.driver)
        self.assertIn("runtime_guard.sample(action_id)", self.navigator)
        self.assertIn("runtime_guard.report_watchdog", self.navigator)

    def test_every_shared_action_is_wrapped_for_replay(self) -> None:
        self.assertIn("runtime_guard.begin_action(action)", self.executor)
        self.assertIn("runtime_guard.end_action", self.executor)
        self.assertIn('"room_after"', self.executor)

    def test_both_runners_emit_replay_and_guard_boundary(self) -> None:
        for source in (self.scenario, self.playthrough):
            self.assertIn("pppv_runtime_guard.gd", source)
            self.assertIn("runtime_guard.replay_bundle()", source)
            self.assertIn('"frame_level_avatar_trajectory": true', source)
            self.assertIn('"world_state_snapshots": true', source)
            self.assertIn('"softlock_watchdog": true', source)
            self.assertIn('"transition_spawn_validation": true', source)


if __name__ == "__main__":
    unittest.main()
