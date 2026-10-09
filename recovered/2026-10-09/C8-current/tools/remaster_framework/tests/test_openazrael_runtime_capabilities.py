from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.openazrael_adapters.runtime_capabilities import (
    audit_runtime_capabilities,
)


class OpenAzraelRuntimeCapabilityTests(unittest.TestCase):
    def test_current_tooling_branch_has_generic_core(self) -> None:
        root = Path(__file__).resolve().parents[3]
        report = audit_runtime_capabilities(root)
        self.assertTrue(
            report["capabilities"]["generic_pppv_runtime_core"]
        )

    def test_current_tooling_branch_has_exact_well_hook_after_v118_integration(self) -> None:
        root = Path(__file__).resolve().parents[3]
        report = audit_runtime_capabilities(root)
        self.assertTrue(
            report["capabilities"]["well_tongs_exact_demo_evidence"]
        )
        self.assertEqual(report["status"], "READY")
        self.assertNotIn(
            "well_tongs_exact_demo_evidence",
            report["blocked"],
        )

    def test_exact_well_capability_turns_ready_when_hooks_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "player.gd").write_text(
                'Input.get_vector("move_left", "move_right", "move_forward", "move_back")\n'
                "move_and_slide()\n",
                encoding="utf-8",
            )
            (scripts / "interaction_probe.gd").write_text(
                'event.is_action_pressed("interact")\n'
                "_find_interactive()\n"
                "PhysicsRayQueryParameters3D.create\n"
                "intersect_ray\n",
                encoding="utf-8",
            )
            (scripts / "demo_state.gd").write_text(
                "signal inventory_changed\n"
                "signal flag_changed\n"
                "signal puzzle_node_changed\n"
                "func canonical_state_hash():\n    pass\n",
                encoding="utf-8",
            )
            (scripts / "legacy_event_runner_v87.gd").write_text(
                "signal logical_audio_event\n",
                encoding="utf-8",
            )
            (scripts / "candidate_diagnostics_v116.gd").write_text(
                "signal event_recorded\n"
                "func record_interaction(target_name):\n    pass\n"
                'record_event("interaction", {})\n'
                "func observe_trigger(room_id, trigger_name, inside):\n    pass\n"
                'record_event("trigger_" + "enter", {})\n',
                encoding="utf-8",
            )
            (scripts / "well_key_interaction.gd").write_text(
                "signal demo_action_step\n"
                '_step("remove_room:R7Key")\n'
                '_step("play_sound:979TONGS.WAV")\n'
                '_step("add_room:R7Key")\n'
                '_step("remove_room:RustyTongR6")\n'
                '_step("remove_inventory:TONG6")\n'
                '_step("default_take:R7Key")\n'
                'LegacyEvents.run("R7_WELL_TONGS_USE")\n'
                'DemoState.remove("rusty_tongs")\n',
                encoding="utf-8",
            )
            report = audit_runtime_capabilities(root)
            self.assertEqual(report["status"], "READY")
            self.assertTrue(
                report["capabilities"]["well_tongs_exact_demo_evidence"]
            )


if __name__ == "__main__":
    unittest.main()
