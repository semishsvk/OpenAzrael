"""Decoder invariants, malformed-input tests and authoritative ATDEMO fixtures."""
import os
import struct
import unittest
from pathlib import Path
import decode_intro_mov_v311 as d

def packet(kind, payload):
    return struct.pack('<IHI', 0x0123FEDC, kind, len(payload)) + bytes(6) + payload

def fixture(packets=None, count=1):
    packets = packets or [packet(5, bytes(768)), packet(1, bytes(range(16)))]
    body = b''.join(packets)
    head = struct.pack('<I4H', 0xAB12EF90, count, 12, 4, 4) + bytes(18)
    return head + struct.pack('<IHIIH', 0xEE9901CF, len(packets), len(body), 0, 0) + body

def huff_fixture():
    table = [0] * 1024
    table[512:514] = [65, 66]
    return struct.pack('<II', 4, 256) + struct.pack('<1024H', *table) + bytes([10, 0, 0, 0])

class DecoderTests(unittest.TestCase):
    def test_huffman_lsb(self):
        self.assertEqual(d.unpack_huffman(huff_fixture(), 4)[0], b'ABAB')
    def test_huffman_cycle(self):
        raw = bytearray(huff_fixture()); struct.pack_into('<H', raw, 8 + 512 * 2, 256)
        with self.assertRaises(d.DecodeError): d.unpack_huffman(raw, 4)
    def test_huffman_outside_child(self):
        raw = bytearray(huff_fixture()); struct.pack_into('<H', raw, 8 + 512 * 2, 999)
        with self.assertRaises(d.DecodeError): d.unpack_huffman(raw, 4)
    def test_huffman_truncated_word(self):
        with self.assertRaises(d.DecodeError): d.unpack_huffman(huff_fixture()[:-1], 4)
    def test_huffman_bad_size(self):
        with self.assertRaises(d.DecodeError): d.unpack_huffman(huff_fixture(), d.MAX_OUTPUT + 1)
    def test_huffman_extra_word(self):
        with self.assertRaises(d.DecodeError): d.unpack_huffman(huff_fixture() + bytes(4), 4)
    def test_container_keyframe(self):
        result = d.decode_movie(fixture())
        self.assertEqual(result['frames'][0]['indices'], bytes(range(16)))
        self.assertEqual(result['header']['opaque_u16_at_6'], 12)
    def test_header_not_depth(self):
        self.assertNotIn('depth', d.read_container(fixture())[0])
    def test_container_truncations(self):
        raw = fixture()
        for cut in (0, 5, 29, 30, 45, 62, len(raw)-1):
            with self.subTest(cut=cut), self.assertRaises(d.DecodeError): d.decode_movie(raw[:cut])
    def test_container_magic(self):
        raw = bytearray(fixture()); raw[0] ^= 1
        with self.assertRaises(d.DecodeError): d.decode_movie(raw)
    def test_packet_magic(self):
        raw = bytearray(fixture()); raw[46] ^= 1
        with self.assertRaises(d.DecodeError): d.decode_movie(raw)
    def test_declared_count(self):
        with self.assertRaises(d.DecodeError): d.decode_movie(fixture(count=2))
    def test_unknown_packet(self):
        with self.assertRaises(d.DecodeError): d.decode_movie(fixture([packet(99,b'x')]))
    def test_extra_file_bytes(self):
        with self.assertRaises(d.DecodeError): d.decode_movie(fixture() + b'junk')
    def test_delta_without_keyframe(self):
        with self.assertRaises(d.DecodeError): d.decode_movie(fixture([packet(5,bytes(768)),packet(4,b'\x01\x01')]))
    def test_bad_palette(self):
        with self.assertRaises(d.DecodeError): d.decode_movie(fixture([packet(5,bytes([255])*768),packet(1,bytes(16))]))
    def test_skip(self):
        previous = bytes(range(16))
        self.assertEqual(d.decode_delta(b'\x01\x01', previous, bytes(16), 4, 4)[0], previous)
    def test_skip_overflow(self):
        with self.assertRaises(d.DecodeError): d.decode_delta(b'\x01\x00', bytes(16), bytes(16), 4, 4)
    def test_raw_tile(self):
        tile = bytes(range(16))
        self.assertEqual(d.decode_delta(b'\x03' + tile, bytes(16), bytes(16), 4, 4)[0], tile)
    def test_small_motion(self):
        previous = bytes(range(16))
        self.assertEqual(d.decode_delta(b'\x02\x77', previous, bytes(16), 4, 4)[0], previous)
    def test_wide_previous_motion(self):
        previous = bytes(range(16))
        self.assertEqual(d.decode_delta(bytes([0,127,63]), previous, bytes(16), 4, 4)[0], previous)
    def test_current_frame_motion(self):
        # First tile is literal 9; second tile must copy the just-decoded first tile.
        stream = bytes([3]) + bytes([9])*16 + bytes([123,191])
        got, stats = d.decode_delta(stream, bytes([2])*32, bytes([7])*32, 8, 4)
        self.assertEqual(got, bytes([9])*32)
        self.assertEqual(stats['opcodes']['current_motion'], 1)
    def test_motion_outside_frame(self):
        with self.assertRaises(d.DecodeError): d.decode_delta(b'\x02\x00', bytes(16), bytes(16), 4, 4)
    def test_delta_truncation(self):
        with self.assertRaises(d.DecodeError): d.decode_delta(b'\x03'+bytes(15), bytes(16), bytes(16), 4, 4)
    def test_delta_unconsumed(self):
        with self.assertRaises(d.DecodeError): d.decode_delta(b'\x01\x01\xff', bytes(16), bytes(16), 4, 4)
    def test_pcm_byte_identity(self):
        audio = bytes(range(256))
        result = d.decode_movie(fixture([packet(5,bytes(768)), packet(1,bytes(16)), packet(6,audio)]))
        self.assertEqual(result['audio_u8'], audio)
        self.assertEqual(result['channels'], 1)

class CorpusTests(unittest.TestCase):
    def test_all_authoritative_movies(self):
        root = Path(os.environ['OPENAZRAEL_CORPUS'])
        expected = {'MINDLOGO.MOV': (40,4,0), 'INTRO.MOV': (50,50,121378),
                    'MOV/INTRO.MOV': (55,55,0), 'MOV/DEMO.MOV': (100,90,0)}
        for name, (frames,unique,audio_bytes) in expected.items():
            with self.subTest(file=name):
                data = (root/name).read_bytes()
                self.assertEqual(d.sha(data), d.SOURCE_SHA[name])
                result = d.decode_movie(data)
                self.assertEqual(len(result['frames']), frames)
                self.assertEqual(len(set(x['index_sha256'] for x in result['frames'])), unique)
                self.assertEqual(len(result['audio_u8']), audio_bytes)
                if audio_bytes:
                    self.assertEqual(d.sha(result['audio_u8']), '08dfdc5c00764e5c0ec9d79d948c3bba52b7c80a17fde3b13b36e68d031ee847')
if __name__ == '__main__': unittest.main(verbosity=2)
