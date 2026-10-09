import unittest,sys,struct,hashlib
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_well_actions_v317 import inspect,EXPECTED
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))/"WORLD.DAT"
class WellTests(unittest.TestCase):
 def test_canonical(self):
  x=inspect(CORPUS);self.assertEqual(len(x["records"]),24);self.assertEqual(x["status"],"STRUCTURAL_PASS_FIDELITY_HOLD")
 def test_hash(self):self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest(),EXPECTED)
 def test_pairing(self):
  x=inspect(CORPUS);from collections import Counter
  counts=Counter((r["opcode"],r["object_id"]) for r in x["records"])
  self.assertEqual(set(counts.values()),{2,4})
 def test_17_integer_operand(self):
  x=inspect(CORPUS);v={r["operand_s16"] for r in x["records"] if r["opcode"]==23}
  self.assertEqual(v,{-9,-5,-1,1,5,9})
 def test_18_float_operand(self):
  x=inspect(CORPUS);v={r["operand_f32"] for r in x["records"] if r["opcode"]==24}
  self.assertEqual(v,{-3.0,-1.0,1.0,3.0})
 def test_fail_closed(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"WORLD.DAT";b=bytearray(CORPUS.read_bytes());b[100]^=1;f.write_bytes(b)
   with self.assertRaises(ValueError):inspect(f)
if __name__=="__main__":unittest.main(verbosity=2)