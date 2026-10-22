from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import subprocess
import time
import uuid


class CaptureSafetyError(RuntimeError):
    def __init__(self, code: str, details: dict | None = None):
        super().__init__(code)
        self.code = code
        self.details = details or {}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _process_cmdlines() -> list[tuple[int, str]]:
    proc = Path("/proc")
    rows: list[tuple[int, str]] = []
    if not proc.is_dir():
        return rows
    for child in proc.iterdir():
        if not child.name.isdigit():
            continue
        try:
            raw = (child / "cmdline").read_bytes()
        except OSError:
            continue
        if raw:
            rows.append((
                int(child.name),
                raw.replace(b"\0", b" ").decode("utf-8", "replace"),
            ))
    return rows


def find_conflicting_movie_captures(
    root: Path,
    *,
    exclude_pids: set[int] | None = None,
) -> list[dict]:
    exclude = set(exclude_pids or set())
    root_text = str(root.resolve())
    hits: list[dict] = []
    for pid, cmdline in _process_cmdlines():
        if pid in exclude or "--write-movie" not in cmdline:
            continue
        if root_text not in cmdline and "pppv_playthrough_runner.gd" not in cmdline:
            continue
        hits.append({"pid": pid, "cmdline": cmdline[:2000]})
    return hits


def assert_no_conflicting_movie_capture(
    root: Path,
    *,
    exclude_pids: set[int] | None = None,
) -> None:
    hits = find_conflicting_movie_captures(root, exclude_pids=exclude_pids)
    if hits:
        raise CaptureSafetyError(
            "DUPLICATE_MOVIE_CAPTURE_DETECTED",
            {"processes": hits},
        )


@dataclass
class CaptureLease:
    path: Path
    pid: int
    nonce: str
    identity: dict

    @classmethod
    def acquire(cls, path: Path, identity: dict) -> "CaptureLease":
        path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            nonce = uuid.uuid4().hex
            payload = {"pid": os.getpid(), "nonce": nonce, "identity": identity}
            try:
                fd = os.open(
                    str(path),
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o644,
                )
            except FileExistsError:
                try:
                    current = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    current = {}
                owner_pid = int(current.get("pid", 0) or 0)
                if owner_pid and _pid_alive(owner_pid):
                    raise CaptureSafetyError(
                        "CAPTURE_LOCK_HELD",
                        {"lock": str(path), "owner": current},
                    )
                path.unlink(missing_ok=True)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True)
                handle.write("\n")
            return cls(path=path, pid=os.getpid(), nonce=nonce, identity=identity)
        raise CaptureSafetyError(
            "CAPTURE_LOCK_ACQUIRE_FAILED",
            {"lock": str(path)},
        )

    def assert_owned(self) -> None:
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CaptureSafetyError(
                "CAPTURE_LOCK_LOST",
                {"lock": str(self.path), "error": str(exc)},
            )
        if current.get("pid") != self.pid or current.get("nonce") != self.nonce:
            raise CaptureSafetyError(
                "CAPTURE_LOCK_STOLEN",
                {"lock": str(self.path), "owner": current},
            )

    def release(self) -> None:
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
        if current.get("pid") == self.pid and current.get("nonce") == self.nonce:
            self.path.unlink(missing_ok=True)


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_monitored_capture(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None,
    raw_movie: Path,
    lease: CaptureLease,
    poll_seconds: float = 0.25,
) -> dict:
    raw_movie.parent.mkdir(parents=True, exist_ok=True)
    log_path = raw_movie.with_suffix(raw_movie.suffix + ".capture.log")
    inode: tuple[int, int] | None = None
    last_size = -1
    max_size = 0
    seen = False

    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            while proc.poll() is None:
                lease.assert_owned()
                conflicts = find_conflicting_movie_captures(
                    cwd,
                    exclude_pids={os.getpid(), proc.pid},
                )
                if conflicts:
                    raise CaptureSafetyError(
                        "DUPLICATE_MOVIE_CAPTURE_DURING_RUN",
                        {"processes": conflicts},
                    )

                if raw_movie.exists():
                    st = raw_movie.stat()
                    current_inode = (int(st.st_dev), int(st.st_ino))
                    if inode is None:
                        inode = current_inode
                        seen = True
                    elif current_inode != inode:
                        raise CaptureSafetyError(
                            "CAPTURE_OUTPUT_REPLACED_DURING_RUN",
                            {
                                "expected_dev_inode": inode,
                                "actual_dev_inode": current_inode,
                            },
                        )
                    size = int(st.st_size)
                    if size < last_size:
                        raise CaptureSafetyError(
                            "CAPTURE_OUTPUT_SIZE_REGRESSED",
                            {
                                "previous_bytes": last_size,
                                "current_bytes": size,
                            },
                        )
                    last_size = size
                    max_size = max(max_size, size)
                elif seen:
                    raise CaptureSafetyError(
                        "CAPTURE_OUTPUT_UNLINKED_DURING_RUN",
                        {"path": str(raw_movie)},
                    )
                time.sleep(poll_seconds)
        except BaseException:
            _terminate(proc)
            raise
        returncode = proc.wait()

    try:
        tail = log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )[-16000:]
    except OSError:
        tail = ""

    if returncode != 0:
        raise CaptureSafetyError(
            "MOVIE_CAPTURE_PROCESS_FAILED",
            {"returncode": returncode, "output_tail": tail},
        )
    if not raw_movie.is_file() or raw_movie.stat().st_size <= 0:
        raise CaptureSafetyError(
            "MOVIE_CAPTURE_OUTPUT_MISSING",
            {"path": str(raw_movie)},
        )

    st = raw_movie.stat()
    if inode is not None and (int(st.st_dev), int(st.st_ino)) != inode:
        raise CaptureSafetyError(
            "CAPTURE_OUTPUT_REPLACED_AFTER_RUN",
            {"path": str(raw_movie)},
        )

    return {
        "status": "PASS",
        "pid": proc.pid,
        "raw_movie": str(raw_movie),
        "dev_inode": list(inode) if inode else None,
        "bytes": int(st.st_size),
        "max_observed_bytes": max_size,
        "log_path": str(log_path),
        "output_tail": tail,
    }


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    rows = sorted(values)
    pos = (len(rows) - 1) * min(1.0, max(0.0, q))
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(rows[lo])
    frac = pos - lo
    return float(rows[lo] * (1.0 - frac) + rows[hi] * frac)


