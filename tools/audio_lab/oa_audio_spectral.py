#!/usr/bin/env python3
"""Source-safe spectral analysis and spectrogram review for OpenAzrael Audio Lab."""
from __future__ import annotations

from pathlib import Path
import argparse
import binascii
import html
import json
import math
import struct
import sys
import zlib

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from tools.audio_lab.common import (
    ensure_output_outside_source,
    iter_audio_files,
    parse_wave,
    tree_digest,
)

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_FFT_SIZE = 512
DEFAULT_HOP_SIZE = 128
DEFAULT_DB_FLOOR = -80.0
DEFAULT_TIME_BINS = 256
DEFAULT_FREQ_BINS = 128

def _read_wave_pcm(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE container")
    fmt = None
    pcm = None
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset:offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        start = offset + 8
        end = start + chunk_size
        if end > len(data):
            raise ValueError("chunk payload exceeds file length")
        payload = data[start:end]
        if chunk_id == b"fmt " and len(payload) >= 16 and fmt is None:
            audio_format, channels, sample_rate, byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", payload, 0)
            fmt = {
                "audio_format": audio_format,
                "channels": channels,
                "sample_rate": sample_rate,
                "byte_rate": byte_rate,
                "block_align": block_align,
                "sample_width_bits": bits,
            }
        elif chunk_id == b"data" and pcm is None:
            pcm = payload
        next_offset = end + (chunk_size & 1)
        if next_offset > len(data) and end == len(data) and (chunk_size & 1):
            next_offset = end
        if next_offset <= offset:
            raise ValueError("invalid RIFF chunk progression")
        offset = next_offset
    if fmt is None or pcm is None:
        raise ValueError("missing fmt or data chunk")
    return fmt, pcm

def decode_wave_mono(path: Path) -> tuple[np.ndarray, int, dict]:
    parsed = parse_wave(path)
    if not parsed.get("valid"):
        raise ValueError(str(parsed.get("parse_error") or "invalid WAV"))
    fmt, pcm = _read_wave_pcm(path)
    if fmt["audio_format"] != 1:
        raise ValueError(f"unsupported WAV format code {fmt['audio_format']}")
    channels = int(fmt["channels"])
    bits = int(fmt["sample_width_bits"])
    if channels <= 0:
        raise ValueError("invalid channel count")

    if bits == 8:
        samples = (np.frombuffer(pcm, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif bits == 16:
        usable = len(pcm) - len(pcm) % 2
        samples = np.frombuffer(pcm[:usable], dtype="<i2").astype(np.float64) / 32768.0
    elif bits == 24:
        usable = len(pcm) - len(pcm) % 3
        raw = np.frombuffer(pcm[:usable], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        vals = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        vals = np.where(vals & 0x800000, vals - (1 << 24), vals)
        samples = vals.astype(np.float64) / 8388608.0
    elif bits == 32:
        usable = len(pcm) - len(pcm) % 4
        samples = np.frombuffer(pcm[:usable], dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"unsupported PCM bit depth {bits}")

    complete = len(samples) - (len(samples) % channels)
    samples = samples[:complete]
    if samples.size == 0:
        mono = np.zeros(0, dtype=np.float64)
    elif channels == 1:
        mono = samples
    else:
        mono = samples.reshape(-1, channels).mean(axis=1)
    return mono, int(fmt["sample_rate"]), parsed

def _validate_fft(fft_size: int, hop_size: int) -> None:
    if fft_size < 32:
        raise ValueError("fft_size must be >= 32")
    if fft_size & (fft_size - 1):
        raise ValueError("fft_size must be a power of two")
    if hop_size <= 0 or hop_size > fft_size:
        raise ValueError("hop_size must be > 0 and <= fft_size")

def stft_power(samples: np.ndarray, sample_rate: int, fft_size: int, hop_size: int) -> tuple[np.ndarray, np.ndarray]:
    _validate_fft(fft_size, hop_size)
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0:
        x = np.zeros(fft_size, dtype=np.float64)
    if x.size <= fft_size:
        frame_count = 1
    else:
        frame_count = 1 + int(math.ceil((x.size - fft_size) / hop_size))
    target_len = (frame_count - 1) * hop_size + fft_size
    if x.size < target_len:
        x = np.pad(x, (0, target_len - x.size))
    starts = np.arange(frame_count)[:, None] * hop_size
    offsets = np.arange(fft_size)[None, :]
    frames = x[starts + offsets]
    window = np.hanning(fft_size)
    spectrum = np.fft.rfft(frames * window, n=fft_size, axis=1)
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    return power, freqs

def spectral_metrics(samples: np.ndarray, sample_rate: int, power: np.ndarray, freqs: np.ndarray) -> dict:
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0:
        x = np.zeros(1, dtype=np.float64)
    avg = np.mean(power, axis=0)
    total = float(np.sum(avg))
    eps = np.finfo(np.float64).tiny

    if total <= eps:
        dominant = centroid = bandwidth = rolloff = 0.0
    else:
        search = avg.copy()
        if search.size > 1:
            search[0] = 0.0
        dominant = float(freqs[int(np.argmax(search))]) if float(np.max(search)) > eps else 0.0
        centroid = float(np.sum(freqs * avg) / total)
        bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * avg) / total))
        threshold = 0.85 * total
        idx = int(np.searchsorted(np.cumsum(avg), threshold, side="left"))
        idx = min(idx, len(freqs) - 1)
        rolloff = float(freqs[idx])

    mean_power = float(np.mean(avg))
    flatness = float(np.exp(np.mean(np.log(avg + eps))) / (mean_power + eps)) if avg.size else 0.0
    rms = float(np.sqrt(np.mean(x * x)))
    peak = float(np.max(np.abs(x)))
    crest = float(peak / rms) if rms > eps else 0.0
    dc = float(np.mean(x))
    if x.size < 2:
        zcr = 0.0
    else:
        signs = x >= 0.0
        zcr = float(np.mean(signs[1:] != signs[:-1]))

    nyquist = sample_rate / 2.0
    high_mask = freqs >= nyquist * 0.75
    high_ratio = float(np.sum(avg[high_mask]) / total) if total > eps and np.any(high_mask) else 0.0

    return {
        "dominant_frequency_hz": dominant,
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "spectral_rolloff_85_hz": rolloff,
        "spectral_flatness": flatness,
        "high_frequency_energy_ratio": high_ratio,
        "dc_offset": dc,
        "rms": rms,
        "peak": peak,
        "crest_factor": crest,
        "zero_crossing_rate": zcr,
    }

def _max_pool_2d(matrix: np.ndarray, target_rows: int, target_cols: int) -> np.ndarray:
    rows, cols = matrix.shape
    if rows <= 0 or cols <= 0 or target_rows <= 0 or target_cols <= 0:
        raise ValueError("pooling dimensions must be positive")
    out = np.empty((target_rows, target_cols), dtype=np.float64)
    for r in range(target_rows):
        r0 = min(rows - 1, (r * rows) // target_rows)
        r1 = min(rows, max(r0 + 1, ((r + 1) * rows + target_rows - 1) // target_rows))
        for c in range(target_cols):
            c0 = min(cols - 1, (c * cols) // target_cols)
            c1 = min(cols, max(c0 + 1, ((c + 1) * cols + target_cols - 1) // target_cols))
            out[r, c] = float(np.max(matrix[r0:r1, c0:c1]))
    return out

def spectrogram_preview(power: np.ndarray, db_floor: float, time_bins: int, freq_bins: int) -> np.ndarray:
    if db_floor >= 0:
        raise ValueError("db_floor must be negative")
    peak = float(np.max(power))
    if peak <= 0:
        db = np.full(power.shape, db_floor, dtype=np.float64)
    else:
        db = 10.0 * np.log10(np.maximum(power / peak, 1e-12))
        db = np.clip(db, db_floor, 0.0)
    # STFT is [time, frequency]; image is [frequency, time].
    pooled = _max_pool_2d(db.T, freq_bins, time_bins)
    normalized = np.clip((pooled - db_floor) / (-db_floor), 0.0, 1.0)
    image = np.rint(normalized * 255.0).astype(np.uint8)
    return np.flipud(image)

def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(kind)
    crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

def write_grayscale_png(path: Path, image: np.ndarray) -> None:
    img = np.asarray(image, dtype=np.uint8)
    if img.ndim != 2 or img.shape[0] <= 0 or img.shape[1] <= 0:
        raise ValueError("PNG image must be a non-empty 2D array")
    height, width = img.shape
    raw = b"".join(b"\x00" + img[row].tobytes() for row in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)

def analyze_file(
    path: Path,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int = DEFAULT_HOP_SIZE,
    db_floor: float = DEFAULT_DB_FLOOR,
    time_bins: int = DEFAULT_TIME_BINS,
    freq_bins: int = DEFAULT_FREQ_BINS,
) -> tuple[dict, np.ndarray]:
    samples, sample_rate, parsed = decode_wave_mono(path)
    power, freqs = stft_power(samples, sample_rate, fft_size, hop_size)
    metrics = spectral_metrics(samples, sample_rate, power, freqs)
    preview = spectrogram_preview(power, db_floor, time_bins, freq_bins)
    record = {
        "filename": path.name,
        "sample_rate": sample_rate,
        "channels": parsed.get("channels"),
        "sample_width_bits": parsed.get("sample_width_bits"),
        "frames": parsed.get("frames"),
        "duration_seconds": parsed.get("duration_seconds"),
        "analysis_frames": int(power.shape[0]),
        "fft_bins": int(power.shape[1]),
        **{k: round(float(v), 9) for k, v in metrics.items()},
    }
    return record, preview

def _all_metrics_finite(record: dict) -> bool:
    metric_keys = (
        "dominant_frequency_hz",
        "spectral_centroid_hz",
        "spectral_bandwidth_hz",
        "spectral_rolloff_85_hz",
        "spectral_flatness",
        "high_frequency_energy_ratio",
        "dc_offset",
        "rms",
        "peak",
        "crest_factor",
        "zero_crossing_rate",
    )
    return all(math.isfinite(float(record[k])) for k in metric_keys)

def write_review_html(path: Path, manifest: dict, source_root: Path) -> None:
    rows = []
    for rec in manifest.get("assets", []):
        image = html.escape(str(rec["spectrogram"]), quote=True)
        audio = html.escape((source_root / rec["path"]).resolve().as_uri(), quote=True)
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(rec['filename'])}</strong></td>"
            f"<td>{rec['sample_rate']} Hz<br>{rec['duration_seconds']} s</td>"
            f"<td><img src='{image}' width='256' height='128' loading='lazy'></td>"
            f"<td>{rec['dominant_frequency_hz']:.1f} Hz</td>"
            f"<td>{rec['spectral_centroid_hz']:.1f} Hz</td>"
            f"<td>{rec['spectral_rolloff_85_hz']:.1f} Hz</td>"
            f"<td>{rec['spectral_flatness']:.6f}</td>"
            f"<td><audio controls preload='none' src='{audio}'></audio></td>"
            "</tr>"
        )
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>OpenAzrael Audio Lab AL-POC-02 Spectral Review</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;line-height:1.35}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbb;padding:8px;vertical-align:top}} th{{text-align:left}}
img{{image-rendering:auto;max-width:256px}} audio{{width:220px}}
</style></head><body>
<h1>OpenAzrael Audio Lab — AL-POC-02 Spectral Review</h1>
<p>Status: <strong>{html.escape(str(manifest.get('status')))}</strong> · Assets: {len(manifest.get('assets', []))}</p>
<table><thead><tr><th>Asset</th><th>Source</th><th>Spectrogram</th><th>Dominant</th><th>Centroid</th><th>Rolloff 85%</th><th>Flatness</th><th>Preview</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>"""
    path.write_text(doc, encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_root", type=Path)
    ap.add_argument("--output-dir", type=Path, default=ROOT / ".tmp/audio_lab/al_poc_02")
    ap.add_argument("--fft-size", type=int, default=DEFAULT_FFT_SIZE)
    ap.add_argument("--hop-size", type=int, default=DEFAULT_HOP_SIZE)
    ap.add_argument("--db-floor", type=float, default=DEFAULT_DB_FLOOR)
    ap.add_argument("--time-bins", type=int, default=DEFAULT_TIME_BINS)
    ap.add_argument("--freq-bins", type=int, default=DEFAULT_FREQ_BINS)
    args = ap.parse_args(argv)

    source = args.source_root.resolve()
    if not source.is_dir():
        ap.error(f"source_root is not a directory: {source}")
    try:
        out = ensure_output_outside_source(source, args.output_dir)
    except ValueError as exc:
        ap.error(str(exc))
    _validate_fft(args.fft_size, args.hop_size)
    if args.time_bins <= 0 or args.freq_bins <= 0:
        ap.error("preview bin counts must be positive")

    files = iter_audio_files(source, {".wav", ".wave"})
    digest_before = tree_digest(source, files)
    spec_dir = out / "spectrograms"
    spec_dir.mkdir(parents=True, exist_ok=True)

    records = []
    errors = []
    for path in files:
        rel = path.relative_to(source).as_posix()
        try:
            rec, preview = analyze_file(
                path,
                fft_size=args.fft_size,
                hop_size=args.hop_size,
                db_floor=args.db_floor,
                time_bins=args.time_bins,
                freq_bins=args.freq_bins,
            )
            safe_name = path.stem + ".png"
            png_path = spec_dir / safe_name
            write_grayscale_png(png_path, preview)
            rec["path"] = rel
            rec["spectrogram"] = f"spectrograms/{safe_name}"
            rec["metrics_finite"] = _all_metrics_finite(rec)
            if not rec["metrics_finite"]:
                errors.append({"path": rel, "code": "SPEC_NONFINITE_METRIC"})
            records.append(rec)
        except Exception as exc:
            errors.append({"path": rel, "code": "SPEC_ANALYSIS_FAILED", "detail": str(exc)})

    digest_after = tree_digest(source, iter_audio_files(source, {".wav", ".wave"}))
    source_unchanged = digest_before == digest_after
    if not source_unchanged:
        errors.append({"path": ".", "code": "SPEC_SOURCE_MUTATED"})

    manifest = {
        "schema": "openazrael.audio_lab.spectral_manifest",
        "version": 1,
        "milestone": "AL-POC-02",
        "status": "PASS" if not errors else "FAIL",
        "parameters": {
            "fft_size": args.fft_size,
            "hop_size": args.hop_size,
            "db_floor": args.db_floor,
            "time_bins": args.time_bins,
            "frequency_bins": args.freq_bins,
        },
        "source_file_count": len(files),
        "source_tree_sha256": digest_before,
        "source_unchanged": source_unchanged,
        "errors": errors,
        "assets": records,
    }
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "spectral_manifest.json"
    html_path = out / "spectral_review.html"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_review_html(html_path, manifest, source)

    print(json.dumps({
        "status": manifest["status"],
        "assets": len(records),
        "errors": len(errors),
        "source_unchanged": source_unchanged,
        "source_tree_sha256": digest_before,
        "manifest": str(manifest_path),
        "review": str(html_path),
    }, indent=2))
    return 0 if manifest["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
