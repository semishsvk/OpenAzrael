#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from common import (
    ROOT,
    prepare_backend_colorkey_input,
    reapply_source_colorkey_mask,
    sha256_file,
    write_json,
)

MODEL_REGISTRY = ROOT / "tools/texture_lab/config/model_registry.json"


def load_registered_model(name: str) -> dict | None:
    if not MODEL_REGISTRY.is_file():
        return None
    registry = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))
    return registry.get("models", {}).get(name)


def verify_registered_runtime(model_name: str, realesrgan_root: Path, model_path: Path) -> dict:
    spec = load_registered_model(model_name)
    if spec is None:
        return {
            "registered": False,
            "status": "UNREGISTERED",
            "model": model_name,
        }

    version_path = realesrgan_root / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else None
    git_head = None
    if (realesrgan_root / ".git").exists():
        try:
            git_head = subprocess.check_output(
                ["git", "-C", str(realesrgan_root), "rev-parse", "HEAD"],
                text=True,
            ).strip()
        except Exception:
            git_head = None
    digest = sha256_file(model_path) if model_path.is_file() else None
    size = model_path.stat().st_size if model_path.is_file() else None

    checks = {
        "source_version_ok": version == str(spec["upstream_version"]),
        "source_commit_ok": git_head == str(spec["upstream_commit"]),
        "checkpoint_size_ok": size == int(spec["checkpoint_size_bytes"]),
        "checkpoint_sha256_ok": digest == str(spec["checkpoint_sha256"]),
        "factor_ok": int(spec["scale"]) == 4,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "registered": True,
        "status": status,
        "model": model_name,
        "source_version": version,
        "expected_source_version": spec["upstream_version"],
        "source_git_head": git_head,
        "expected_source_git_head": spec["upstream_commit"],
        "checkpoint_size_bytes": size,
        "expected_checkpoint_size_bytes": spec["checkpoint_size_bytes"],
        "checkpoint_sha256": digest,
        "expected_checkpoint_sha256": spec["checkpoint_sha256"],
        "checks": checks,
    }


def build_realesrgan_python_command(
    python_exe: str,
    realesrgan_root: Path,
    src: Path,
    out_dir: Path,
    model_name: str,
    model_path: Path,
    factor: int,
    tile: int,
    fp32: bool,
    denoise_strength: float | None,
) -> list[str]:
    script = realesrgan_root / "inference_realesrgan.py"
    argv = [
        python_exe,
        str(script),
        "-n", model_name,
        "-i", str(src),
        "-o", str(out_dir),
        "-s", str(factor),
        "--model_path", str(model_path),
        "--suffix", "",
        "--ext", "png",
        "-t", str(tile),
    ]
    if fp32:
        argv.append("--fp32")
    if denoise_strength is not None:
        argv.extend(["-dn", str(denoise_strength)])
    return argv


