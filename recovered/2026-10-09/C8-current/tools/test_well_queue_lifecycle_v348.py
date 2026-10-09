#!/usr/bin/env python3
"""Source-grounded queue lifecycle checks for C8. Never grants fidelity PASS."""
import unittest,sys,struct
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from le_bound_image_v312 import BoundLE
ROOT=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
class Queue(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.code=BoundLE.parse((ROOT/"R.EXE").read_bytes()).objects[0].data
 def call(self,site,target):
  self.assertEqual(self.code[site],0xe8)
  self.assertEqual(site+5+struct.unpack_from("<i",self.code,site+1)[0],target)
 def test_tick_caller(self):self.call(0x47dd,0x1d660)
 def test_tick_dispatch(self):self.call(0x1d660,0xc764)
 def test_flush_callers(self):
  for x in (0x2c3c,0x1afd2,0x1d1b5):self.call(x,0xc91c)
 def test_head_insert(self):
  self.assertEqual(self.code[0xc717:0xc71c],bytes.fromhex("a338230200"))
  self.assertEqual(self.code[0xc71c:0xc71f],bytes.fromhex("89501e"))
 def test_pause_guard(self):
  self.assertEqual(self.code[0x47d3:0x47db],bytes.fromhex("66833d9a1d010000"))
  self.assertEqual(self.code[0x47db:0x47dd],bytes.fromhex("7505"))
 def test_progress_increment(self):
  self.assertEqual(self.code[0x410b4:0x410c4],bytes.fromhex("d98324010000d88320010000c6434401"))
if __name__=="__main__":unittest.main(verbosity=2)