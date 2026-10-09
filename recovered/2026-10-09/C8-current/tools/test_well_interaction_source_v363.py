#!/usr/bin/env python3
"""Complete Well Room branch→transform/state/audio structural chain, source-only."""
import collections,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_well_interaction_source_v363 import derive,EXPECTED,SOURCE,OUTPUT
from audit_well_actions_v317 import inspect
class R7Interaction(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=SOURCE.read_bytes()
  cls.groups=derive(cls.raw)
  cls.by_node={(g["node"],g["slot"]):g for g in cls.groups}
 def test_canonical(self):
  self.assertEqual(hashlib.sha256(self.raw).hexdigest(),EXPECTED)
  self.assertEqual(len(self.groups),12)
 def test_population(self):
  actions=[a for g in self.groups for a in g["actions"]]
  self.assertEqual(len(actions),48)
  self.assertEqual(collections.Counter(a["kind"] for a in actions),
                   {"rotation":16,"translation":8,"sound":12,"state_write":8,"opaque_state_action":4})
 def test_sound_bindings(self):
  expected={2:"983TUNK.WAV",3:"983TUNK.WAV",5:"977TURN.WAV",6:"977TURN.WAV",
    10:"983TUNK.WAV",11:"983TUNK.WAV",13:"977TURN.WAV",14:"977TURN.WAV"}
  for node,wav in expected.items():
   sounds=[a for a in self.by_node[(node,0)]["actions"] if a["kind"]=="sound"]
   self.assertEqual([a["sound_file"] for a in sounds],[wav])
  for node in (8,16):
   for slot,wav in ((0,"982PUSH.WAV"),(1,"981PULL.WAV")):
    sound=[a for a in self.by_node[(node,slot)]["actions"] if a["kind"]=="sound"]
    self.assertEqual([a["sound_file"] for a in sound],[wav])
 def test_source_state_writes(self):
  expected={
   (8,0):[(44,0)],(8,1):[(44,1),(42,0),(43,0)],
   (16,0):[(46,0)],(16,1):[(46,1),(42,0),(43,0)],
  }
  for key,changes in expected.items():
   rows=[a for a in self.by_node[key]["actions"] if a["kind"]=="state_write"]
   self.assertEqual([(a["source_state_index"],a["source_state_value"]) for a in rows],changes)
   self.assertTrue(all(a["source_array"]=="WORLD_SECTION4_STATE_U16" for a in rows))
 def test_unverified_opaque_opcode_01(self):
  self.assertEqual(len([a for g in self.groups for a in g["actions"] if a["kind"]=="opaque_state_action"]),4)
 def test_audio_is_in_r7_context(self):
  sounds=[a for g in self.groups for a in g["actions"] if a["kind"]=="sound"]
  self.assertTrue(all(a["room_context"]==1 for a in sounds))
 def test_condition_pairs(self):
  for node,index in ((8,44),(16,46)):
   self.assertEqual([(self.by_node[(node,slot)]["condition"]["opcode"],
                      self.by_node[(node,slot)]["condition"]["state_index_candidate"]) for slot in (0,1)],
                    [(4,index),(10,index)])
 def test_original_action_order_not_confused_with_sound_timing(self):
  self.assertEqual([a["opcode"] for a in self.by_node[(16,0)]["actions"]],[24,23,4,1,40])
  self.assertEqual([a["opcode"] for a in self.by_node[(16,1)]["actions"]],[24,23,4,1,4,4,40])
  self.assertEqual([a["opcode"] for a in self.by_node[(8,0)]["actions"]],[24,23,40,1,4])
  self.assertEqual([a["opcode"] for a in self.by_node[(8,1)]["actions"]],[24,23,40,1,4,4,4])
 def test_transform_subset_matches_v317(self):
  source={(a["source_offset"],a["opcode"]) for g in self.groups for a in g["actions"] if a["kind"] in ("rotation","translation")}
  reference={(r["offset"],r["opcode"]) for r in inspect(SOURCE)["records"]}
  self.assertEqual(source,reference)
 def test_corrupted_source_rejected(self):
  changed=bytearray(self.raw);changed[1024]^=1
  with self.assertRaises(ValueError):derive(bytes(changed))
 def test_generated_manifest_explicit_hold(self):
  ir=json.loads(OUTPUT.read_text(encoding="utf8"))
  self.assertEqual(ir["groups"],self.groups)
  self.assertEqual(ir["world_sha256"],EXPECTED)
  self.assertIn("opcode_01_runtime_semantics",ir["hold"])
  self.assertIn("original_audio_physical_timing",ir["hold"])
if __name__=="__main__":unittest.main(verbosity=2)