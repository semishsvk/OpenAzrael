import unittest
import struct
from audit_intro_mov_container_v309 import parse
class TestMovContainer(unittest.TestCase):
    def make(self):
        b=bytearray(128);b[:4]=bytes.fromhex("90ef12ab")
        struct.pack_into("<4H",b,4,40,12,640,480)
        return b
    def test_valid(self):
        x=parse(bytes(self.make()),"x")
        self.assertEqual(x["candidate_frame_count"],40)
        self.assertEqual(x["fidelity"],"HOLD")
        self.assertEqual(x["decoded_frames"],0)
    def test_magic(self):
        b=self.make();b[0]=0
        with self.assertRaises(ValueError):parse(bytes(b),"x")
    def test_truncated(self):
        with self.assertRaises(ValueError):parse(b"","x")
    def test_bad_dimensions(self):
        b=self.make();struct.pack_into("<H",b,8,0)
        with self.assertRaises(ValueError):parse(bytes(b),"x")
if __name__=="__main__":unittest.main()