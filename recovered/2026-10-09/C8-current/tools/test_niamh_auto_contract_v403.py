#!/usr/bin/env python3
"""Source-bound v403 Niamh automatic first-room-visit contract, no invented input trigger."""
from pathlib import Path
import json,hashlib,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
EVENTS=ROOT/"data/trigger_event_ir_v137.json"
SCHEMA=ROOT/"data/tests/kg001_niamh_auto_once_contract_v403.json"
EVIDENCE=ROOT/"data/xaf_trigger_evidence.json"
GRAPHS=ROOT/"data/gameplay_event_graph_v87.json"
ROOMMANAGER=ROOT/"scripts/room_manager.gd"
class NiamhAutoActivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events=json.loads(EVENTS.read_text(encoding="utf8"))
        cls.contract=json.loads(SCHEMA.read_text(encoding="utf8"))
        cls.evidence=json.loads(EVIDENCE.read_text(encoding="utf8"))
        cls.graphs=json.loads(GRAPHS.read_text(encoding="utf8"))
        cls.manager=ROOMMANAGER.read_text(encoding="utf8")
        cls.ghost=[x for x in cls.events["rooms"]["R7"] if x.get("trigger")=="zxactghost"]
    def test_original_ghost_unique_source_trigger(self):
        self.assertEqual(len(self.ghost),1)
        self.assertEqual(self.ghost[0]["class"],"activation_enter")
        self.assertEqual(self.ghost[0]["event_graph"],"R7_NIAMH_ACTIVATE")
        self.assertEqual(self.ghost[0]["one_shot_flag"],"R7NiamhActivated")
    def test_initial_overlap_enabled_only_for_niamh_activation(self):
        self.assertIs(self.ghost[0].get("initial_overlap"),True)
        all_activations=[x for room in self.events["rooms"].values() for x in room if x.get("class")=="activation_enter"]
        self.assertEqual([x["trigger"] for x in all_activations if x.get("initial_overlap")],["zxactghost"])
    def test_source_volume_is_authored_not_guessed(self):
        ghost=[x for x in self.evidence["rooms"]["R7"]["triggers"] if x.get("name")=="zxactghost"]
        self.assertEqual(len(ghost),1)
        self.assertEqual(ghost[0]["material"],"TRANSPARANT")
        self.assertEqual(len(ghost[0]["bounds"]),2)
    def test_no_user_click_or_key_binding_required(self):
        c=self.contract
        self.assertEqual(c["version"],403)
        self.assertIn("NO click",c["interaction_requirement"])
        self.assertEqual(c["authority"]["authored_trigger"],"R7/zxactghost")
        self.assertIn("first",c["spawn_semantics"].lower())
    def test_original_animation_and_conversation_route(self):
        a=self.graphs["graphs"]["R7_NIAMH_ACTIVATE"]["actions"]
        self.assertEqual([x["op"] for x in a],
            ["set_flag","set_puzzle_node","request_character_animation","request_conversation"])
        self.assertEqual(a[0]["key"],"R7NiamhActivated")
        self.assertEqual(a[2]["family"],"NOLOOP1")
        self.assertEqual(a[2]["next_family"],"REST")
        self.assertEqual(a[3]["family"],"1A")
    def test_dispatch_guards_against_duplicate(self):
        self.assertIn('DemoState.flag(one_shot_flag)',self.manager)
        self.assertIn('binding.get("initial_overlap", false)',self.manager)
        self.assertIn('_dispatch_trigger_edge(trigger_name, inside)',self.manager)
    def test_scope_never_promotes_fidelity(self):
        self.assertTrue(any("timing" in x for x in self.contract["not_asserted"]))
        self.assertEqual(self.contract["status"],"SOURCE_BOUND_RUNTIME_PASS_FIDELITY_HOLD")
    def test_godot_regression_runner_authored(self):
        p=ROOT/"scripts/kg001_niamh_auto_once_runner_v403.gd"
        s=p.read_text(encoding="utf8")
        self.assertIn('OPENAZRAEL_NIAMH_AUTO_ONCE_V403',s)
        for evidence in ("no_second_ghost_dispatch","saved_game_no_reactivation",
          "auto_initial_overlap_once","dialog_auto_open","NO_MANUAL_CLICK_OR_M_KEY"):
            self.assertIn(evidence,s)
if __name__=="__main__":
    result=unittest.main(verbosity=2,exit=False)
    passed=result.result.wasSuccessful()
    print("NIAMH_AUTO_CONTRACT_V403 "+json.dumps({
        "status":"PASS" if passed else "FAIL",
        "checks":result.result.testsRun,
        "failed":[str(t[0]) for t in result.result.failures+result.result.errors],
        "scope":"Source-bound automatic Niamh, original frame timing HOLD"
    }))
    sys.exit(0 if passed else 1)