#!/usr/bin/env python3
"""Record a source-safe Candidate 4 real-runtime proof walkthrough.

This tool is deliberately fail-closed. It only emits a final MP4 when the
current tracked source is clean, Candidate 4 preflight/freeze are PASS on the
same Git SHA, the captured graphical PPPV run evaluates PASS, and its semantic
replay/final-state fingerprints match the existing deterministic PPPV baseline.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import array
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import atexit
from types import SimpleNamespace

try:
    from tools.remaster_framework.capture_safety import (
        CaptureLease,
        CaptureSafetyError,
        assert_no_conflicting_movie_capture,
        audit_visual_stability,
        run_monitored_capture,
    )
except ModuleNotFoundError:
    from remaster_framework.capture_safety import (
        CaptureLease,
        CaptureSafetyError,
        assert_no_conflicting_movie_capture,
        audit_visual_stability,
        run_monitored_capture,
    )

ROOT = Path(__file__).resolve().parents[1]
KG_TMP = ROOT / ".tmp/kg001"
PPPV_TMP = ROOT / ".tmp/kg001_pppv_v2"
OUT_DIR = ROOT / ".tmp/kg001_proof_capture"

PREFLIGHT = KG_TMP / "candidate4_preflight_receipt.json"
FREEZE = KG_TMP / "candidate4_frozen_release_receipt.json"
PLAN = PPPV_TMP / "pppv_playthrough_plan.json"
SCENARIOS = PPPV_TMP / "pppv_scenarios.json"
BASELINE_EVAL = PPPV_TMP / "kg001_pppv_playthrough_evaluation.json"
DETERMINISM = PPPV_TMP / "kg001_pppv_determinism.json"
RUNTIME = OUT_DIR / "kg001_pppv_proof_runtime.json"
EVALUATION = OUT_DIR / "kg001_pppv_proof_evaluation.json"
RECEIPT = OUT_DIR / "kg001_proof_capture_receipt_v152.json"
DEFAULT_AVI = OUT_DIR / "OpenAzrael_KG001_Candidate4_Proof_raw.avi"
DEFAULT_MP4 = OUT_DIR / "OpenAzrael_KG001_Candidate4_Proof.mp4"
RAW_AUDIO_PCM = OUT_DIR / "OpenAzrael_KG001_Candidate4_Proof_raw_audio.s16le"
MP4_AUDIO_PCM = OUT_DIR / "OpenAzrael_KG001_Candidate4_Proof_mp4_audio.s16le"
SAFETY_LOCK = OUT_DIR / ".capture.lock"


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def git_value(*args: str) -> str:
    proc = run(["git", *args])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_clean() -> bool:
    proc = run(["git", "status", "--porcelain", "--untracked-files=normal"])
    return proc.returncode == 0 and proc.stdout.strip() == ""


def resolve_executable(value: str | None, fallbacks: list[str]) -> str | None:
    candidates: list[str] = []
    if value:
        candidates.append(value)
    candidates.extend(fallbacks)
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return str(path.resolve())
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def probe_media(ffprobe: str, path: Path) -> dict:
    proc = run([
        ffprobe, "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json", str(path),
    ])
    if proc.returncode != 0:
        return {"status": "FAIL", "output": proc.stdout[-12000:]}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "FAIL", "output": proc.stdout[-12000:]}
    if not isinstance(payload, dict):
        return {"status": "FAIL"}
    payload["status"] = "PASS"
    return payload


def decode_audio_pcm(ffmpeg: str, media: Path, out_pcm: Path) -> dict:
    out_pcm.unlink(missing_ok=True)
    proc = run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(media),
        "-map", "0:a:0", "-vn",
        "-ac", "2", "-ar", "48000",
        "-f", "s16le", str(out_pcm),
    ])
    if proc.returncode != 0 or not out_pcm.is_file() or out_pcm.stat().st_size < 4:
        return {
            "status": "FAIL",
            "returncode": proc.returncode,
            "output_tail": proc.stdout[-12000:],
        }
    samples = array.array("h")
    with out_pcm.open("rb") as handle:
        samples.fromfile(handle, out_pcm.stat().st_size // 2)
    if sys.byteorder != "little":
        samples.byteswap()
    max_abs = max((abs(int(v)) for v in samples), default=0)
    nonzero = sum(1 for v in samples if v != 0)
    duration_seconds = len(samples) / (48000.0 * 2.0)
    return {
        "status": "PASS" if max_abs > 0 and nonzero > 0 else "FAIL",
        "path": display_path(out_pcm),
        "sha256": sha256(out_pcm),
        "bytes": out_pcm.stat().st_size,
        "sample_rate_hz": 48000,
        "channels": 2,
        "sample_format": "s16le",
        "sample_count_interleaved": len(samples),
        "nonzero_sample_count": nonzero,
        "max_abs_sample": max_abs,
        "duration_seconds": duration_seconds,
        "digital_silence": max_abs == 0 or nonzero == 0,
    }


def audio_streams(probe: dict) -> list[dict]:
    rows = probe.get("streams", []) if isinstance(probe, dict) else []
    if not isinstance(rows, list):
        return []
    return [
        row for row in rows
        if isinstance(row, dict) and row.get("codec_type") == "audio"
    ]


def fail(reason: str, details: dict | None = None, *, final_video: Path | None = None) -> int:
    RECEIPT.unlink(missing_ok=True)
    if final_video is not None:
        final_video.unlink(missing_ok=True)
    payload = {
        "schema": "openazrael.kg001.proof_capture",
        "version": 152,
        "status": "FAIL",
        "reason": reason,
    }
    if details:
        payload["details"] = details
    print(json.dumps(payload, indent=2))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", help="ffmpeg executable; otherwise ffmpeg from PATH is used.")
    parser.add_argument("--ffprobe", help="ffprobe executable; otherwise sibling/PATH ffprobe is used.")
    parser.add_argument("--output", type=Path, default=DEFAULT_MP4, help="Final MP4 path.")
    parser.add_argument("--raw-avi", type=Path, default=DEFAULT_AVI, help="Godot Movie Maker AVI path.")
    parser.add_argument("--fps", type=int, default=30, help="Deterministic capture frame rate (24-60).")
    args = parser.parse_args()

    if not 24 <= args.fps <= 60:
        return fail("INVALID_FPS", {"fps": args.fps})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final_video = args.output.expanduser().resolve()
    raw_avi = args.raw_avi.expanduser().resolve()
    final_video.parent.mkdir(parents=True, exist_ok=True)
    raw_avi.parent.mkdir(parents=True, exist_ok=True)

    try:
        assert_no_conflicting_movie_capture(ROOT, exclude_pids={os.getpid()})
        capture_lease = CaptureLease.acquire(
            SAFETY_LOCK,
            {
                "purpose": "kg001-proof-capture-v152",
                "argv": sys.argv,
                "root": str(ROOT.resolve()),
            },
        )
        atexit.register(capture_lease.release)
    except CaptureSafetyError as exc:
        return fail(exc.code, exc.details, final_video=final_video)

    for stale in (
        RUNTIME, EVALUATION, RECEIPT, raw_avi, final_video,
        RAW_AUDIO_PCM, MP4_AUDIO_PCM,
    ):
        stale.unlink(missing_ok=True)

    if not git_clean():
        return fail("DIRTY_GIT_BEFORE_CAPTURE", final_video=final_video)

    head = git_value("rev-parse", "HEAD")
    tree = git_value("rev-parse", "HEAD^{tree}")
    if not head or not tree:
        return fail("GIT_IDENTITY_UNAVAILABLE", final_video=final_video)

    preflight = load_json(PREFLIGHT)
    if (
        preflight.get("status") != "PASS"
        or preflight.get("export_allowed") is not True
        or preflight.get("commit_sha") != head
    ):
        return fail(
            "CANDIDATE4_PREFLIGHT_NOT_PASS_FOR_CURRENT_HEAD",
            {"current_head": head, "preflight_head": preflight.get("commit_sha", "")},
            final_video=final_video,
        )

    # Revalidate the complete frozen source/runtime asset identity immediately
    # before recording. The freeze script is deterministic and writes only .tmp.
    freeze_check = run([sys.executable, "tools/freeze_candidate4_release.py"])
    if freeze_check.returncode != 0:
        return fail(
            "CANDIDATE4_FREEZE_REVALIDATION_FAILED",
            {"output_tail": freeze_check.stdout[-12000:]},
            final_video=final_video,
        )
    freeze = load_json(FREEZE)
    if (
        freeze.get("status") != "PASS"
        or freeze.get("commit_sha") != head
        or freeze.get("source_tree_sha") != tree
        or freeze.get("preflight_receipt", {}).get("sha256") != sha256(PREFLIGHT)
    ):
        return fail("CANDIDATE4_FREEZE_NOT_BOUND_TO_CURRENT_HEAD", freeze, final_video=final_video)

    missing = [
        display_path(path)
        for path in (PLAN, SCENARIOS, BASELINE_EVAL, DETERMINISM)
        if not path.is_file()
    ]
    if missing:
        return fail("PPPV_BASELINE_EVIDENCE_MISSING", {"missing": missing}, final_video=final_video)

    baseline = load_json(BASELINE_EVAL)
    determinism = load_json(DETERMINISM)
    if (
        baseline.get("status") != "PASS"
        or determinism.get("status") != "PASS"
        or int(determinism.get("repeat_count", 0)) < 2
    ):
        return fail(
            "PPPV_BASELINE_NOT_DETERMINISTIC_PASS",
            {
                "baseline_status": baseline.get("status", ""),
                "determinism_status": determinism.get("status", ""),
                "repeat_count": determinism.get("repeat_count", 0),
            },
            final_video=final_video,
        )

    godot = resolve_executable(
        str(preflight.get("godot_executable", "")) or None,
        [os.environ.get("GODOT_BIN", ""), "godot4", "godot"],
    )
    if not godot:
        return fail("GODOT_NOT_FOUND", final_video=final_video)

    ffmpeg = resolve_executable(args.ffmpeg, ["ffmpeg"])
    if not ffmpeg:
        return fail("FFMPEG_NOT_FOUND", final_video=final_video)
    ffprobe = resolve_executable(
        None,
        [str(Path(ffmpeg).with_name("ffprobe")), "ffprobe"],
    )
    if not ffprobe:
        return fail("FFPROBE_NOT_FOUND", final_video=final_video)
    ffmpeg_path = Path(ffmpeg)
    sibling_ffprobe = ffmpeg_path.with_name(
        "ffprobe.exe" if ffmpeg_path.name.lower().endswith(".exe") else "ffprobe"
    )
    ffprobe = resolve_executable(
        args.ffprobe,
        [str(sibling_ffprobe), "ffprobe"],
    )
    if not ffprobe:
        return fail("FFPROBE_NOT_FOUND", final_video=final_video)

    proof_env = os.environ.copy()
    proof_env["OPENAZRAEL_PROOF_GIT_SHA"] = head
    proof_env["OPENAZRAEL_PROOF_FREEZE_SHA"] = sha256(FREEZE)
    proof_env["OPENAZRAEL_PROOF_CANDIDATE"] = "KG-001 Candidate 4"

    movie_cmd = [
        godot,
        "--path", str(ROOT),
        "--write-movie", str(raw_avi),
        "--fixed-fps", str(args.fps),
        "--script", "res://scripts/validation/pppv_playthrough_runner.gd",
        "--",
        f"--pppv-plan={PLAN}",
        f"--pppv-scenarios={SCENARIOS}",
        f"--pppv-output={RUNTIME}",
        "--pppv-proof-overlay=1",
    ]
    try:
        capture_monitor = run_monitored_capture(
            movie_cmd,
            cwd=ROOT,
            env=proof_env,
            raw_movie=raw_avi,
            lease=capture_lease,
        )
        movie = SimpleNamespace(
            returncode=0,
            stdout=str(capture_monitor.get("output_tail", "")),
        )
    except CaptureSafetyError as exc:
        return fail(exc.code, exc.details, final_video=final_video)
    if (
        movie.returncode != 0
        or not raw_avi.is_file()
        or raw_avi.stat().st_size <= 0
        or not RUNTIME.is_file()
    ):
        return fail(
            "GODOT_PROOF_CAPTURE_FAILED",
            {
                "returncode": movie.returncode,
                "raw_movie_exists": raw_avi.is_file(),
                "runtime_exists": RUNTIME.is_file(),
                "output_tail": movie.stdout[-16000:],
            },
            final_video=final_video,
        )

    raw_probe_proc = run([
        ffprobe,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(raw_avi),
    ])
    try:
        raw_probe = json.loads(raw_probe_proc.stdout)
    except (json.JSONDecodeError, TypeError):
        raw_probe = {}
    raw_streams = raw_probe.get("streams", []) if isinstance(raw_probe, dict) else []
    raw_audio_streams = [
        row for row in raw_streams
        if isinstance(row, dict) and row.get("codec_type") == "audio"
    ]
    if raw_probe_proc.returncode != 0 or not raw_audio_streams:
        return fail(
            "RAW_MOVIE_AUDIO_STREAM_MISSING",
            {
                "returncode": raw_probe_proc.returncode,
                "probe": raw_probe,
                "output_tail": raw_probe_proc.stdout[-12000:],
            },
            final_video=final_video,
        )

    volume_proc = run([
        ffmpeg,
        "-hide_banner", "-nostats",
        "-i", str(raw_avi),
        "-map", "0:a:0",
        "-af", "volumedetect",
        "-f", "null", "-",
    ])
    max_volume_match = re.search(
        r"max_volume:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB",
        volume_proc.stdout,
        re.IGNORECASE,
    )
    max_volume_text = max_volume_match.group(1) if max_volume_match else ""
    if (
        volume_proc.returncode != 0
        or not max_volume_text
        or max_volume_text.lower() in {"-inf", "inf"}
    ):
        return fail(
            "RAW_MOVIE_AUDIO_SILENT_OR_UNVERIFIED",
            {
                "returncode": volume_proc.returncode,
                "max_volume_db": max_volume_text,
                "output_tail": volume_proc.stdout[-12000:],
            },
            final_video=final_video,
        )
    max_volume_db = float(max_volume_text)
    if max_volume_db <= -96.0:
        return fail(
            "RAW_MOVIE_AUDIO_EFFECTIVELY_SILENT",
            {"max_volume_db": max_volume_db},
            final_video=final_video,
        )

    raw_probe = probe_media(ffprobe, raw_avi)
    raw_audio_streams = audio_streams(raw_probe)
    if raw_probe.get("status") != "PASS" or not raw_audio_streams:
        return fail(
            "RAW_PROOF_CAPTURE_AUDIO_STREAM_MISSING",
            {"probe": raw_probe},
            final_video=final_video,
        )
    raw_audio = decode_audio_pcm(ffmpeg, raw_avi, RAW_AUDIO_PCM)
    if raw_audio.get("status") != "PASS":
        return fail(
            "RAW_PROOF_CAPTURE_AUDIO_SILENT_OR_UNDECODABLE",
            raw_audio,
            final_video=final_video,
        )

    evaluator = run([
        sys.executable,
        "-m", "tools.remaster_framework.evaluate_playthrough",
        "--runtime-bundle", str(RUNTIME),
        "--output", str(EVALUATION),
    ])
    captured = load_json(EVALUATION)
    if evaluator.returncode != 0 or captured.get("status") != "PASS":
        return fail(
            "CAPTURED_PPPV_EVALUATION_FAILED",
            {
                "returncode": evaluator.returncode,
                "evaluation": captured,
                "output_tail": evaluator.stdout[-12000:],
            },
            final_video=final_video,
        )

    replay = str(captured.get("semantic_replay_sha256", ""))
    final_state = str(captured.get("final_state_sha256", ""))
    baseline_replay = str(baseline.get("semantic_replay_sha256", ""))
    baseline_final = str(baseline.get("final_state_sha256", ""))
    deterministic_replays = [str(v) for v in determinism.get("semantic_replay_sha256", [])]
    deterministic_finals = [str(v) for v in determinism.get("final_state_sha256", [])]
    identity_match = (
        replay
        and final_state
        and replay == baseline_replay
        and final_state == baseline_final
        and all(v == replay for v in deterministic_replays)
        and all(v == final_state for v in deterministic_finals)
    )
    if not identity_match:
        return fail(
            "CAPTURED_RUN_DIFFERS_FROM_DETERMINISTIC_BASELINE",
            {
                "captured_replay": replay,
                "baseline_replay": baseline_replay,
                "determinism_replays": deterministic_replays,
                "captured_final_state": final_state,
                "baseline_final_state": baseline_final,
                "determinism_final_states": deterministic_finals,
            },
            final_video=final_video,
        )

    ffmpeg_cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(raw_avi),
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(final_video),
    ]
    transcode = run(ffmpeg_cmd)
    if transcode.returncode != 0 or not final_video.is_file() or final_video.stat().st_size <= 0:
        return fail(
            "FFMPEG_TRANSCODE_FAILED",
            {
                "returncode": transcode.returncode,
                "output_tail": transcode.stdout[-12000:],
            },
            final_video=final_video,
        )

    final_probe_proc = run([
        ffprobe,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(final_video),
    ])
    try:
        final_probe = json.loads(final_probe_proc.stdout)
    except (json.JSONDecodeError, TypeError):
        final_probe = {}
    final_streams = final_probe.get("streams", []) if isinstance(final_probe, dict) else []
    final_audio_streams = [
        row for row in final_streams
        if isinstance(row, dict) and row.get("codec_type") == "audio"
    ]
    if final_probe_proc.returncode != 0 or not final_audio_streams:
        return fail(
            "FINAL_MP4_AUDIO_STREAM_MISSING",
            {
                "returncode": final_probe_proc.returncode,
                "probe": final_probe,
                "output_tail": final_probe_proc.stdout[-12000:],
            },
            final_video=final_video,
        )

    mp4_probe = probe_media(ffprobe, final_video)
    mp4_audio_streams = audio_streams(mp4_probe)
    if mp4_probe.get("status") != "PASS" or not mp4_audio_streams:
        return fail(
            "FINAL_MP4_AUDIO_STREAM_MISSING",
            {"probe": mp4_probe},
            final_video=final_video,
        )
    mp4_audio = decode_audio_pcm(ffmpeg, final_video, MP4_AUDIO_PCM)
    if mp4_audio.get("status") != "PASS":
        return fail(
            "FINAL_MP4_AUDIO_SILENT_OR_UNDECODABLE",
            mp4_audio,
            final_video=final_video,
        )

    try:
        visual_qa = audit_visual_stability(
            ffmpeg,
            final_video,
            fps=float(args.fps),
            p99_frame_mad_max=28.0,
            p99_luma_jump_max=14.0,
            isolated_flash_score_max=45.0,
        )
    except CaptureSafetyError as exc:
        return fail(exc.code, exc.details, final_video=final_video)
    if visual_qa.get("status") != "PASS":
        return fail(
            "VISUAL_STABILITY_GATE_FAILED",
            visual_qa,
            final_video=final_video,
        )

    godot_ver = run([godot, "--version"])
    ffmpeg_ver = run([ffmpeg, "-version"])
    ffmpeg_first = ffmpeg_ver.stdout.splitlines()[0] if ffmpeg_ver.stdout else ""

    receipt = {
        "schema": "openazrael.kg001.proof_capture",
        "version": 152,
        "status": "PASS",
        "candidate": "KG-001 Candidate 4",
        "commit_sha": head,
        "source_tree_sha": tree,
        "preflight_receipt": {
            "path": display_path(PREFLIGHT),
            "sha256": sha256(PREFLIGHT),
        },
        "frozen_release_receipt": {
            "path": display_path(FREEZE),
            "sha256": sha256(FREEZE),
        },
        "pppv_baseline": {
            "plan_sha256": sha256(PLAN),
            "scenario_bundle_sha256": sha256(SCENARIOS),
            "determinism_sha256": sha256(DETERMINISM),
            "semantic_replay_sha256": replay,
            "final_state_sha256": final_state,
            "repeat_count_before_capture": determinism.get("repeat_count", 0),
            "captured_run_matches_baseline": True,
        },
        "captured_run": {
            "runtime_path": display_path(RUNTIME),
            "runtime_sha256": sha256(RUNTIME),
            "evaluation_path": display_path(EVALUATION),
            "evaluation_sha256": sha256(EVALUATION),
            "status": "PASS",
        },
        "video": {
            "path": display_path(final_video),
            "sha256": sha256(final_video),
            "bytes": final_video.stat().st_size,
            "container": "mp4",
            "video_codec": "h264/libx264",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_required": True,
            "audio_stream": {
                "codec_name": final_audio_streams[0].get("codec_name", ""),
                "sample_rate": final_audio_streams[0].get("sample_rate", ""),
                "channels": final_audio_streams[0].get("channels", 0),
                "channel_layout": final_audio_streams[0].get("channel_layout", ""),
            },
            "fps": args.fps,
            "viewport": [1280, 720],
            "camera": "production_player_camera",
            "overlay": "git_sha+freeze_sha+room+pppv_step+status",
        },
        "audio_evidence": {
            "required": True,
            "raw_capture_stream_count": len(raw_audio_streams),
            "raw_capture_primary_stream": raw_audio_streams[0],
            "raw_capture_pcm": raw_audio,
            "final_mp4_stream_count": len(mp4_audio_streams),
            "final_mp4_primary_stream": mp4_audio_streams[0],
            "final_mp4_pcm": mp4_audio,
            "digital_silence_forbidden": True,
            "source": "Godot Movie Maker runtime mix",
        },
        "raw_movie": {
            "path": display_path(raw_avi),
            "sha256": sha256(raw_avi),
            "bytes": raw_avi.stat().st_size,
            "writer": "Godot Movie Maker AVI",
            "audio_required": True,
            "audio_stream": {
                "codec_name": raw_audio_streams[0].get("codec_name", ""),
                "sample_rate": raw_audio_streams[0].get("sample_rate", ""),
                "channels": raw_audio_streams[0].get("channels", 0),
                "channel_layout": raw_audio_streams[0].get("channel_layout", ""),
                "max_volume_db": max_volume_db,
                "non_silent_signal_verified": True,
            },
        },
        "capture_safety": {
            "single_writer_lock": True,
            "duplicate_movie_maker_forbidden": True,
            "output_inode_monitored": True,
            "output_size_monotonic_required": True,
            "movie_monitor": capture_monitor,
            "visual_stability": visual_qa,
        },
        "toolchain": {
            "godot": godot_ver.stdout.strip(),
            "ffmpeg": ffmpeg_first,
            "ffprobe": run([ffprobe, "-version"]).stdout.splitlines()[0],
        },
        "evidence_boundary": (
            "Supplemental exact-source runtime evidence only. It proves that this "
            "captured graphical PPPV run reached the same accepted replay/final "
            "state as the deterministic baseline. It does not replace packaged "
            "EXE/PCK parity or manual G10."
        ),
        "ai_generated_visuals": False,
        "noclip_or_fly_camera": False,
        "direct_gameplay_state_injection": False,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    if not git_clean():
        return fail(
            "TRACKED_SOURCE_CHANGED_DURING_CAPTURE",
            final_video=final_video,
        )

    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
