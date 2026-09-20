from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import struct
import unittest

from tools.audio_lab.oa_audio_canonical_verify import verify_corpus

def write_pcm8(path: Path, samples: bytes, sample_rate: int=22050, terminal_pad: bool=True):
    fmt=struct.pack("<HHIIHH",1,1,sample_rate,sample_rate,1,8)
    body=b"WAVE"+b"fmt "+struct.pack("<I",16)+fmt+b"data"+struct.pack("<I",len(samples))+samples
    if terminal_pad and len(samples)&1:
        body += b"\0"
    path.write_bytes(b"RIFF"+struct.pack("<I",len(body))+body)

def ir_row(path: Path, sample_rate: int=22050):
    raw=path.read_bytes()
    # test fixtures are mono 8-bit PCM; data begins at byte 44
    data_bytes=struct.unpack_from("<I",raw,40)[0]
    return {
        "filename":path.name,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "channels":1,
        "sample_rate":sample_rate,
        "sample_width_bits":8,
        "frames":data_bytes,
        "duration_seconds":data_bytes/sample_rate,
    }

class CanonicalSourceVerifyTests(unittest.TestCase):
    def test_complete_exact_corpus_passes_and_reports_pad_warning(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            a=root/"A.WAV"; b=root/"B.WAV"
            write_pcm8(a,b"\x80\x81\x82\x83")
            write_pcm8(b,b"\x80\x81\x82",terminal_pad=False)
            ir={"audio":{"sounds":[ir_row(a),ir_row(b)]}}
            report=verify_corpus(root,ir)
            self.assertEqual(report["status"],"PASS")
            self.assertEqual(report["source_file_count"],2)
            self.assertEqual(report["errors"],0)
            self.assertEqual(report["warnings"],1)
            rows={r["filename"]:r for r in report["assets"]}
            self.assertTrue(rows["B.WAV"]["terminal_pad_missing"])

    def test_hash_mismatch_is_failure(self):
        with TemporaryDirectory() as td:
            root=Path(td); a=root/"A.WAV"
            write_pcm8(a,b"\x80\x81")
            row=ir_row(a); row["sha256"]="0"*64
            report=verify_corpus(root,{"audio":{"sounds":[row]}})
            self.assertEqual(report["status"],"FAIL")
            self.assertGreater(report["errors"],0)

    def test_missing_and_extra_are_failures(self):
        with TemporaryDirectory() as td:
            root=Path(td); a=root/"A.WAV"; extra=root/"EXTRA.WAV"
            write_pcm8(a,b"\x80\x81"); write_pcm8(extra,b"\x80\x81")
            missing=root/"MISSING.WAV"; write_pcm8(missing,b"\x80\x81")
            row_missing=ir_row(missing); missing.unlink()
            report=verify_corpus(root,{"audio":{"sounds":[ir_row(a),row_missing]}})
            self.assertEqual(report["status"],"FAIL")
            self.assertEqual(report["missing_expected_assets"],["MISSING.WAV"])
            self.assertEqual(report["unexpected_assets"],["EXTRA.WAV"])

if __name__ == "__main__":
    unittest.main()
