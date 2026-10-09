#!/usr/bin/env python3
"""Pin opcode 0x04 WORLD state-write semantics to original R.EXE instructions."""
import hashlib,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from le_bound_image_v312 import BoundLE
from analyze_world_runtime_serialization_v106 import parse_world
from build_well_interaction_source_v363 import derive,SOURCE,EXPECTED
ROOT=SOURCE.parent
class SourceStateWrite(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.image=BoundLE.parse((ROOT/"R.EXE").read_bytes())
  cls.code=cls.image.objects[0].data
  cls.world=SOURCE.read_bytes()
  cls.groups={(g["node"],g["slot"]):g for g in derive(cls.world)}
 def test_handler_table_opcode4(self):
  site=0x1b09c+4*0x04
  self.assertEqual(struct.unpack_from("<I",self.code,site)[0],0x1b2b1)
  fx=self.image.fixup_at(1,site)
  self.assertEqual((fx.target_object,fx.target_offset),(1,0x1b2b1))
 def test_handler_writes_same_array_as_condition(self):
  self.assertEqual(self.code[0x1b2ba:0x1b2c0],bytes.fromhex("8b15a4380400"))
  self.assertEqual(self.code[0x1b2cb:0x1b2ce],bytes.fromhex("668902"))
  self.assertEqual(self.code[0x2c50e:0x2c512],bytes.fromhex("a4380400"))
  self.assertEqual(self.code[0x2c541:0x2c545],bytes.fromhex("a4380400"))
 def test_world_state_array_is_101(self):
  parsed=parse_world(self.world)
  self.assertTrue(parsed["consumed_exactly_to_eof"])
  self.assertEqual(parsed["sections"][4]["count"],101)
  self.assertEqual(parsed["sections"][4]["stream_records"],0)
 def test_source_state_transitions(self):
  expect={(8,0):[(44,0)],(8,1):[(44,1),(42,0),(43,0)],
          (16,0):[(46,0)],(16,1):[(46,1),(42,0),(43,0)]}
  for key,transitions in expect.items():
   actions=[a for a in self.groups[key]["actions"] if a["kind"]=="state_write"]
   self.assertEqual([(a["source_state_index"],a["source_state_value"]) for a in actions],transitions)
 def test_opaque_opcode01_is_not_pretended_known(self):
  for node in (8,16):
   for slot in (0,1):
    extra=[a for a in self.groups[(node,slot)]["actions"] if a["opcode"]==1]
    self.assertEqual(len(extra),1)
    self.assertEqual(extra[0]["kind"],"opaque_state_action")
 def test_world_hash(self):
  self.assertEqual(hashlib.sha256(self.world).hexdigest(),EXPECTED)
if __name__=="__main__":unittest.main(verbosity=2)