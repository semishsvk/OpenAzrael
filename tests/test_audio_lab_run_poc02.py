from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import struct
import unittest

import numpy as np

from tools.audio_lab.common import tree_digest
from tools.audio_lab.oa_audio_run_poc02 import main as run_poc02
from tools.audio_lab.oa_audio_spectral import analyze_file, spectral_fingerprint

def write_pcm16_wave(path: Path, samples: np.ndarray, sample_rate: int=8000) -> None:
    x=np.clip(np.asarray(samples,dtype=np.float64),-1.0,0.999969)
    pcm=np.rint(x*32767.0).astype("<i2").tobytes()
    fmt=struct.pack("<HHIIHH",1,1,sample_rate,sample_rate*2,2,16)
    body=b"WAVE"+b"fmt "+struct.pack("<I",16)+fmt+b"data"+struct.pack("<I",len(pcm))+pcm
    path.write_bytes(b"RIFF"+struct.pack("<I",len(body))+body)

def ir_row(path: Path, sample_rate: int=8000) -> dict:
    raw=path.read_bytes()
    frames=struct.unpack_from("<I",raw,40)[0]//2
    return {
        "filename":path.name,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "channels":1,
        "sample_rate":sample_rate,
        "sample_width_bits":16,
        "frames":frames,
        "duration_seconds":frames/sample_rate,
    }

class AudioLabRunPOC02Tests(unittest.TestCase):
    def test_end_to_end_canonical_spectral_runner(self):
        with TemporaryDirectory() as td:
            base=Path(td)
            src=base/"src"; src.mkdir()
            sr=8000
            t=np.arange(sr,dtype=np.float64)/sr
            a=src/"A.wav"; b=src/"B.wav"
            write_pcm16_wave(a,0.4*np.sin(2*np.pi*440*t),sr)
            write_pcm16_wave(b,0.2*np.sin(2*np.pi*880*t),sr)

            ir=base/"ir.json"
            ir.write_text(json.dumps({"audio":{"sounds":[ir_row(a,sr),ir_row(b,sr)]}}),encoding="utf-8")

            records=[]
            for path in (a,b):
                rec,_=analyze_file(path)
                records.append(rec)
            evidence=base/"evidence.json"
            evidence.write_text(json.dumps({
                "source_tree_sha256":tree_digest(src,[a,b]),
                "asset_count":2,
                "analysis_fingerprint_sha256":spectral_fingerprint(records),
            }),encoding="utf-8")

            out=base/"out"
            rc=run_poc02([
                str(src),
                "--output-dir",str(out),
                "--legacy-ir",str(ir),
                "--evidence",str(evidence),
            ])
            self.assertEqual(rc,0)
            summary=json.loads((out/"al_poc_02_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"],"PASS")
            self.assertTrue(all(summary["gates"].values()))
            self.assertEqual(summary["asset_count"],2)
            self.assertEqual(summary["baseline_diffs"],[])
            for name in (
                "canonical_source_report.json",
                "spectral_manifest.json",
                "spectral_review.html",
                "spectral_baseline_check.json",
            ):
                self.assertTrue((out/name).exists(),name)

    def test_output_inside_source_is_rejected(self):
        with TemporaryDirectory() as td:
            src=Path(td)/"src"; src.mkdir()
            write_pcm16_wave(src/"A.wav",np.zeros(100),8000)
            with self.assertRaises(SystemExit) as cm:
                run_poc02([str(src),"--output-dir",str(src/"reports")])
            self.assertEqual(cm.exception.code,2)
            self.assertFalse((src/"reports").exists())

if __name__=="__main__":
    unittest.main()
