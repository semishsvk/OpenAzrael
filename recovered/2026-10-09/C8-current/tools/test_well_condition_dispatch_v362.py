#!/usr/bin/env python3
"""Corrected-LE proof of complementary R7 WORLD condition predicates."""
import hashlib,json,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from le_bound_image_v312 import BoundLE
from analyze_world_puzzle_sound_bridge_v107 import parse_section6_blobs
from build_well_condition_gates_v362 import derive,EXPECTED_SHA,OUTPUT,SOURCE
EXE=SOURCE.parent/"R.EXE"
EXE_SHA="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
class R7Conditions(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=SOURCE.read_bytes();cls.exe=EXE.read_bytes()
  cls.image=BoundLE.parse(cls.exe);cls.code=cls.image.objects[0].data
  cls.records=derive(cls.raw)
 def test_corpus_pin(self):
  self.assertEqual(hashlib.sha256(self.raw).hexdigest(),EXPECTED_SHA)
  self.assertEqual(hashlib.sha256(self.exe).hexdigest(),EXE_SHA)
 def test_corrected_condition_dispatcher(self):
  self.assertEqual(self.code[0x2c3b4:0x2c3bb],bytes.fromhex("5156575583ec08"))
  site=0x2c887
  self.assertEqual(self.code[site],0xe8)
  self.assertEqual(site+5+struct.unpack_from("<i",self.code,site+1)[0],0x2c3b4)
 def test_original_jump_table_relocations(self):
  for op,target in ((4,0x2c50a),(10,0x2c533)):
   site=0x2c368+4*op
   fx=self.image.fixup_at(1,site)
   self.assertEqual((fx.target_object,fx.target_offset),(1,target))
   self.assertEqual(struct.unpack_from("<I",self.code,site)[0],target)
 def test_predicate_branch_code(self):
  # opcode 4 tests source state[index] != 0; opcode 10 tests == 0
  self.assertEqual(self.code[0x2c51b:0x2c51d],bytes.fromhex("0f85"))
  self.assertEqual(self.code[0x2c54a:0x2c54c],bytes.fromhex("0f84"))
  self.assertEqual(self.code[0x2c50c:0x2c512],bytes.fromhex("8b15a4380400"))
  self.assertEqual(self.code[0x2c540:0x2c545],bytes.fromhex("a1a4380400"))
 def test_node_8_16_complementary(self):
  by_node={}
  for r in self.records:by_node.setdefault(r["node"],[]).append(r)
  self.assertEqual(set(by_node),{8,16})
  for node,idx in ((8,44),(16,46)):
   rows=by_node[node]
   self.assertEqual([(r["slot"],r["condition_opcode"],r["condition_index"],r["predicate"]) for r in rows],
                    [(0,4,idx,"nonzero"),(1,10,idx,"zero")])
 def test_conditional_action_alignment(self):
  blobs=parse_section6_blobs(self.raw)["blobs"]
  for cond in self.records:
   act=[a for a in blobs if a["kind"]=="blob27" and a["top_index"]==4 and a["node_index"]==cond["node"] and a["object_index"]==cond["slot"]]
   self.assertEqual(len(act),5 if cond["slot"]==0 else 7)
   transforms=[a for a in act if a["raw"][0] in (0x17,0x18)]
   self.assertEqual(len(transforms),2)
   sounds=[a for a in act if a["raw"][0]==0x28]
   self.assertEqual(len(sounds),1)
 def test_generated_ir_is_source_scoped(self):
  ir=json.loads(OUTPUT.read_text(encoding="utf8"))
  self.assertEqual(ir["records"],self.records)
  self.assertEqual(ir["source_sha256"],EXPECTED_SHA)
  self.assertNotIn("FIDELITY_PASS",ir["status"])
  self.assertIn("state_index_to_named_flag",ir["unverified"])
if __name__=="__main__":unittest.main(verbosity=2)