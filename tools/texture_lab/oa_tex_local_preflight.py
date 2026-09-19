#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from common import PILLOW_VERSION, PINNED_PILLOW_VERSION, ROOT, write_json

SMOKE_SETS = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"
QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
CLASSIC_DIR = ROOT / "assets/textures/classic"
ENHANCED_DIR = ROOT / "assets/textures/enhanced"
BASELINE = ROOT / "data/texture_lab/rt_poc_01_drift_baseline.json"

GIB = 1024 ** 3
DISK_SAFETY_BYTES = 5 * GIB


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_existing(path: Path) -> Path:
    current = path.resolve()
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def disk_info(path: Path) -> dict:
    probe = nearest_existing(path)
    usage = shutil.disk_usage(probe)
    return {
        "requested_path": str(path),
        "probe_path": str(probe),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def total_ram_bytes() -> int | None:
    try:
        if hasattr(os, "sysconf"):
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            return page_size * pages
    except (ValueError, OSError, TypeError):
        pass
    return None


def nvidia_gpu_info() -> list[dict]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []

    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            total_mib = int(parts[1])
            free_mib = int(parts[2])
        except ValueError:
            continue
        rows.append(
            {
                "name": parts[0],
                "vram_total_mib": total_mib,
                "vram_free_mib": free_mib,
                "driver_version": parts[3],
            }
        )
    return rows


def preset_info(name: str) -> dict:
    config = load_json(SMOKE_SETS)
    preset = config.get("presets", {}).get(name)
    if not isinstance(preset, dict):
        raise SystemExit(f"unknown AI smoke preset: {name}")
    return preset


def toolchain_check() -> dict:
    baseline_pillow = None
    baseline_schema = None
    if BASELINE.is_file():
        try:
            baseline = load_json(BASELINE)
            baseline_pillow = baseline.get("pillow_version")
            baseline_schema = baseline.get("schema")
        except (OSError, json.JSONDecodeError):
            baseline_pillow = None

    current_ok = PILLOW_VERSION == PINNED_PILLOW_VERSION
    baseline_ok = baseline_pillow == PINNED_PILLOW_VERSION
    return {
        "current_pillow_version": PILLOW_VERSION,
        "expected_pillow_version": PINNED_PILLOW_VERSION,
        "current_pillow_ok": current_ok,
        "baseline_path": str(BASELINE),
        "baseline_schema": baseline_schema,
        "baseline_pillow_version": baseline_pillow,
        "baseline_pillow_ok": baseline_ok,
        "status": "PASS" if current_ok and baseline_ok else "HOLD",
        "repair": (
            "Install tools/texture_lab/requirements-source-safe.txt, then rerun "
            "oa_tex_run_poc.py and oa_tex_calibrate_drift.py."
        ),
    }


def classic_check() -> dict:
    files = sorted(CLASSIC_DIR.glob("*.png")) if CLASSIC_DIR.is_dir() else []
    return {
        "path": str(CLASSIC_DIR),
        "count": len(files),
        "expected_count": 86,
        "status": "PASS" if len(files) == 86 else "HOLD",
    }


def enhanced_check(texture_ids: list[str], variant: str) -> dict:
    rows = []
    for texture_id in texture_ids:
        path = ENHANCED_DIR / texture_id / variant
        rows.append(
            {
                "id": texture_id,
                "path": str(path),
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return {
        "variant": variant,
        "rows": rows,
        "status": "PASS" if all(row["exists"] for row in rows) else "HOLD",
    }


def qwen_storage_check(comfy_root: Path) -> dict:
    contract = load_json(QWEN_CONTRACT)
    rows = []
    missing_bytes = 0
    for role, spec in contract["required_models"].items():
        path = comfy_root / str(spec["relative_path"])
        expected = int(spec["size_bytes"])
        exists = path.is_file()
        actual = path.stat().st_size if exists else None
        size_ok = actual == expected if exists else False
        if not size_ok:
            missing_bytes += expected
        rows.append(
            {
                "role": role,
                "path": str(path),
                "exists": exists,
                "size_bytes": actual,
                "expected_size_bytes": expected,
                "size_ok": size_ok,
                "sha256_expected": spec["sha256"],
            }
        )

    storage = disk_info(comfy_root)
    required_free = missing_bytes + DISK_SAFETY_BYTES
    enough_space = storage["free_bytes"] >= required_free
    all_present_by_size = all(row["size_ok"] for row in rows)
    return {
        "comfy_root": str(comfy_root),
        "models": rows,
        "missing_or_invalid_model_bytes": missing_bytes,
        "disk_safety_bytes": DISK_SAFETY_BYTES,
        "required_free_bytes_for_missing_models": required_free,
        "disk": storage,
        "disk_capacity_ok": enough_space,
        "all_required_models_present_by_size": all_present_by_size,
        "note": (
            "Size checks are planning-only. oa_tex_qwen_preflight.py performs "
            "the required SHA-256 verification before execution."
        ),
        "status": "PASS" if enough_space else "HOLD",
    }


def realesrgan_check(
    source_root: Path | None,
    model_path: Path | None,
    python_exe: Path | None,
) -> dict:
    rows = {
        "source_root": {
            "path": str(source_root) if source_root else None,
            "exists": bool(source_root and (source_root / "inference_realesrgan.py").is_file()),
        },
        "model": {
            "path": str(model_path) if model_path else None,
            "exists": bool(model_path and model_path.is_file()),
        },
        "python": {
            "path": str(python_exe) if python_exe else None,
            "exists": bool(python_exe and python_exe.is_file()),
        },
    }
    supplied = source_root is not None or model_path is not None or python_exe is not None
    ready = supplied and all(row["exists"] for row in rows.values())
    return {
        **rows,
        "status": "PASS" if ready else "HOLD",
        "note": (
            "File presence only. oa_tex_realesrgan_doctor.py verifies exact "
            "source/checkpoint identity and Python dependencies."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local disk/input/hardware readiness preflight for OpenAzrael AI texture stages."
    )
    parser.add_argument("--preset", required=True)
    parser.add_argument("--comfy-root", type=Path, default=None)
    parser.add_argument("--enhanced-variant", default="lanczos_x4.png")
    parser.add_argument("--realesrgan-root", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--realesrgan-python", type=Path, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / ".local/texture_lab/local_preflight.json",
    )
    args = parser.parse_args()

    preset = preset_info(args.preset)
    mode = str(preset["mode"])
    texture_ids = [str(value) for value in preset.get("textures", [])]

    system = {
        "platform": platform.platform(),
        "python": sys.version,
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ram_total_bytes": total_ram_bytes(),
        "nvidia_gpus": nvidia_gpu_info(),
        "project_disk": disk_info(ROOT),
    }

    checks = {
        "toolchain": toolchain_check(),
        "classic": classic_check(),
    }
    if mode == "recreated":
        checks["enhanced"] = enhanced_check(texture_ids, args.enhanced_variant)
        if args.comfy_root is None:
            checks["qwen_storage"] = {
                "status": "HOLD",
                "reason": "--comfy-root is required for a recreated-stage readiness decision",
            }
        else:
            checks["qwen_storage"] = qwen_storage_check(args.comfy_root)
    else:
        checks["realesrgan"] = realesrgan_check(
            args.realesrgan_root,
            args.model_path,
            args.realesrgan_python,
        )

    blocking = [
        name
        for name, row in checks.items()
        if row.get("status") != "PASS"
    ]
    ready = not blocking
    report = {
        "schema": "openazrael.texture_lab.local_preflight.v2",
        "preset": args.preset,
        "mode": mode,
        "textures": texture_ids,
        "system": system,
        "checks": checks,
        "blocking_checks": blocking,
        "ready_for_runtime_doctors": ready,
        "note": (
            "VRAM/RAM are reported rather than used as arbitrary hard gates. "
            "The runtime doctors remain authoritative for actual backend readiness."
        ),
    }
    write_json(args.out, report)
    print(
        f"{'PASS' if ready else 'HOLD'} local_preflight "
        f"preset={args.preset} blocking={','.join(blocking) if blocking else 'none'} "
        f"report={args.out}"
    )
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
