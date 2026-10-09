#!/usr/bin/env python3
"""Demo R7 Niamh source/visual contract, backed by authentic native image evidence.

This is NOT an original engine semantics or timing fidelity PASS.
"""
from pathlib import Path
import hashlib,json,os,sys,unittest
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/reconstruction/niamh_visual_calibration_v415.json"
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS",
 "F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
ROOM=ROOT/"assets/rooms/R7.glb"
MANAGER=ROOT/"scripts/room_manager.gd"
HELPER=ROOT/"scripts/niamh_visual_calibration_v415.gd"

def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()

class SourceMeasuredVisual(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.meta=json.loads(CONTRACT.read_text(encoding="utf8"))
  cls.source=cls.meta["source_authority"]
  cls.fit=cls.meta["measured_transform"]
  cls.scene=trimesh.load(ROOM,force="scene")
 def test_demo_scope_not_retail(self):
  self.assertEqual(self.meta["version"],415)
  self.assertEqual(self.source["room"],"R7")
  self.assertEqual(self.meta["project_scope"],"OpenAzrael Demo C8 R7 only; NOT Retail and NOT universal framework")
  self.assertFalse(self.meta["candidate_8_promotion_allowed"])
 def test_original_authoritative_hashes(self):
  for f,key in (("R.EXE","read_only_original_R_EXE_SHA256"),
                ("TEXTURES/NIAMH.XAF","NIAMH_XAF_SHA256"),
                ("NIAMH.ANI","NIAMH_ANI_SHA256")):
   path=CORPUS/f
   self.assertTrue(path.is_file())
   self.assertEqual(digest(path),self.source[key])
 def test_world_original_well_root_is_authoritative(self):
  t,name=self.scene.graph["wel_well__WELL_WELLWALL"]
  self.assertTrue(np.allclose(t[:3,3],self.source["original_well_world_root_xyz"],atol=.2))
  self.assertEqual(self.source["well_source_object"],"wel_well__WELL_WELLWALL")
 def test_source_original_actor_proxy_not_modified(self):
  t,name=self.scene.graph["nibody__mesh"]
  self.assertTrue(np.allclose(t[:3,3],self.source["actor_baseline_world_root_xyz"],atol=.2))
  self.assertEqual(self.source["source_actor_proxy"],"nibody")
 def test_empirical_transform_not_misread_height_metadata(self):
  self.assertTrue(self.fit["NIAMH_ANI_HEIGHT33_IS_NOT_TREATED_AS_TRANSLATION"])
  self.assertEqual(self.fit["vertical_offset"],40.0)
  self.assertEqual(self.fit["yaw_degrees"],90.0)
  self.assertEqual(self.fit["horizontal_position"],"well_source_object.global_position.xz")
  self.assertEqual(self.fit["transparency_override"],"NONE")
  self.assertEqual(self.fit["depth_policy"],"SOURCE_OPAQUE_WITH_STANDARD_DEPTH_TEST")
 def test_multiframe_original_evidence_identifiers(self):
  records=self.meta["source_native_capture_evidence"]
  self.assertEqual(len(records),6)
  self.assertEqual([r["file"] for r in records],[f"r_{n:03d}.raw1.png" for n in range(3,9)])
  self.assertTrue(all(len(r["sha256"])==64 for r in records))
  evidence=self.meta["multi_frame_error"]
  self.assertEqual(evidence["frames"],6)
  self.assertGreater(evidence["mean_relative_error_reduction_percent"],34)
  self.assertGreater(evidence["min_relative_error_reduction_percent"],30)
  self.assertEqual(evidence["status"],"ORIGINAL_FRAME_VISUAL_ALIGNMENT_IMPROVED_NOT_PIXEL_EXACT")
 def test_helper_must_fail_closed_and_be_source_scoped(self):
  s=HELPER.read_text(encoding="utf8")
  for marker in ("HOLD_VISUAL_CALIBRATION","ORIGINAL_R_EXE","ORIGINAL_NIAMH_XAF",
                 "NO_ORIGINAL_FRAMES","SOURCE_WORLD_MOVED","WRONG_SOURCE",
                 "UNTESTED_PARAMETER","APPLIED_ORIGINAL_FRAME_CALIBRATION_PROVISIONAL"):
   if marker=="NO_ORIGINAL_FRAMES":marker="NO_ORIGINAL_FRAMES"
   self.assertIn(marker,s)
  self.assertIn('height-40.0',s)
  self.assertIn("character_root.rotate_y",s)
 def test_only_explicit_niamh_source_room_calibrated(self):
  s=MANAGER.read_text(encoding="utf8")
  self.assertIn('if character == "Niamh":',s)
  self.assertIn('preload("res://scripts/niamh_visual_calibration_v415.gd").apply(character_root, target, current_room)',s)
  self.assertIn('character_root.global_position = target.global_position',s)
  self.assertIn('_prepare_source_character_materials(character_root)',s)
  self.assertEqual(s.count('preload("res://scripts/niamh_visual_calibration_v415.gd").apply'),1)
 def test_source_animation_immutable_and_continuity(self):
  import re
  src=(ROOT/"assets/characters/Niamh/NOLOOP1.tres").read_text(encoding="utf8")
  self.assertIn('resource_name = "NOLOOP1"',src)
  self.assertIn('length = 0.933333333',src) # still provisional source clock
  doc=self.meta["fidelity_holds"]
  self.assertTrue(any("time base" in x for x in doc))
  self.assertTrue(any("Retail" in x or "retail" in x for x in doc))
 def test_negative_practice_explicit_not_accepted_as_fidelity(self):
  self.assertEqual(self.meta["evidence_class"],"ORIGINAL_RUNTIME_FRAME_VISUAL_FIT_PROVISIONAL")
  self.assertNotEqual(self.meta["multi_frame_error"]["status"],"PIXEL_EXACT_FIDELITY_PASS")

if __name__=="__main__":
 result=unittest.main(verbosity=2,exit=False)
 success=result.result.wasSuccessful()
 print("NIAMH_VISUAL_SOURCE_V415 "+json.dumps({
  "status":"PASS" if success else "FAIL","checks":result.result.testsRun,
  "failed":[str(x[0]) for x in result.result.failures+result.result.errors],
  "scope":"Demo R7 only, native-original measured render fit, timing and retail fidelity HOLD"
 }))
 sys.exit(0 if success else 1)