def audit_visual_stability(
    ffmpeg: str,
    media: Path,
    *,
    fps: float,
    width: int = 160,
    height: int = 90,
    p99_frame_mad_max: float = 28.0,
    p99_luma_jump_max: float = 14.0,
    isolated_flash_score_max: float = 45.0,
) -> dict:
    frame_bytes = width * height
    proc = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner", "-loglevel", "error",
            "-i", str(media),
            "-an",
            "-vf", f"scale={width}:{height}:flags=area,format=gray",
            "-pix_fmt", "gray",
            "-f", "rawvideo",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None

    frames: list[bytes] = []
    while True:
        chunk = proc.stdout.read(frame_bytes)
        if not chunk:
            break
        if len(chunk) != frame_bytes:
            proc.kill()
            raise CaptureSafetyError(
                "VISUAL_AUDIT_TRUNCATED_FRAME",
                {"bytes": len(chunk), "expected": frame_bytes},
            )
        frames.append(chunk)

    stderr = (
        proc.stderr.read().decode("utf-8", "replace")
        if proc.stderr is not None
        else ""
    )
    returncode = proc.wait()
    if returncode != 0 or len(frames) < 3:
        raise CaptureSafetyError(
            "VISUAL_AUDIT_DECODE_FAILED",
            {
                "returncode": returncode,
                "frames": len(frames),
                "stderr": stderr[-12000:],
            },
        )

    means = [sum(frame) / frame_bytes for frame in frames]
    diffs = [
        sum(abs(x - y) for x, y in zip(a, b)) / frame_bytes
        for a, b in zip(frames, frames[1:])
    ]
    luma_jumps = [
        abs(a - b)
        for a, b in zip(means, means[1:])
    ]

    flash_scores: list[float] = []
    for idx in range(1, len(frames) - 1):
        prev_f = frames[idx - 1]
        cur_f = frames[idx]
        next_f = frames[idx + 1]
        prev_cur = sum(
            abs(x - y) for x, y in zip(prev_f, cur_f)
        ) / frame_bytes
        cur_next = sum(
            abs(x - y) for x, y in zip(cur_f, next_f)
        ) / frame_bytes
        prev_next = sum(
            abs(x - y) for x, y in zip(prev_f, next_f)
        ) / frame_bytes
        flash_scores.append(max(0.0, prev_cur + cur_next - prev_next))

    p99_mad = _quantile(diffs, 0.99)
    p99_luma = _quantile(luma_jumps, 0.99)
    max_flash = max(flash_scores, default=0.0)
    hotspots = sorted(
        (
            {
                "frame": idx + 1,
                "seconds": (idx + 1) / fps,
                "frame_mad": value,
            }
            for idx, value in enumerate(diffs)
        ),
        key=lambda row: row["frame_mad"],
        reverse=True,
    )[:12]

    failures: list[str] = []
    if p99_mad > p99_frame_mad_max:
        failures.append("P99_FRAME_MAD")
    if p99_luma > p99_luma_jump_max:
        failures.append("P99_LUMA_JUMP")
    if max_flash > isolated_flash_score_max:
        failures.append("ISOLATED_FLASH_SCORE")

    return {
        "status": "PASS" if not failures else "FAIL",
        "frame_count": len(frames),
        "fps": fps,
        "analysis_resolution": [width, height],
        "p99_frame_mad": p99_mad,
        "p99_luma_jump": p99_luma,
        "max_isolated_flash_score": max_flash,
        "thresholds": {
            "p99_frame_mad_max": p99_frame_mad_max,
            "p99_luma_jump_max": p99_luma_jump_max,
            "isolated_flash_score_max": isolated_flash_score_max,
        },
        "failures": failures,
        "hotspots": hotspots,
    }
