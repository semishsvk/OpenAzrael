"""Shared source-safe primitives for OpenAzrael Audio Lab."""
from __future__ import annotations

from array import array
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import math
import struct

AUDIO_EXTENSIONS = {".wav", ".wave", ".ogg", ".mp3", ".flac", ".aif", ".aiff", ".opus"}
TEXT_REFERENCE_EXTENSIONS = {
    ".gd", ".tscn", ".tres", ".cfg", ".ini", ".json", ".py", ".md", ".txt", ".csv", ".toml", ".yaml", ".yml"
}
SKIP_DIR_NAMES = {".git", ".godot", ".import", ".tmp", ".cache", "build", "dist", "exports", "export", "__pycache__"}

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def iter_audio_files(root: Path, extensions: Iterable[str] = AUDIO_EXTENSIONS) -> list[Path]:
    root = root.resolve()
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in extensions}
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in SKIP_DIR_NAMES for part in rel_parts[:-1]):
            continue
        if path.suffix.lower() in exts:
            out.append(path)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix().casefold())

def tree_digest(root: Path, files: Iterable[Path]) -> str:
    h = sha256()
    root = root.resolve()
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix().casefold()):
        rel = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()

def _decode_pcm_samples(raw: bytes, bits: int) -> list[float]:
    if not raw:
        return []
    if bits == 8:
        return [(b - 128) / 128.0 for b in raw]
    if bits == 16:
        usable = len(raw) - (len(raw) % 2)
        vals = array("h")
        vals.frombytes(raw[:usable])
        if struct.pack("=h", 1) != struct.pack("<h", 1):
            vals.byteswap()
        return [v / 32768.0 for v in vals]
    if bits == 24:
        usable = len(raw) - (len(raw) % 3)
        out: list[float] = []
        for i in range(0, usable, 3):
            v = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
            if v & 0x800000:
                v -= 1 << 24
            out.append(v / 8388608.0)
        return out
    if bits == 32:
        usable = len(raw) - (len(raw) % 4)
        return [v[0] / 2147483648.0 for v in struct.iter_unpack("<i", raw[:usable])]
    return []

def _waveform_bins(samples: list[float], bins: int = 96) -> list[list[float]]:
    if not samples:
        return []
    bins = max(1, min(bins, len(samples)))
    out: list[list[float]] = []
    for i in range(bins):
        start = (i * len(samples)) // bins
        end = ((i + 1) * len(samples)) // bins
        segment = samples[start:max(start + 1, end)]
        out.append([round(min(segment), 6), round(max(segment), 6)])
    return out

def _silence_seconds(samples: list[float], sample_rate: int, channels: int, threshold: float = 0.01) -> tuple[float, float]:
    if not samples or sample_rate <= 0 or channels <= 0:
        return 0.0, 0.0
    leading = 0
    for value in samples:
        if abs(value) > threshold:
            break
        leading += 1
    trailing = 0
    for value in reversed(samples):
        if abs(value) > threshold:
            break
        trailing += 1
    denom = float(sample_rate * channels)
    return leading / denom, trailing / denom

