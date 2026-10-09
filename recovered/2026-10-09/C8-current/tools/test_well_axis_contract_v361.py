#!/usr/bin/env python3
"""Pin WORLD axis byte against original i386 instructions; reject guessed modes."""
import collections, hashlib, json, struct, sys, unittest
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_well_actions_v317 import inspect
from le_bound_image_v312 import BoundLE
ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
CONTRACT = ROOT / "data/tests/well_source_axis_contract_v361.json"
IR = ROOT / "data/runtime_generated/well_source_actions_v358.json"
class AxisEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = (CORPUS / "R.EXE").read_bytes()
        cls.world = (CORPUS / "WORLD.DAT").read_bytes()
        cls.image = BoundLE.parse(cls.exe)
        cls.c = cls.image.objects[0].data
        cls.d = cls.image.objects[1].data
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf8"))
        cls.rows = inspect(CORPUS / "WORLD.DAT")["records"]
    def test_source_hashes(self):
        self.assertEqual(hashlib.sha256(self.exe).hexdigest(), self.contract["exe_sha256"])
        self.assertEqual(hashlib.sha256(self.world).hexdigest(), self.contract["world_sha256"])
    def test_axis_byte_is_record_offset_9_in_both_handlers(self):
        for site in (0x1b624, 0x1b7fd):
            self.assertEqual(self.c[site:site+7], bytes.fromhex("8b4206c1f81850"))
        self.assertEqual(self.contract["axis_byte_offset"], 9)
    def test_rotation_axis_0_y_1_x_2_z(self):
        self.assertEqual(self.c[0x1a399:0x1a3a1], bytes.fromhex("c74424040000803f"))
        self.assertEqual(self.c[0x1a3a3:0x1a3aa], bytes.fromhex("c704240000803f"))
        self.assertEqual(self.c[0x1a3ac:0x1a3b4], bytes.fromhex("c74424080000803f"))
        self.assertEqual(self.contract["axis_to_source_vector_component"]["23"], {"0":1,"1":0,"2":2})
    def test_translation_axis_0_z_1_y_2_x(self):
        self.assertEqual(self.c[0x1a435:0x1a43d], bytes.fromhex("dd442418d95c2408"))
        self.assertEqual(self.c[0x1a43f:0x1a447], bytes.fromhex("dd442418d95c2404"))
        self.assertEqual(self.c[0x1a449:0x1a450], bytes.fromhex("dd442418d91c24"))
        self.assertEqual(self.contract["axis_to_source_vector_component"]["24"], {"0":2,"1":1,"2":0})
    def test_action_population_and_mode_is_not_axis_field(self):
        raw_counts = collections.Counter()
        for row in self.rows:
            self.assertNotIn("mode", row)
            self.assertIn(row["axis_code"],(0,1,2))
            self.assertEqual(self.world[row["offset"]+9],row["axis_code"])
            raw_counts[(row["opcode"],row["axis_code"])]+=1
        self.assertEqual(raw_counts, {(23,2):16,(24,1):4,(24,2):4})
    def test_scheduler_pi_scaling(self):
        for off in (0x6a80,0x603c):
            self.assertAlmostEqual(struct.unpack_from("<d",self.d,off)[0],3.141592654,places=9)
        for off in (0x2f25,0x1714,0x171c):
            self.assertAlmostEqual(struct.unpack_from("<d",self.d,off)[0],1/180,places=12)
    def test_generated_ir_explicit_axis(self):
        ir=json.loads(IR.read_text(encoding="utf8"))
        self.assertEqual(ir["source_sha256"],self.contract["world_sha256"])
        self.assertEqual(len(ir["records"]),24)
        for row in ir["records"]:
            self.assertIn("axis_code",row)
            self.assertNotIn("mode",row)
            self.assertEqual(self.world[row["source_offset"]+9],row["axis_code"])
    def test_no_premature_fidelity_promotion(self):
        for key in ("godot_coordinate_frame_verified","original_gameplay_trigger_verified","original_transform_composition_verified","production_motion_allowed"):
            self.assertIs(self.contract[key],False)
if __name__=="__main__":unittest.main(verbosity=2)