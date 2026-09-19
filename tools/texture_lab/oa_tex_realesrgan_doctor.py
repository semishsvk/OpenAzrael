#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from common import ROOT, sha256_file, write_json

REGISTRY = ROOT / "tools/texture_lab/config/model_registry.json"


def module_status(name: str) -> dict:
    try:
        module = importlib.import_module(name)
        return {
            "status": "PASS",
            "version": getattr(module, "__version__", "unknown"),
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose the pinned OpenAzrael Real-ESRGAN runtime.")
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=ROOT / ".local/texture_lab/realesrgan",
    )
    parser.add_argument("--model", default="RealESRGAN_x4plus")
    parser.add_argument("--realesrgan-root", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    spec = registry["models"][args.model]
    source_dir = args.realesrgan_root or (args.runtime_dir / "Real-ESRGAN")
    checkpoint = args.model_path or (args.runtime_dir / "weights" / spec["checkpoint_filename"])

    checkpoint_status = {"status": "MISSING"}
    if checkpoint.is_file():
        digest = sha256_file(checkpoint)
        checkpoint_status = {
            "status": "PASS" if (
                checkpoint.stat().st_size == int(spec["checkpoint_size_bytes"])
                and digest == spec["checkpoint_sha256"]
            ) else "FAIL",
            "size_bytes": checkpoint.stat().st_size,
            "sha256": digest,
        }

    modules = {
        name: module_status(name)
        for name in ["torch", "torchvision", "cv2", "PIL", "basicsr", "realesrgan"]
    }

    source_version = None
    source_head = None
    version_path = source_dir / "VERSION"
    if version_path.is_file():
        source_version = version_path.read_text(encoding="utf-8").strip()
    if (source_dir / ".git").exists():
        try:
            source_head = subprocess.check_output(
                ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                text=True,
            ).strip()
        except Exception:
            source_head = None

    report = {
        "schema": "openazrael.texture_lab.realesrgan_doctor.v1",
        "python": sys.version,
        "platform": platform.platform(),
        "source_dir": str(source_dir),
        "checkpoint_path": str(checkpoint),
        "source_exists": source_dir.is_dir(),
        "source_version": source_version,
        "source_version_ok": source_version == spec["upstream_version"],
        "source_git_head": source_head,
        "source_git_head_ok": source_head == spec["upstream_commit"],
        "checkpoint": checkpoint_status,
        "modules": modules,
        "ready": (
            source_dir.is_dir()
            and source_version == spec["upstream_version"]
            and source_head == spec["upstream_commit"]
            and checkpoint_status.get("status") == "PASS"
            and modules["torch"]["status"] == "PASS"
            and modules["torchvision"]["status"] == "PASS"
            and modules["basicsr"]["status"] == "PASS"
            and modules["realesrgan"]["status"] == "PASS"
        ),
    }
    report_path = args.report or args.runtime_dir / "doctor_report.json"
    write_json(report_path, report)
    print(("PASS" if report["ready"] else "HOLD") + f" Real-ESRGAN doctor report={report_path}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
