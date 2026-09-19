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
from oa_tex_realesrgan_runtime import (
    load_contract as load_runtime_contract,
    pip_freeze_snapshot,
    probe_python,
)

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


def dependency_install_commands(
    python_exe: str | Path,
    source_dir: Path,
    runtime_contract: dict,
) -> list[list[str]]:
    basicsr_version = str(
        runtime_contract["packages"]["basicsr"]["version"]
    )
    return [
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            f"basicsr=={basicsr_version}",
        ],
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "-e",
            str(source_dir),
        ],
    ]


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
    parser.add_argument("--create-venv", action="store_true")
    parser.add_argument("--venv-dir", type=Path, default=None)
    parser.add_argument("--venv-system-site-packages", action="store_true")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    spec = load_model_spec(args.model)
    runtime = args.runtime_dir.resolve()
    source_dir = runtime / "Real-ESRGAN"
    weights_dir = runtime / "weights"
    checkpoint = weights_dir / str(spec["checkpoint_filename"])

    runtime.mkdir(parents=True, exist_ok=True)

    effective_python = Path(args.python_exe)
    venv_dir = args.venv_dir or (runtime / "venv")
    if args.create_venv:
        candidate = (
            venv_dir / "Scripts" / "python.exe"
            if sys.platform.startswith("win")
            else venv_dir / "bin" / "python"
        )
        if not candidate.is_file():
            argv = [args.python_exe, "-m", "venv"]
            if args.venv_system_site_packages:
                argv.append("--system-site-packages")
            argv.append(str(venv_dir))
            subprocess.run(argv, check=True)
        effective_python = candidate

    if args.clone_upstream and not source_dir.exists():
        clone_upstream(spec, source_dir)

    runtime_contract = load_runtime_contract()
    dependency_preflight = None
    dependency_postflight = None
    freeze_snapshot = None

    if args.install_python_deps:
        if not source_dir.is_dir():
            raise SystemExit("--install-python-deps requires the pinned upstream source directory")

        dependency_preflight = probe_python(
            effective_python,
            runtime_contract,
            require_basicsr=False,
            require_realesrgan=False,
        )
        if dependency_preflight.get("status") != "PASS":
            raise SystemExit(
                "Real-ESRGAN dependency install requires the exact pinned "
                "Python/Torch/torchvision runtime first. Run "
                "oa_tex_realesrgan_runtime.py check for details."
            )

        for install_argv in dependency_install_commands(
            effective_python,
            source_dir,
            runtime_contract,
        ):
            subprocess.run(install_argv, check=True)

        dependency_postflight = probe_python(
            effective_python,
            runtime_contract,
            require_basicsr=True,
            require_realesrgan=True,
        )
        if dependency_postflight.get("status") != "PASS":
            raise SystemExit(
                "installed Real-ESRGAN texture runtime does not satisfy the "
                "pinned compatibility contract"
            )
        freeze_snapshot = pip_freeze_snapshot(effective_python)
        if freeze_snapshot.get("status") != "PASS":
            raise SystemExit("could not fingerprint the installed Python runtime")

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
        "schema": "openazrael.texture_lab.realesrgan_bootstrap.v2",
        "model": args.model,
        "runtime_dir": str(runtime),
        "source": upstream_status,
        "checkpoint": verification,
        "python_runtime": {
            "executable": str(effective_python),
            "venv_dir": str(venv_dir) if args.create_venv else None,
            "created_or_selected_venv": bool(args.create_venv),
            "system_site_packages": bool(args.venv_system_site_packages),
        },
        "identity_ready": (
            verification.get("status") == "PASS"
            and upstream_status["exists"]
            and upstream_status["version_ok"] is True
            and upstream_status["git_head_ok"] is True
        ),
        "runtime_contract": {
            "schema": runtime_contract.get("schema"),
            "python_major_minor": runtime_contract["python"]["major_minor"],
            "torch": runtime_contract["packages"]["torch"]["version"],
            "torchvision": runtime_contract["packages"]["torchvision"]["version"],
            "basicsr": runtime_contract["packages"]["basicsr"]["version"],
            "face_enhancement": runtime_contract.get("face_enhancement"),
        },
        "dependency_install_requested": bool(args.install_python_deps),
        "dependency_preflight": dependency_preflight,
        "dependency_postflight": dependency_postflight,
        "pip_freeze": freeze_snapshot,
        "texture_runtime_excludes": runtime_contract.get(
            "excluded_texture_runtime_packages", []
        ),
        "doctor_required_for_inference": True,
    }
    report_path = args.report or runtime / "bootstrap_report.json"
    write_json(report_path, report)

    if verification.get("status") == "FAIL":
        print("FAIL checkpoint identity mismatch")
        return 2
    if not report["identity_ready"]:
        print(f"HOLD runtime identity incomplete report={report_path}")
        return 1

    print(
        "PASS Real-ESRGAN runtime identity "
        f"model={args.model} sha256={verification['sha256']} "
        f"python={effective_python} report={report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
