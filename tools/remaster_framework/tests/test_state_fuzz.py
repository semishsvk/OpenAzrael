from __future__ import annotations

import unittest

from tools.remaster_framework.state_fuzz import (
    StateFuzzConfig,
    run_state_fuzz,
)


class StateFuzzTests(unittest.TestCase):
    def test_deterministic_recoverable_model_passes(self) -> None:
        def transition(state: int, action: str):
            if action == "inc" and state < 2:
                return state + 1, ()
            if action == "reset":
                return 0, ()
            return state, ()

        report = run_state_fuzz(
            initial_state=0,
            actions=("inc", "reset", "noop"),
            transition=transition,
            state_key=lambda state: str(state),
            invariant_errors=lambda state: (
                [] if 0 <= state <= 2 else ["out_of_range"]
            ),
            reachable_state_keys={"0", "1", "2"},
            recoverable_state_keys={"0", "1", "2"},
            is_success=lambda state: state == 2,
            config=StateFuzzConfig(
                seed_base=10,
                seed_count=8,
                steps_per_seed=32,
                restart_probability=0.0,
            ),
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["attempts"], 256)
        self.assertEqual(report["failure_count"], 0)

    def test_nondeterministic_transition_is_rejected(self) -> None:
        counter = {"value": 0}

        def transition(state: int, action: str):
            counter["value"] += 1
            return state + counter["value"], ()

        report = run_state_fuzz(
            initial_state=0,
            actions=("step",),
            transition=transition,
            state_key=lambda state: str(state),
            invariant_errors=lambda state: [],
            no_op_effects_must_be_empty=True,
            config=StateFuzzConfig(
                seed_base=1,
                seed_count=1,
                steps_per_seed=1,
            ),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any(
                row["property"] == "transition_determinism"
                for row in report["failures"]
            )
        )

    def test_noop_side_effect_is_rejected(self) -> None:
        report = run_state_fuzz(
            initial_state=0,
            actions=("noop",),
            transition=lambda state, action: (state, ("sound.wav",)),
            state_key=lambda state: str(state),
            invariant_errors=lambda state: [],
            config=StateFuzzConfig(
                seed_base=1,
                seed_count=1,
                steps_per_seed=1,
            ),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any(
                row["property"] == "noop_side_effect"
                for row in report["failures"]
            )
        )

    def test_unrecoverable_state_is_reported_as_softlock(self) -> None:
        report = run_state_fuzz(
            initial_state=0,
            actions=("trap",),
            transition=lambda state, action: (1, ()),
            state_key=lambda state: str(state),
            invariant_errors=lambda state: [],
            reachable_state_keys={"0", "1"},
            recoverable_state_keys={"0"},
            config=StateFuzzConfig(
                seed_base=1,
                seed_count=1,
                steps_per_seed=1,
            ),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any(
                row["property"] == "liveness_softlock"
                for row in report["failures"]
            )
        )


if __name__ == "__main__":
    unittest.main()
