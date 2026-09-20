from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.audio_lab.common import ensure_output_outside_source
from tools.audio_lab.oa_audio_scan import main as scan_main
from tools.audio_lab.oa_audio_run_poc import main as run_poc
from tools.audio_lab.oa_audio_review_pack import main as review_main

class AudioLabSourceSafetyTests(unittest.TestCase):
    def test_output_guard_rejects_equal_and_nested_paths(self):
        with TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            with self.assertRaises(ValueError):
                ensure_output_outside_source(source, source)
            with self.assertRaises(ValueError):
                ensure_output_outside_source(source, source / "reports")
            sibling = Path(td) / "reports"
            self.assertEqual(ensure_output_outside_source(source, sibling), sibling.resolve())

    def test_scanner_rejects_output_inside_source_before_writing(self):
        with TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            nested = source / "reports"
            with self.assertRaises(SystemExit) as cm:
                scan_main([str(source), "--output-dir", str(nested)])
            self.assertEqual(cm.exception.code, 2)
            self.assertFalse(nested.exists())

    def test_orchestrator_rejects_output_inside_source_before_writing(self):
        with TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            nested = source / "reports"
            with self.assertRaises(SystemExit) as cm:
                run_poc([str(source), "--output-dir", str(nested)])
            self.assertEqual(cm.exception.code, 2)
            self.assertFalse(nested.exists())

    def test_review_pack_rejects_output_inside_source_when_source_root_is_known(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            source = base / "source"
            source.mkdir()
            nested = source / "review"
            with self.assertRaises(SystemExit) as cm:
                review_main([
                    str(base / "missing_manifest.json"),
                    str(base / "missing_reference.json"),
                    "--source-root", str(source),
                    "--output-dir", str(nested),
                ])
            self.assertEqual(cm.exception.code, 2)
            self.assertFalse(nested.exists())

if __name__ == "__main__":
    unittest.main()
