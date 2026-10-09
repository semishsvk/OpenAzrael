import struct,unittest
from audit_intro_mov_header_v310 import analyze
class TestHeader(unittest.TestCase):
 def make(self):
  b=bytearray(128);b[:4]=bytes.fromhex("90ef12ab");struct.pack_into("<4H",b,4,40,12,640,480);return b
 def test_width_is_not_offset(self):
  b=self.make();struct.pack_into("<I",b,20,640);x=analyze(b,"x");self.assertEqual(x["header_words"][2]["classifications"],["width"])
 def test_ambiguous_is_not_proven(self):
  b=self.make();struct.pack_into("<I",b,20,96);x=analyze(b,"x");self.assertEqual(x["header_words"][2]["classifications"],["in_file_numeric_candidate_not_proven_offset"])
 def test_invalid(self):
  with self.assertRaises(ValueError):analyze(b"bad","x")
 def test_fail_closed(self):
  x=analyze(self.make(),"x");self.assertFalse(x["frame_boundaries_verified"]);self.assertEqual(x["decoded_frames"],0)
if __name__=="__main__":unittest.main()