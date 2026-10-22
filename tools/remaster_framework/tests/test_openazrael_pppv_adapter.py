from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.openazrael_adapters.physical_pppv import (
    adapt_physical_traversal_contract,
)
from tools.openazrael_adapters.well_pppv import adapt_well_tongs_contract
from tools.openazrael_adapters.pppv import write_scenarios
from tools.remaster_framework.validation import (
    ExecutionMode,
    ValidationScenario,
)


class OpenAzraelPPPVAdapterTests(unittest.TestCase):
    def test_well_tongs_generates_real_player_scenarios(self) -> None:
        contract = {
            "schema": "openazrael.kg001.well_tongs_animation_contract",
            "version": 118,
            "room": "R7",
            "interaction": "Interact_WellKey",
            "inventory_precondition": "rusty_tongs",
            "exact_compiled_action_sequence": [
                {"semantic": "remove_room_object", "object": "R7Key"},
                {"semantic": "play_sound", "asset": "979TONGS.WAV"},
                {"semantic": "add_room_object", "object": "R7Key"},
                {"semantic": "remove_room_object", "object": "RustyTongR6"},
                {"semantic": "remove_inventory", "object": "TONG6"},
            ],
            "sound": {"filename": "979TONGS.WAV"},
            "dispatch_observation": {
                "transform_or_rotation_opcode_present": False
            },
        }

        positive, negative = adapt_well_tongs_contract(contract)
        self.assertEqual(positive.validate(), [])
        self.assertEqual(negative.validate(), [])
        self.assertEqual(
            [action.action_id for action in positive.actions],
            ["approach_well", "aim_well", "interact_well"],
        )
        self.assertEqual(
            [action.execution_mode for action in positive.actions],
            [
                ExecutionMode.INPUT,
                ExecutionMode.INPUT,
                ExecutionMode.INTERACTION_PROBE,
            ],
        )
        self.assertFalse(positive.metadata["direct_interact_call_allowed"])
        self.assertEqual(
            list(positive.sequences[0].expected),
            [
                "remove_room:R7Key",
                "play_sound:979TONGS.WAV",
                "add_room:R7Key",
                "remove_room:RustyTongR6",
                "remove_inventory:TONG6",
                "default_take:R7Key",
            ],
        )
        self.assertTrue(
            any(
                item.requirement_id == "no_invented_transform_tween"
                for item in positive.forbidden
            )
        )
        self.assertEqual(
            ValidationScenario.from_dict(positive.to_dict()).to_dict(),
            positive.to_dict(),
        )

    def test_physical_contract_generates_floor_and_stairs(self) -> None:
        contract = {
            "schema": "openazrael.kg001.physical_traversal_contract",
            "version": 117,
            "production_path": {
                "body": "CharacterBody3D",
                "movement_solver": "move_and_slide",
            },
            "floor_regression": {"room": "R1", "spawn_view": "spaview"},
            "stair_regressions": [
                {
                    "room": "R8",
                    "mesh": "step011__mesh",
                    "minimum_tread_levels": 4,
                    "audited_total_rise": 15.18616,
                    "audited_horizontal_run": 31.200357,
                    "approximate_rise_per_step": 5.062053,
                },
                {
                    "room": "R8",
                    "mesh": "stairs__STAIR2",
                    "minimum_tread_levels": 8,
                    "audited_total_rise": 87.954292,
                    "audited_horizontal_run": 133.443661,
                    "approximate_rise_per_step": 12.565,
                },
            ],
        }

        scenarios = adapt_physical_traversal_contract(contract)
        self.assertEqual(len(scenarios), 3)
        self.assertTrue(all(scenario.validate() == [] for scenario in scenarios))
        self.assertTrue(
            all(
                action.execution_mode == ExecutionMode.INPUT
                for scenario in scenarios
                for action in scenario.actions
            )
        )
        self.assertFalse(
            scenarios[0].metadata["direct_horizontal_velocity_injection_accepted"]
        )
        self.assertTrue(
            all(
                scenario.metadata.get("fake_stair_fixture_allowed") is False
                for scenario in scenarios[1:]
            )
        )


    def test_split_scenarios_are_deterministic_validation_documents(self) -> None:
        contract = {
            "schema": "openazrael.kg001.well_tongs_animation_contract",
            "version": 118,
            "room": "R7",
            "interaction": "Interact_WellKey",
            "inventory_precondition": "rusty_tongs",
            "exact_compiled_action_sequence": [
                {"semantic": "remove_room_object", "object": "R7Key"},
                {"semantic": "play_sound", "asset": "979TONGS.WAV"},
                {"semantic": "add_room_object", "object": "R7Key"},
                {"semantic": "remove_room_object", "object": "RustyTongR6"},
                {"semantic": "remove_inventory", "object": "TONG6"},
            ],
            "sound": {"filename": "979TONGS.WAV"},
            "dispatch_observation": {
                "transform_or_rotation_opcode_present": False,
            },
        }
        scenarios = list(adapt_well_tongs_contract(contract))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle.json"
            split = root / "split"
            write_scenarios(scenarios, bundle, split_dir=split)

            files = sorted(path.name for path in split.glob("*.json"))
            self.assertEqual(
                files,
                [
                    "openazrael_r7_well_tongs_negative_without_tongs.json",
                    "openazrael_r7_well_tongs_positive.json",
                ],
            )
            positive = json.loads(
                (
                    split / "openazrael_r7_well_tongs_positive.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                positive["schema"],
                "remaster.validation_scenario",
            )
            self.assertEqual(
                positive["scenario_id"],
                "openazrael.r7.well_tongs.positive",
            )


if __name__ == "__main__":
    unittest.main()
