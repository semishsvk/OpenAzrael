from __future__ import annotations

from pathlib import Path
import json
import unittest

from tools.audio_lab.oa_audio_spectral_baseline import compare_spectral_baseline
from tools.audio_lab.oa_audio_spectral import (
    DEFAULT_DB_FLOOR,
    DEFAULT_FFT_SIZE,
    DEFAULT_FREQ_BINS,
    DEFAULT_HOP_SIZE,
    DEFAULT_TIME_BINS,
    OUTLIER_THRESHOLD,
)

class AudioLabSpectralBaselineTests(unittest.TestCase):
    def test_exact_manifest_matches(self):
        evidence = {
            "source_tree_sha256": "a"*64,
            "asset_count": 2,
            "analysis_fingerprint_sha256": "b"*64,
        }
        manifest = {
            "status": "PASS",
            "source_tree_sha256": "a"*64,
            "analysis_fingerprint_sha256": "b"*64,
            "source_unchanged": True,
            "errors": [],
            "assets": [{"filename":"A.wav"},{"filename":"B.wav"}],
        }
        self.assertEqual(compare_spectral_baseline(manifest, evidence), [])

    def test_fingerprint_drift_is_explicit(self):
        evidence = {
            "source_tree_sha256": "a"*64,
            "asset_count": 1,
            "analysis_fingerprint_sha256": "b"*64,
        }
        manifest = {
            "status": "PASS",
            "source_tree_sha256": "a"*64,
            "analysis_fingerprint_sha256": "c"*64,
            "source_unchanged": True,
            "errors": [],
            "assets": [{"filename":"A.wav"}],
        }
        diffs = compare_spectral_baseline(manifest, evidence)
        self.assertEqual([d["field"] for d in diffs], ["analysis_fingerprint_sha256"])

    def test_code_defaults_match_poc02_contract(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root/"data/audio_lab/al_poc_02_contract.json").read_text(encoding="utf-8"))
        defaults = contract["default_parameters"]
        self.assertEqual(DEFAULT_FFT_SIZE, defaults["fft_size"])
        self.assertEqual(DEFAULT_HOP_SIZE, defaults["hop_size"])
        self.assertEqual(DEFAULT_DB_FLOOR, defaults["spectrogram_db_floor"])
        self.assertEqual(DEFAULT_TIME_BINS, defaults["preview_time_bins"])
        self.assertEqual(DEFAULT_FREQ_BINS, defaults["preview_frequency_bins"])
        self.assertEqual(OUTLIER_THRESHOLD, defaults["outlier_threshold_robust_z"])

    def test_committed_evidence_is_consistent_with_poc01_and_contract(self):
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root/"data/audio_lab/al_poc_02_canonical_spectral_evidence.json").read_text(encoding="utf-8"))
        source = json.loads((root/"data/audio_lab/al_poc_01_canonical_source_evidence.json").read_text(encoding="utf-8"))
        contract = json.loads((root/"data/audio_lab/al_poc_02_contract.json").read_text(encoding="utf-8"))
        ir = json.loads((root/"data/audio/legacy_world_ir.json").read_text(encoding="utf-8"))
        names = {x["filename"] for x in ir["audio"]["sounds"]}
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["source_tree_sha256"], source["source_tree_sha256"])
        self.assertEqual(evidence["asset_count"], source["source_file_count"])
        self.assertEqual(evidence["asset_count"], 30)
        self.assertEqual(len(evidence["analysis_fingerprint_sha256"]), 64)
        self.assertEqual(evidence["parameters"]["fft_size"], contract["default_parameters"]["fft_size"])
        self.assertEqual(evidence["parameters"]["hop_size"], contract["default_parameters"]["hop_size"])
        self.assertEqual(evidence["parameters"]["spectrogram_db_floor"], contract["default_parameters"]["spectrogram_db_floor"])
        flagged = evidence["review_only_outliers"]
        self.assertEqual(flagged["flagged_assets"], 8)
        self.assertEqual(flagged["flagged_metrics"], 8)
        self.assertTrue(all(x["filename"] in names for x in flagged["assets"]))

if __name__ == "__main__":
    unittest.main()
