#!/usr/bin/env python3
"""Pin R.EXE opcode-01 guard and section-3 callback cleanup; no fidelity claim."""
import struct,unittest,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from le_bound_image_v312 import BoundLE
from analyze_world_runtime_serialization_v106 import parse_world
from build_well_interaction_source_v363 import derive,SOURCE
ROOT=SOURCE.parent
class CallbackOracle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.code=BoundLE.parse((ROOT/"R.EXE").read_bytes()).objects[0].data
  cls.world=SOURCE.read_bytes()
  cls.groups=derive(cls.world)
 def test_opcode_01_dispatch_address(self):
  self.assertEqual(struct.unpack_from("<I",self.code,0x1b09c+4)[0],0x1b222)
 def test_section3_object_array_and_guard(self):
  self.assertEqual(self.code[0x1b22b:0x1b230],bytes.fromhex("a1ec380400"))
  self.assertEqual(self.code[0x1b230:0x1b233],bytes.fromhex("8b0490"))
  self.assertEqual(self.code[0x1b233:0x1b237],bytes.fromhex("668b400c"))
  self.assertEqual(self.code[0x1b237:0x1b23a],bytes.fromhex("6685c0"))
 def test_calls_callback_cleanup_and_resets_object(self):
  site=0x1b249
  self.assertEqual(self.code[site],0xe8)
  self.assertEqual(site+5+struct.unpack_from("<i",self.code,site+1)[0],0x1a90c)
  self.assertEqual(self.code[0x1b263:0x1b269],bytes.fromhex("66c7400c0000"))
 def test_source_world_section3_count(self):
  parsed=parse_world(self.world)
  self.assertEqual(parsed["sections"][3]["count"],3)
 def test_all_four_source_records_index_section3_zero(self):
  rows=[a for g in self.groups for a in g["actions"] if a["opcode"]==1]
  self.assertEqual(len(rows),4)
  for a in rows:
   self.assertEqual(a["source_section3_index"],0)
   self.assertEqual(a["source_runtime_guard_offset"],12)
   self.assertEqual(a["source_handler"],"LE_object1:0x1B222")
   self.assertEqual(a["kind"],"opaque_state_action")
   self.assertEqual(a["meaning"],"SECTION3_CALLBACK_EFFECT_HOLD")
 def test_source_callback_queue_not_equated_to_well_transform(self):
  self.assertEqual(self.code[0x1a932:0x1a93f],bytes.fromhex("39cb75e366c78266470200ffff"))
  self.assertEqual(self.code[0x1a986:0x1a98d],bytes.fromhex("66891d7a470200"))
  # Original code scans ten slots and invalidates a matching ID with 0xFFFF.
  self.assertEqual(self.code[0x1a91f:0x1a922],bytes.fromhex("83fa0a"))
if __name__=="__main__":unittest.main(verbosity=2)