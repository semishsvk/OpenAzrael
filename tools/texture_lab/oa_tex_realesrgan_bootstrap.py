#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

from common import ROOT, write_json

REGISTRY = ROOT / "tools/texture_lab/config/model_registry.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_model_spec(name: str) -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    try:
        return registry["models"][name]
    except KeyError as exc:
        raise SystemExit(f"model is not registered: {name}") from exc


def verify_checkpoint(path: Path, spec: dict) -> dict:
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    size = path.stat().st_size
    digest = sha256_file(path)
    expected_size = int(spec["checkpoint_size_bytes"])
    expected_sha = str(spec["checkpoint_sha256"]).lower()
    ok = size == expected_size and digest.lower() == expected_sha
    return {
        "status": "PASS" if ok else "FAIL",
        "path": str(path),
        "size_bytes": size,
        "expected_size_bytes": expected_size,
        "sha256": digest,
        "expected_sha256": expected_sha,
        "size_ok": size == expected_size,
        "sha256_ok": digest.lower() == expected_sha,
    }


def download_checkpoint(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists():
        partial.unlink()
    with urllib.request.urlopen(url) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(destination)


def clone_upstream(spec: dict, destination: Path) -> None:
    if destination.exists():
        raise SystemExit(f"upstream destination already exists: {destination}")
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            str(spec["upstream_tag"]),
            str(spec["upstream_repository"]),
            str(destination),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap and cryptographically verify the pinned Real-ESRGAN RT-POC-01 runtime."
    )
    parser.add_argument("--model", default="RealESRGAN_x4plus")
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=ROOT / ".local/texture_lab/realesrgan",
    )
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--clone-upstream", action="store_true")
    parser.add_argument("--install-python-deps", action="store_true")
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    spec = load_model_spec(args.model)
    runtime = args.runtime_dir.resolve()
    source_dir = runtime / "Real-ESRGAN"
    weights_dir = runtime / "weights"
    checkpoint = weights_dir / str(spec["checkpoint_filename"])

    runtime.mkdir(parents=True, exist_ok=True)

    if args.clone_upstream and not source_dir.exists():
        clone_upstream(spec, source_dir)

    if args.install_python_deps:
        if not source_dir.is_dir():
            raise SystemExit("--install-python-deps requires the pinned upstream source directory")
        subprocess.run(
            [
                args.python_exe,
                "-m",
                "pip",
                "install",
                "basicsr==1.4.2",
                "facexlib>=0.2.5",
                "gfpgan>=1.3.5",
                "-e",
                str(source_dir),
            ],
            check=True,
        )

    before = verify_checkpoint(checkpoint, spec)
    if args.download_model and before["status"] != "PASS":
        download_checkpoint(str(spec["official_checkpoint_url"]), checkpoint)

    verification = verify_checkpoint(checkpoint, spec)
    upstream_status = {
        "path": str(source_dir),
        "exists": source_dir.is_dir(),
        "expected_tag": spec["upstream_tag"],
        "expected_commit": spec["upstream_commit"],
        "version_file": None,
        "version_ok": None,
        "git_head": None,
        "git_head_ok": None,
    }
    version_path = source_dir / "VERSION"
    if version_path.is_file():
        version = version_path.read_text(encoding="utf-8").strip()
        upstream_status["version_file"] = version
        upstream_status["version_ok"] = version == str(spec["upstream_version"])

    if (source_dir / ".git").exists():
        try:
            head = subprocess.check_output(
                ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            upstream_status["git_head"] = head
            upstream_status["git_head_ok"] = head == str(spec["upstream_commit"])
        except Exception:
            upstream_status["git_head_ok"] = False

    report = {
        "schema": "openazrael.texture_lab.realesrgan_bootstrap.v1",
        "model": args.model,
        "runtime_dir": str(runtime),
        "source": upstream_status,
        "checkpoint": verification,
        "ready_for_inference": (
            verification.get("status") == "PASS"
            and upstream_status["exists"]
            and upstream_status["version_ok"] is True
            and upstream_status["git_head_ok"] is True
        ),
    }
    report_path = args.report or runtime / "bootstrap_report.json"
    write_json(report_path, report)

    if verification.get("status") == "FAIL":
        print("FAIL checkpoint identity mismatch")
        return 2
    if not report["ready_for_inference"]:
        print(f"HOLD runtime incomplete report={report_path}")
        return 1

    print(
        "PASS Real-ESRGAN runtime identity "
        f"model={args.model} sha256={verification['sha256']} report={report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