def parse_wave(path: Path) -> dict:
    """Parse RIFF/WAVE without mutating it, tolerating missing terminal pad bytes."""
    data = path.read_bytes()
    result = {
        "container": "WAVE",
        "valid": False,
        "riff_declared_size": None,
        "riff_actual_size": len(data),
        "riff_size_matches": None,
        "terminal_pad_missing": False,
        "audio_format": None,
        "channels": None,
        "sample_rate": None,
        "byte_rate": None,
        "block_align": None,
        "sample_width_bits": None,
        "data_bytes": None,
        "frames": None,
        "duration_seconds": None,
        "peak": None,
        "rms": None,
        "clipped_samples": None,
        "clipped_fraction": None,
        "leading_silence_seconds": None,
        "trailing_silence_seconds": None,
        "waveform_bins": [],
        "parse_error": None,
    }
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        result["parse_error"] = "not a RIFF/WAVE container"
        return result

    declared = struct.unpack_from("<I", data, 4)[0] + 8
    result["riff_declared_size"] = declared
    result["riff_size_matches"] = declared == len(data)

    fmt = None
    pcm = None
    offset = 12
    try:
        while offset + 8 <= len(data):
            chunk_id = data[offset:offset + 4]
            chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
            payload_start = offset + 8
            payload_end = payload_start + chunk_size
            if payload_end > len(data):
                raise ValueError("chunk payload exceeds file length")
            payload = data[payload_start:payload_end]
            if chunk_id == b"fmt " and len(payload) >= 16 and fmt is None:
                fmt = struct.unpack_from("<HHIIHH", payload, 0)
            elif chunk_id == b"data" and pcm is None:
                pcm = payload

            next_offset = payload_end + (chunk_size & 1)
            if next_offset > len(data) and payload_end == len(data) and (chunk_size & 1):
                result["terminal_pad_missing"] = True
                next_offset = payload_end
            if next_offset <= offset:
                raise ValueError("invalid RIFF chunk progression")
            offset = next_offset
    except Exception as exc:
        result["parse_error"] = str(exc)
        return result

    if fmt is None:
        result["parse_error"] = "missing fmt chunk"
        return result
    if pcm is None:
        result["parse_error"] = "missing data chunk"
        return result

    audio_format, channels, sample_rate, byte_rate, block_align, bits = fmt
    result.update({
        "audio_format": audio_format,
        "channels": channels,
        "sample_rate": sample_rate,
        "byte_rate": byte_rate,
        "block_align": block_align,
        "sample_width_bits": bits,
        "data_bytes": len(pcm),
    })
    if block_align:
        result["frames"] = len(pcm) // block_align
    if sample_rate and block_align:
        result["duration_seconds"] = round((len(pcm) // block_align) / float(sample_rate), 9)

    if audio_format == 1 and bits in (8, 16, 24, 32):
        samples = _decode_pcm_samples(pcm, bits)
        if samples:
            peak = max(abs(v) for v in samples)
            rms = math.sqrt(sum(v * v for v in samples) / len(samples))
            if bits == 8:
                clipped = sum(1 for b in pcm if b in (0, 255))
            else:
                clipped = sum(1 for v in samples if abs(v) >= 0.999969)
            lead, trail = _silence_seconds(samples, sample_rate, channels)
            result.update({
                "peak": round(peak, 9),
                "rms": round(rms, 9),
                "clipped_samples": clipped,
                "clipped_fraction": round(clipped / float(len(samples)), 9),
                "leading_silence_seconds": round(lead, 9),
                "trailing_silence_seconds": round(trail, 9),
                "waveform_bins": _waveform_bins(samples),
            })

    result["valid"] = True
    return result

def detect_format(path: Path) -> str:
    head = path.read_bytes()[:12]
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "WAVE"
    if head.startswith(b"fLaC"):
        return "FLAC"
    if head.startswith(b"OggS"):
        return "OGG"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "MP3"
    if head.startswith(b"FORM"):
        return "AIFF"
    return path.suffix.lower().lstrip(".").upper() or "UNKNOWN"

def scan_references(reference_root: Path, names: Iterable[str]) -> dict[str, list[str]]:
    """Find literal filename references in repository text files."""
    reference_root = reference_root.resolve()
    keys = sorted({name.casefold(): name for name in names}.items())
    found: dict[str, list[str]] = {canonical: [] for _, canonical in keys}
    if not keys:
        return found
    for path in reference_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_REFERENCE_EXTENSIONS:
            continue
        try:
            rel = path.relative_to(reference_root)
        except ValueError:
            continue
        if any(part in SKIP_DIR_NAMES for part in rel.parts[:-1]):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").casefold()
        except OSError:
            continue
        for folded, canonical in keys:
            if folded in text:
                found[canonical].append(rel.as_posix())
    for canonical in found:
        found[canonical] = sorted(set(found[canonical]), key=str.casefold)
    return found
