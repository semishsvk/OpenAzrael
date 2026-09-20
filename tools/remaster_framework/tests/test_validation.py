from __future__ import annotations

import unittest

from tools.remaster_framework.validation import (
    ActionKind,
    EvidenceRequirement,
    ExecutionMode,
    PlayerAction,
    RuntimeEvidence,
    StateExpectation,
    ValidationScenario,
    canonical_state_hash,
    evaluate_scenario,
)


class ValidationLabTests(unittest.TestCase):
    def test_canonical_hash_ignores_dict_insertion_order(self) -> None:
        first = {"flags": {"b": False, "a": True}, "position": [1.0, 2.0, -0.0]}
        second = {"position": [1.0, 2.0, 0.0], "flags": {"a": True, "b": False}}
        self.assertEqual(canonical_state_hash(first), canonical_state_hash(second))

    def test_direct_call_interaction_is_rejected_by_contract(self) -> None:
        action = PlayerAction(
            action_id="use_well",
            kind=ActionKind.INTERACT,
            execution_mode=ExecutionMode.INPUT,
            target="Interact_WellKey",
        )
        self.assertTrue(
            any("interaction_probe" in error for error in action.validate())
        )

    def test_scenario_requires_player_action_and_effect_evidence(self) -> None:
        scenario = ValidationScenario(
            scenario_id="well_tongs",
            room="R7",
            setup={"inventory": ["rusty_tongs"]},
            actions=(
                PlayerAction(
                    action_id="approach",
                    kind=ActionKind.MOVE,
                    execution_mode=ExecutionMode.INPUT,
                    input_action="move_forward",
                    frames=30,
                ),
                PlayerAction(
                    action_id="interact",
                    kind=ActionKind.INTERACT,
                    execution_mode=ExecutionMode.INTERACTION_PROBE,
                    target="Interact_WellKey",
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id="trigger",
                    kind="trigger",
                    match={"target": "Interact_WellKey"},
                ),
                EvidenceRequirement(
                    requirement_id="audio",
                    kind="audio",
                    match={"asset": "979TONGS.WAV"},
                    after_requirement="trigger",
                ),
            ),
            forbidden=(
                EvidenceRequirement(
                    requirement_id="no_invented_tween",
                    kind="animation",
                    match={"kind": "invented_transform_tween"},
                ),
            ),
            state_expectations=(
                StateExpectation(
                    path="inventory.rusty_tongs",
                    before=True,
                    after=False,
                ),
                StateExpectation(
                    path="inventory.well_key",
                    before=False,
                    after=True,
                ),
            ),
        )

        evidence = [
            RuntimeEvidence(
                event_id="e1",
                frame=1,
                kind="player_action",
                payload={"action_id": "approach", "execution_mode": "input"},
            ),
            RuntimeEvidence(
                event_id="e2",
                frame=31,
                kind="player_action",
                payload={
                    "action_id": "interact",
                    "execution_mode": "interaction_probe",
                },
            ),
            RuntimeEvidence(
                event_id="e3",
                frame=32,
                kind="trigger",
                payload={"target": "Interact_WellKey"},
            ),
            RuntimeEvidence(
                event_id="e4",
                frame=33,
                kind="audio",
                payload={"asset": "979TONGS.WAV"},
            ),
        ]

        before = {
            "inventory": {"rusty_tongs": True, "well_key": False},
        }
        after = {
            "inventory": {"rusty_tongs": False, "well_key": True},
        }
        self.assertEqual(
            evaluate_scenario(scenario, evidence, before, after),
            [],
        )

    def test_missing_player_evidence_fails(self) -> None:
        scenario = ValidationScenario(
            scenario_id="walk",
            room="R1",
            setup={},
            actions=(
                PlayerAction(
                    action_id="forward",
                    kind=ActionKind.MOVE,
                    execution_mode=ExecutionMode.INPUT,
                    input_action="move_forward",
                    frames=10,
                ),
            ),
            requirements=(),
        )
        errors = evaluate_scenario(scenario, [], {}, {})
        self.assertTrue(any("missing player_action evidence" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
