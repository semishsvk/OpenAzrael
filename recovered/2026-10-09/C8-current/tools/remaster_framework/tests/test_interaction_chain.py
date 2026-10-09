import unittest
from tools.remaster_framework.fidelity import INTERACTION_CHAIN_STAGES,validate_interaction_chain

def valid():
    return {"schema":"remaster.interaction_chain_fidelity","version":1,"project_id":"fixture","scene_id":"room","interaction_id":"lever","progression_gate":"INTERACTION_FIDELITY_VERIFIED","stages":{s:{"state":"VERIFIED","applicable":True,"evidence":[{"authority_class":"CORPUS_AUTHORITY","ref":"sha256:fixture"}]} for s in INTERACTION_CHAIN_STAGES}}

class ChainTests(unittest.TestCase):
    def test_full_pass(self): self.assertEqual(validate_interaction_chain(valid()),[])
    def test_missing_animation_blocks(self):
        p=valid();del p["stages"]["animation"]
        self.assertTrue(any("animation" in x for x in validate_interaction_chain(p)))
    def test_missing_audio_blocks(self):
        p=valid();p["stages"]["audio"]["state"]="HOLD"
        self.assertTrue(any("audio" in x for x in validate_interaction_chain(p)))
    def test_absence_requires_proof(self):
        p=valid();p["stages"]["animation"]["applicable"]=False
        self.assertTrue(any("source proof" in x for x in validate_interaction_chain(p)))
    def test_replay_required(self):
        p=valid();del p["stages"]["deterministic_replay_capture_diff"]
        self.assertTrue(validate_interaction_chain(p))