def run_official_python(args, src: Path, dest: Path) -> dict:
    if args.realesrgan_root is None or args.model_path is None:
        raise SystemExit("--realesrgan-root and --model-path are required for realesrgan-python backend")
    script = args.realesrgan_root / "inference_realesrgan.py"
    if not script.is_file():
        raise SystemExit(f"Real-ESRGAN inference script not found: {script}")
    if not args.model_path.is_file():
        raise SystemExit(f"Real-ESRGAN model not found: {args.model_path}")

    identity = verify_registered_runtime(args.model, args.realesrgan_root, args.model_path)
    if identity.get("registered") and identity.get("status") != "PASS":
        raise SystemExit(
            "registered Real-ESRGAN runtime identity mismatch; "
            "refusing inference. Run oa_tex_realesrgan_doctor.py for details."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = dest.parent / f"{src.stem}.png"
    argv = build_realesrgan_python_command(
        args.python_exe,
        args.realesrgan_root,
        src,
        dest.parent,
        args.model,
        args.model_path,
        args.factor,
        args.tile,
        args.fp32,
        args.denoise_strength,
    )
    started = time.perf_counter()
    subprocess.run(argv, check=True)
    elapsed_seconds = time.perf_counter() - started
    if not expected.is_file():
        raise RuntimeError(f"Real-ESRGAN completed but expected output is missing: {expected}")
    if expected != dest:
        if dest.exists():
            dest.unlink()
        shutil.move(str(expected), str(dest))
    return {
        "backend": "realesrgan-python",
        "argv": argv,
        "model_path": str(args.model_path),
        "model_sha256": sha256_file(args.model_path),
        "runtime_identity": identity,
        "tile": args.tile,
        "fp32": bool(args.fp32),
        "denoise_strength": args.denoise_strength,
        "elapsed_seconds": elapsed_seconds,
    }


def run_command_template(args, src: Path, dest: Path) -> dict:
    if not args.command:
        raise SystemExit("--command is required for command backend")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rendered = args.command.format(
        input=str(src),
        output=str(dest),
        factor=args.factor,
        model=args.model,
    )
    argv = shlex.split(rendered)
    started = time.perf_counter()
    subprocess.run(argv, check=True)
    elapsed_seconds = time.perf_counter() - started
    if not dest.is_file():
        raise RuntimeError(f"restore command did not create: {dest}")
    return {
        "backend": "command",
        "argv": argv,
        "command_template": args.command,
        "runtime_identity": {
            "registered": False,
            "status": "EXTERNAL_BACKEND_UNVERIFIED",
        },
        "elapsed_seconds": elapsed_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Restored adapter. Generated pixels stay outside Git; exact model identity is recorded."
    )
    parser.add_argument("--input", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--report", type=Path, default=ROOT / "data/texture_lab/ai_restore_run.json")
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument("--model", default="RealESRGAN_x4plus")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--backend", choices=["realesrgan-python", "command"], default="realesrgan-python")
    parser.add_argument("--realesrgan-root", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--tile", type=int, default=0, help="Prefer 0 for texture fidelity; use tiling only when required.")
    parser.add_argument("--fp32", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--denoise-strength", type=float, default=None)
    parser.add_argument(
        "--command",
        default=None,
        help="Fallback command template containing {input}, {output}, {factor}, {model}.",
    )
    args = parser.parse_args()

    wanted = set(args.only or [])
    sources = [p for p in sorted(args.input.glob("*.png")) if not wanted or p.stem in wanted]
    if not sources:
        raise SystemExit("no input PNGs selected")

    rows = []
    backend_records = []
    run_started = time.perf_counter()
    for src in sources:
        out_dir = args.output / src.stem
        dest = out_dir / f"realesrgan_x{args.factor}.png"
        with tempfile.TemporaryDirectory(prefix="openazrael_tex_") as td:
            prepared_src, colorkey_prepared = prepare_backend_colorkey_input(
                src, Path(td) / src.name
            )
            if args.backend == "realesrgan-python":
                backend = run_official_python(args, prepared_src, dest)
            else:
                backend = run_command_template(args, prepared_src, dest)

        colorkey_reapplied = reapply_source_colorkey_mask(src, dest)
        backend_records.append(backend)
        rows.append(
            {
                "id": src.stem,
                "source_sha256": sha256_file(src),
                "output_sha256": sha256_file(dest),
                "model": args.model,
                "factor": args.factor,
                "backend": backend["backend"],
                "inference_wall_seconds": float(
                    backend.get("elapsed_seconds", 0.0)
                ),
                "legacy_colorkey_input_prepared": colorkey_prepared,
                "legacy_colorkey_mask_reapplied": colorkey_reapplied,
            }
        )

    run_wall_seconds = time.perf_counter() - run_started
    measured_inference_seconds = sum(
        float(row.get("inference_wall_seconds", 0.0))
        for row in rows
    )
    reproducibility = backend_records[0] if backend_records else {}
    write_json(
        args.report,
        {
            "schema": "openazrael.texture_lab.ai_restore_run.v5",
            "mode": "ai_restored",
            "reproducibility": reproducibility,
            "legacy_colorkey_policy": "prepare_alpha_safe_input_then_reapply_exact_source_mask",
            "performance": {
                "texture_count": len(rows),
                "run_wall_seconds": run_wall_seconds,
                "measured_inference_wall_seconds": measured_inference_seconds,
                "mean_inference_wall_seconds_per_texture": (
                    measured_inference_seconds / len(rows)
                    if rows
                    else None
                ),
                "textures_per_minute_inference_only": (
                    (60.0 * len(rows) / measured_inference_seconds)
                    if measured_inference_seconds > 0
                    else None
                ),
                "timing_scope": (
                    "wall-clock subprocess timing; observational, "
                    "not a GPU kernel benchmark"
                ),
            },
            "textures": rows,
        },
    )
    print(f"PASS ai_restored textures={len(rows)} backend={args.backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
