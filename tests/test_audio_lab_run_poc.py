from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import struct
import unittest

from tools.audio_lab.common import sha256_file
from tools.audio_lab.oa_audio_run_poc import main as run_poc

def write_pcm8_wave(path: Path, samples: bytes, sample_rate: int = 22050) -> None:
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate, 1, 8)
    fmt_chunk = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    data_chunk = b"data" + struct.pack("<I", len(samples)) + samples
    if len(samples) & 1:
        data_chunk += b"\0"
    body = b"WAVE" + fmt_chunk + data_chunk
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)

class AudioLabRunPOCTests(unittest.TestCase):
    def test_end_to_end_poc_pass(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            src = base / "src"
            src.mkdir()
            a = src / "A.wav"
            b = src / "B.wav"
            write_pcm8_wave(a, bytes([128, 130, 140, 128]))
            write_pcm8_wave(b, bytes([128, 120, 100, 128]))

            ir = base / "ir.json"
            ir.write_text(json.dumps({
                "audio": {
                    "sounds": [
                        {"filename":"A.wav","sha256":sha256_file(a),"channels":1,"sample_rate":22050,"sample_width_bits":8,"positional_ambient_references":[]},
                        {"filename":"B.wav","sha256":sha256_file(b),"channels":1,"sample_rate":22050,"sample_width_bits":8,"positional_ambient_references":["OA_AMB_B"]},
                    ],
                    "ambient_emitters": [
                        {"emitter_id":"OA_AMB_B","sample":"B.wav","room_id":1,"source":{"file":"AMB1.SND"}}
                    ],
                }
            }), encoding="utf-8")
            graph = base / "graph.json"
            graph.write_text(json.dumps({
                "graphs":{"G":{"actions":[{"op":"play_sound","asset":"A.wav"}]}}
            }), encoding="utf-8")
            fp = base / "fp.json"
            fp.write_text('{"entries":[]}', encoding="utf-8")
            refs = base / "refs"
            refs.mkdir()
            out = base / "out"

            rc = run_poc([
                str(src),
                "--output-dir", str(out),
                "--reference-root", str(refs),
                "--fingerprints", str(fp),
                "--legacy-ir", str(ir),
                "--event-graph", str(graph),
            ])
            self.assertEqual(rc, 0)
            summary = json.loads((out / "al_poc_01_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "PASS")
            self.assertTrue(all(summary["gates"].values()))
            self.assertEqual(summary["inventory"]["assets"], 2)
            self.assertEqual(summary["inventory"]["runtime_mapped"], 2)
            self.assertEqual(summary["inventory"]["expected_unmapped"], 0)
            self.assertEqual(summary["inventory"]["unexpected_orphans"], 0)
            self.assertEqual(summary["review"]["priority_counts"]["P4"], 2)
            for name in (
                "audio_reference_report.json",
                "audio_review_pack.json",
                "audio_review_pack.html",
            ):
                self.assertTrue((out / name).is_file(), name)

if __name__ == "__main__":
    unittest.main()
