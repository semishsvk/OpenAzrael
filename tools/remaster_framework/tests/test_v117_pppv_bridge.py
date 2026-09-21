from __future__ import annotations

import unittest

from tools.openazrael_adapters.v117_pppv_bridge import evaluate_v117_bridge


class V117PPPVBridgeTests(unittest.TestCase):
    def _contract(self) -> dict:
        return {
            "schema": "openazrael.kg001.physical_traversal_contract",
            "version": 117,
            "production_path": {},
            "floor_regression": {
                "room": "R1",
                "spawn_view": "spaview",
            },
            "stair_regressions": [
                {
                    "room": "R8",
                    "mesh": "step011__mesh",
                    "minimum_tread_levels": 4,
                },
                {
                    "room": "R8",
                    "mesh": "stairs__STAIR2",
                    "minimum_tread_levels": 8,
                },
            ],
        }

    def _runtime(self, status: str = "PASS") -> dict:
        events = []
        event_id = 1

        def add(kind: str, payload: dict) -> None:
            nonlocal event_id
            events.append({
                "event_id": f"ev_{event_id:06d}",
                "frame": event_id,
                "kind": kind,
                "payload": payload,
            })
            event_id += 1

        for action_id in ("r1_forward", "r1_back"):
            add("player_action", {
                "action_id": action_id,
                "execution_mode": "input",
            })
            add("collision_support", {
                "action_id": action_id,
                "continuous": True,
                "fell_through": False,
            })
            add("movement", {
                "action_id": action_id,
                "progress_ok": True,
            })

        for mesh in ("step011__mesh", "stairs__STAIR2"):
            for action_id, direction in (
                ("ascend", "ascending"),
                ("descend", "descending"),
            ):
                add("player_action", {
                    "action_id": action_id,
                    "execution_mode": "input",
                })
                add("stair_traversal", {
                    "mesh": mesh,
                    "direction": direction,
                    "progress_ok": True,
                    "height_ok": True,
                    "fell_through": False,
                })

        return {
            "schema": "openazrael.kg001.physical_traversal",
            "version": 117,
            "status": status,
            "pppv_evidence": {
                "schema": "remaster.runtime_evidence",
                "version": 1,
                "events": events,
            },
        }

    def test_pass_is_bridge_pass_but_not_final_oracle(self) -> None:
        report = evaluate_v117_bridge(self._runtime(), self._contract())
        self.assertEqual(report["status"], "BRIDGE_PASS")
        self.assertFalse(report["final_pppv_oracle"])
        self.assertTrue(
            all(
                row["status"] == "PASS"
                for row in report["generic_scenarios"]
            )
        )

    def test_legacy_failure_cannot_be_bridge_pass(self) -> None:
        report = evaluate_v117_bridge(
            self._runtime(status="FAIL"),
            self._contract(),
        )
        self.assertEqual(report["status"], "BRIDGE_FAIL")

    def test_missing_generic_evidence_fails_bridge(self) -> None:
        runtime = self._runtime()
        runtime["pppv_evidence"] = {"events": []}
        report = evaluate_v117_bridge(runtime, self._contract())
        self.assertEqual(report["status"], "BRIDGE_FAIL")


if __name__ == "__main__":
    unittest.main()
