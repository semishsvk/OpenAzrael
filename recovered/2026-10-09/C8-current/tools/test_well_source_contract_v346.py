#!/usr/bin/env python3
"""Well Room source-grounded regression contract; never promotes fidelity."""
import hashlib, json, struct, sys, unittest
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_well_actions_v317 import inspect
from analyze_world_sound_record_fields_v113 import parse_section0
from le_bound_image_v312 import BoundLE
ROOT=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
MANIFEST=Path(__file__).resolve().parents[1]/"data/R7.textured.v44.manifest.json"
NAMES={98:"well_lev02",99:"well_weel2",100:"well_pzpi1",101:"well_weel3",222:"well_lev01",223:"well_weel4",224:"well_pzpi2",225:"well_weel1",1145:"well_pzpa1",1148:"well_pzpa2"}
class SourceContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.world=(ROOT/"WORLD.DAT").read_bytes()
  cls.exe=(ROOT/"R.EXE").read_bytes()
  cls.rows=inspect(ROOT/"WORLD.DAT")["records"]
  cls.sec,_=parse_section0(cls.world)
  cls.manifest=json.loads(MANIFEST.read_text())
  cls.code=BoundLE.parse(cls.exe).objects[0].data
  cls.data=BoundLE.parse(cls.exe).objects[1].data
 def test_object_identity(self):
  for idx,name in NAMES.items():self.assertEqual(self.sec[idx]["name"],name)
 def test_manifest_coverage(self):
  present={x["object"] for x in self.manifest["objects"]}
  self.assertTrue(set(NAMES.values())<=present)
 def test_parent_binding(self):
  objects={x["object"]:x for x in self.manifest["objects"]}
  self.assertEqual(objects["well_pzpi1"]["parent"],"well_pzpa1")
  self.assertEqual(objects["well_pzpi2"]["parent"],"well_pzpa2")
 def test_actions_only_bound_targets(self):
  self.assertEqual({x["object_id"] for x in self.rows},set(NAMES))
 def test_source_angle_constants(self):
  self.assertAlmostEqual(struct.unpack_from("<d",self.data,0x6a80)[0],3.141592654,places=9)
  self.assertAlmostEqual(struct.unpack_from("<d",self.data,0x2f25)[0],1/180,places=12)
 def test_scheduler_tick_guard(self):
  self.assertEqual(self.code[0x47d3:0x47db],bytes.fromhex("66833d9a1d010000"))
  self.assertEqual(self.code[0x47db:0x47dd],bytes.fromhex("7505"))
  self.assertEqual(self.code[0x47dd],0xe8)
 def test_scheduler_queue_head(self):
  self.assertEqual(self.code[0xc710:0xc711],b"\x52")
  self.assertEqual(self.code[0xc717:0xc71c],bytes.fromhex("a338230200"))
 def test_release_hold(self):
  self.assertEqual(inspect(ROOT/"WORLD.DAT")["status"],"STRUCTURAL_PASS_FIDELITY_HOLD")
if __name__=="__main__":unittest.main(verbosity=2)