from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.remaster_framework.corpus import discover_corpus


class CorpusDiscoveryTests(unittest.TestCase):
    def _make_demo_shape(self, root: Path, wav_count: int = 30) -> None:
        for name in (
            "PUZZLES.DAT",
            "ROOMS.DAT",
            "WORLD.DAT",
            "MUSIC.DAT",
            "R.EXE",
            "CHARACTE.DAT",
        ):
            (root / name).write_bytes(name.encode("ascii"))
        (root / "AMB0.SND").write_text("SAMPLE 0,0,0 S001.WAV\n", encoding="ascii")
        (root / "NPC0.DAT").write_text("0\n", encoding="ascii")
        for index in range(wav_count):
            (root / f"S{index:03d}.WAV").write_bytes(b"RIFF")

    def test_demo_profile_matches_evidence_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_demo_shape(root)

            result = discover_corpus(root)
            profile = result["profiles"][0]

            self.assertEqual(profile["profile_id"], "openazrael_demo_v1")
            self.assertEqual(profile["status"], "match")

    def test_retail_profile_matches_evidence_backed_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "PUZZLES.DAT",
                "OBJECTS.DAT",
                "ROOMS.DAT",
                "CHARACTE.DAT",
            ):
                (root / name).write_bytes(name.encode("ascii"))

            result = discover_corpus(root)
            profiles = {
                row["profile_id"]: row
                for row in result["profiles"]
            }

            self.assertEqual(
                profiles["openazrael_retail_v1"]["status"],
                "match",
            )
            self.assertEqual(
                profiles["openazrael_demo_v1"]["status"],
                "no_match",
            )

    def test_count_drift_is_partial_not_false_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_demo_shape(root, wav_count=29)

            result = discover_corpus(root)
            profile = result["profiles"][0]

            self.assertEqual(profile["status"], "partial")
            self.assertFalse(profile["expected_counts"][0]["pass"])

    def test_missing_anchor_is_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_demo_shape(root)
            (root / "PUZZLES.DAT").unlink()

            result = discover_corpus(root)
            profile = result["profiles"][0]

            self.assertEqual(profile["status"], "no_match")
            self.assertIn("PUZZLES.DAT", profile["missing_exact"])


if __name__ == "__main__":
    unittest.main()
