from __future__ import annotations
import unittest
from tools.remaster_framework.fidelity import (
    SCENE_FIDELITY_ASPECTS, validate_scene_fidelity_closure,
)

def evidence():
    return [{"authority_class":"CORPUS_AUTHORITY","ref":"sha256:" + "a"*64}]

def valid_payload():
    return {
        "schema":"remaster.scene_fidelity_closure","version":1,
        "project_id":"fixture","scene_id":"scene-1",
        "progression_gate":"SCENE_FIDELITY_VERIFIED",
        "aspects":{
            aspect:{"assertions":[{"claim":aspect+" verified","state":"VERIFIED","evidence":evidence()}]}
            for aspect in SCENE_FIDELITY_ASPECTS
        },
    }

class SceneFidelityClosureTests(unittest.TestCase):
    def test_complete_scene_passes(self):
        self.assertEqual(validate_scene_fidelity_closure(valid_payload()), [])

    def test_missing_exit_fails_closed(self):
        p=valid_payload(); del p["aspects"]["exit"]
        self.assertTrue(any("exit: missing" in x for x in validate_scene_fidelity_closure(p)))

    def test_hold_blocks_promotion(self):
        p=valid_payload(); p["aspects"]["dialogue_ui"]["assertions"][0]["state"]="HOLD"
        self.assertTrue(any("requires VERIFIED" in x for x in validate_scene_fidelity_closure(p)))

    def test_replay_alone_cannot_promote_scene(self):
        p=valid_payload()
        p["aspects"]={"deterministic_replay_capture_diff":p["aspects"]["deterministic_replay_capture_diff"]}
        errors=validate_scene_fidelity_closure(p)
        self.assertGreaterEqual(len([x for x in errors if "missing required aspect" in x]), 9)

    def test_invalid_authority_fails(self):
        p=valid_payload(); p["aspects"]["audio"]["assertions"][0]["evidence"][0]["authority_class"]="GUESS"
        self.assertTrue(any("invalid authority_class" in x for x in validate_scene_fidelity_closure(p)))

if __name__=="__main__":
    unittest.main()
