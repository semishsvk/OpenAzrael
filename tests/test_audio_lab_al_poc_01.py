from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import struct
import unittest

from tools.audio_lab.common import parse_wave, sha256_file
from tools.audio_lab.oa_audio_scan import main as scan_main
from tools.audio_lab.oa_audio_validate import validate

def write_pcm8_wave(path: Path, samples: bytes, sample_rate: int = 22050, add_terminal_pad: bool = True) -> None:
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate, 1, 8)
    fmt_chunk = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    data_chunk = b"data" + struct.pack("<I", len(samples)) + samples
    if add_terminal_pad and (len(samples) & 1):
        data_chunk += b"\0"
    body = b"WAVE" + fmt_chunk + data_chunk
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)

def write_ir(path: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps({"audio": {"sounds": entries}}), encoding="utf-8")

class AudioLabALPOC01Tests(unittest.TestCase):
    def test_tolerates_missing_terminal_riff_pad_without_mutation(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "S137.WAV"
            write_pcm8_wave(p, bytes([128, 129, 130]), add_terminal_pad=False)
            before = p.read_bytes()
            parsed = parse_wave(p)
            self.assertTrue(parsed["valid"])
            self.assertTrue(parsed["terminal_pad_missing"])
            self.assertEqual(parsed["data_bytes"], 3)
            self.assertEqual(p.read_bytes(), before)

    def test_pcm_metadata_and_waveform(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "tone.wav"
            write_pcm8_wave(p, bytes([128, 140, 160, 200, 128, 80, 40, 128]))
            parsed = parse_wave(p)
            self.assertEqual(parsed["audio_format"], 1)
            self.assertEqual(parsed["channels"], 1)
            self.assertEqual(parsed["sample_rate"], 22050)
            self.assertEqual(parsed["sample_width_bits"], 8)
            self.assertEqual(parsed["frames"], 8)
            self.assertTrue(parsed["waveform_bins"])
            self.assertGreater(parsed["peak"], 0)

    def test_scan_is_deterministic_complete_and_source_safe(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            src = base / "demo"
            src.mkdir()
            write_pcm8_wave(src / "B.WAV", bytes([128, 130, 140, 128]))
            write_pcm8_wave(src / "a.wav", bytes([128, 120, 100, 128]))
            hashes_before = {p.name: sha256_file(p) for p in src.iterdir()}

            fp = base / "fingerprints.json"
            fp.write_text(json.dumps({"entries": [
                {"path": "assets/audio/a.wav", "sha256": hashes_before["a.wav"]},
            ]}), encoding="utf-8")
            ir = base / "legacy_world_ir.json"
            write_ir(ir, [
                {"filename":"a.wav","sha256":hashes_before["a.wav"],"channels":1,"sample_rate":22050,"sample_width_bits":8,"positional_ambient_references":[]},
                {"filename":"B.WAV","sha256":hashes_before["B.WAV"],"channels":1,"sample_rate":22050,"sample_width_bits":8,"positional_ambient_references":["OA_AMB_TEST"]},
            ])

            refs = base / "refs"
            refs.mkdir()
            (refs / "event.json").write_text('{"asset":"a.wav"}', encoding="utf-8")
            (refs / "runtime.gd").write_text('const SAMPLE = "a.wav"', encoding="utf-8")

            out1, out2 = base / "out1", base / "out2"
            args = ["--reference-root", str(refs), "--fingerprints", str(fp), "--legacy-ir", str(ir)]
            self.assertEqual(scan_main([str(src), "--output-dir", str(out1), *args]), 0)
            self.assertEqual(scan_main([str(src), "--output-dir", str(out2), *args]), 0)

            m1 = (out1 / "audio_manifest.json").read_bytes()
            m2 = (out2 / "audio_manifest.json").read_bytes()
            self.assertEqual(m1, m2)
            hashes_after = {p.name: sha256_file(p) for p in src.iterdir()}
            self.assertEqual(hashes_before, hashes_after)

            manifest = json.loads(m1)
            self.assertEqual([a["path"] for a in manifest["assets"]], ["a.wav", "B.WAV"])
            self.assertTrue(manifest["qa"]["expected_corpus_complete"])
            self.assertEqual(manifest["qa"]["expected_corpus_count"], 2)
            self.assertEqual(manifest["qa"]["runtime_mapped_assets"], 2)
            self.assertEqual(validate(manifest, src), [])

    def test_missing_expected_asset_fails_corpus_gate(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            src = base / "demo"
            src.mkdir()
            write_pcm8_wave(src / "x.wav", bytes([128, 129, 130, 131]))
            xhash = sha256_file(src / "x.wav")
            ir = base / "legacy_world_ir.json"
            write_ir(ir, [
                {"filename":"x.wav","sha256":xhash,"channels":1,"sample_rate":22050,"sample_width_bits":8},
                {"filename":"missing.wav","sha256":"1"*64,"channels":1,"sample_rate":22050,"sample_width_bits":8},
            ])
            fp = base / "fingerprints.json"
            fp.write_text('{"entries":[]}', encoding="utf-8")
            out = base / "out"
            rc = scan_main([str(src), "--output-dir", str(out), "--reference-root", str(base), "--fingerprints", str(fp), "--legacy-ir", str(ir)])
            self.assertEqual(rc, 2)
            manifest = json.loads((out / "audio_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["qa"]["expected_corpus_complete"])
            self.assertEqual(manifest["qa"]["missing_expected_assets"], ["missing.wav"])

    def test_fingerprint_mismatch_fails(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            src = base / "demo"
            src.mkdir()
            write_pcm8_wave(src / "x.wav", bytes([128, 129, 130, 131]))
            fp = base / "fingerprints.json"
            fp.write_text(json.dumps({"entries": [
                {"path": "assets/audio/x.wav", "sha256": "0" * 64}
            ]}), encoding="utf-8")
            ir = base / "legacy_world_ir.json"
            write_ir(ir, [])
            out = base / "out"
            rc = scan_main([str(src), "--output-dir", str(out), "--reference-root", str(base), "--fingerprints", str(fp), "--legacy-ir", str(ir)])
            self.assertEqual(rc, 2)
            manifest = json.loads((out / "audio_manifest.json").read_text(encoding="utf-8"))
            codes = [i["code"] for i in manifest["assets"][0]["issues"]]
            self.assertIn("AUD007_FINGERPRINT_MISMATCH", codes)

    def test_metadata_mismatch_fails(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            src = base / "demo"
            src.mkdir()
            write_pcm8_wave(src / "x.wav", bytes([128, 129, 130, 131]), sample_rate=22050)
            ir = base / "legacy_world_ir.json"
            write_ir(ir, [{
                "filename":"x.wav","sha256":sha256_file(src/"x.wav"),
                "channels":1,"sample_rate":11025,"sample_width_bits":8
            }])
            fp = base / "fingerprints.json"
            fp.write_text('{"entries":[]}', encoding="utf-8")
            out = base / "out"
            rc = scan_main([str(src), "--output-dir", str(out), "--reference-root", str(base), "--fingerprints", str(fp), "--legacy-ir", str(ir)])
            self.assertEqual(rc, 2)
            manifest = json.loads((out / "audio_manifest.json").read_text(encoding="utf-8"))
            codes = [i["code"] for i in manifest["assets"][0]["issues"]]
            self.assertIn("AUD012_METADATA_MISMATCH", codes)

    def test_sha256_is_exact(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "x.bin"
            p.write_bytes(b"OpenAzrael")
            self.assertEqual(sha256_file(p), hashlib.sha256(b"OpenAzrael").hexdigest())

if __name__ == "__main__":
    unittest.main()
