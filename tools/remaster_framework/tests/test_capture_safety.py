from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
import unittest

from tools.remaster_framework.capture_safety import (
    CaptureLease,
    CaptureSafetyError,
    run_monitored_capture,
)


class CaptureSafetyTests(unittest.TestCase):
    def test_live_lock_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "capture.lock"
            lease = CaptureLease.acquire(lock, {"test": True})
            self.addCleanup(lease.release)
            with self.assertRaises(CaptureSafetyError) as caught:
                CaptureLease.acquire(lock, {"second": True})
            self.assertEqual(caught.exception.code, "CAPTURE_LOCK_HELD")

    def test_stale_lock_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "capture.lock"
            lock.write_text(
                json.dumps({"pid": 999999999, "nonce": "stale"}),
                encoding="utf-8",
            )
            lease = CaptureLease.acquire(lock, {"test": "reclaim"})
            try:
                lease.assert_owned()
            finally:
                lease.release()
            self.assertFalse(lock.exists())

    def test_monitored_capture_accepts_monotonic_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = root / "movie.avi"
            lock = root / "capture.lock"
            lease = CaptureLease.acquire(lock, {"test": "monitor"})
            code = (
                "from pathlib import Path; import sys,time; "
                "p=Path(sys.argv[1]); p.write_bytes(b'a'*32); time.sleep(.05); "
                "f=p.open('ab'); f.write(b'b'*32); f.close(); time.sleep(.05)"
            )
            try:
                result = run_monitored_capture(
                    [sys.executable, "-c", code, str(raw)],
                    cwd=root,
                    env=os.environ.copy(),
                    raw_movie=raw,
                    lease=lease,
                    poll_seconds=0.01,
                )
            finally:
                lease.release()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(raw.stat().st_size, 64)


if __name__ == "__main__":
    unittest.main()
