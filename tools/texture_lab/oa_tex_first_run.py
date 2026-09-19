#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from PIL import Image

from common import PINNED_PILLOW_VERSION, PILLOW_VERSION, ROOT, write_json
from oa_tex_realesrgan_runtime import load_contract as load_runtime_contract, probe_python

DEFAULT_RUNTIME = ROOT / ".local/texture_lab/realesrgan"
DEFAULT_LAUNCHPAD_DIR = ROOT / ".local/texture_lab/launchpad"
SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"


def venv_python(runtime_dir: Path) -> Path:
    return (
        runtime_dir / "venv" / "Scripts" / "python.exe"
        if sys.platform.startswith("win")
        else runtime_dir / "venv" / "bin" / "python"
    )


def runtime_paths(runtime_dir: Path) -> dict[str, Path]:
    return {
        "runtime": runtime_dir,
        "source": runtime_dir / "Real-ESRGAN",
        "model": runtime_dir / "weights" / "RealESRGAN_x4plus.pth",
        "python": venv_python(runtime_dir),
    }


def quote(argv: list[str]) -> str:
    return shlex.join([str(v) for v in argv])


def command_record(name: str, argv: list[str]) -> dict:
    return {"name": name, "argv": [str(v) for v in argv], "command": quote(argv)}


def baseline_plan() -> list[dict]:
    py = sys.executable
    return [
        command_record(
            "scan_classic",
            [py, str(ROOT / "tools/texture_lab/oa_tex_scan.py")],
        ),
        command_record(
            "build_enhanced",
            [py, str(ROOT / "tools/texture_lab/oa_tex_run_poc.py")],
        ),
        command_record(
            "calibrate_drift",
            [py, str(ROOT / "tools/texture_lab/oa_tex_calibrate_drift.py")],
        ),
    ]


def bootstrap_plan(
    runtime_dir: Path,
    install_python_deps: bool,
    runtime_python: str | None = None,
) -> list[dict]:
    paths = runtime_paths(runtime_dir)
    base_python = runtime_python or sys.executable
    bootstrap = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_realesrgan_bootstrap.py"),
        "--runtime-dir",
        str(runtime_dir),
        "--clone-upstream",
        "--download-model",
        "--create-venv",
        "--python-exe",
        str(base_python),
    ]
    commands = [command_record("bootstrap_realesrgan", bootstrap)]
    if install_python_deps:
        torch_check = [
            sys.executable,
            str(ROOT / "tools/texture_lab/oa_tex_realesrgan_runtime.py"),
            "check",
            "--python-exe",
            str(paths["python"]),
        ]
        install = [
            sys.executable,
            str(ROOT / "tools/texture_lab/oa_tex_realesrgan_bootstrap.py"),
            "--runtime-dir",
            str(runtime_dir),
            "--install-python-deps",
            "--python-exe",
            str(paths["python"]),
        ]
        commands.extend(
            [
                command_record("verify_user_installed_torch", torch_check),
                command_record("install_realesrgan_python_deps", install),
            ]
        )
    return commands


def restored_smoke_plan(runtime_dir: Path) -> list[dict]:
    paths = runtime_paths(runtime_dir)
    launch_dir = DEFAULT_LAUNCHPAD_DIR
    preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_local_preflight.py"),
        "--preset",
        "restored_smoke_1",
        "--realesrgan-root",
        str(paths["source"]),
        "--model-path",
        str(paths["model"]),
        "--realesrgan-python",
        str(paths["python"]),
        "--out",
        str(launch_dir / "restored_smoke_1_preflight.json"),
    ]
    doctor = [
        str(paths["python"]),
        str(ROOT / "tools/texture_lab/oa_tex_realesrgan_doctor.py"),
        "--runtime-dir",
        str(runtime_dir),
        "--realesrgan-root",
        str(paths["source"]),
        "--model-path",
        str(paths["model"]),
        "--report",
        str(launch_dir / "restored_smoke_1_doctor.json"),
    ]
    bakeoff = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_ai_bakeoff.py"),
        "restored",
        "--preset",
        "restored_smoke_1",
        "--realesrgan-python",
        str(paths["python"]),
        "--realesrgan-root",
        str(paths["source"]),
        "--model-path",
        str(paths["model"]),
    ]
    return [
        command_record("local_preflight", preflight),
        command_record("runtime_doctor", doctor),
        command_record("canonical_bakeoff", bakeoff),
    ]


def poc_source_status(
    source_dir: Path = ROOT / "assets/textures/classic",
    selection_path: Path = SELECTION,
) -> dict:
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    rows = []
    for entry in selection.get("textures", []):
        texture_id = str(entry["id"])
        expected = tuple(int(v) for v in entry.get("expected_size", []))
        path = source_dir / f"{texture_id}.png"
        actual = None
        readable = False
        if path.is_file():
            try:
                with Image.open(path) as image:
                    image.load()
                    actual = tuple(image.size)
                    readable = True
            except Exception:
                readable = False
        rows.append(
            {
                "id": texture_id,
                "path": str(path),
                "exists": path.is_file(),
                "readable": readable,
                "expected_size": list(expected),
                "actual_size": list(actual) if actual is not None else None,
                "size_ok": bool(readable and expected and actual == expected),
            }
        )
    ok = bool(rows) and all(row["size_ok"] for row in rows)
    return {
        "status": "PASS" if ok else "HOLD",
        "selection_path": str(selection_path),
        "source_dir": str(source_dir),
        "expected_texture_count": len(rows),
        "rows": rows,
    }


def classic_count() -> int:
    classic = ROOT / "assets/textures/classic"
    return len(list(classic.glob("*.png"))) if classic.is_dir() else 0


def baseline_status() -> dict:
    baseline = ROOT / "data/texture_lab/rt_poc_01_drift_baseline.json"
    run_report = ROOT / "data/texture_lab/rt_poc_01_run.json"
    payload = {}
    if baseline.is_file():
        try:
            payload = json.loads(baseline.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    baseline_ok = (
        payload.get("schema") == "openazrael.texture_lab.rt_poc_01_drift_baseline.v2"
        and payload.get("pillow_version") == PINNED_PILLOW_VERSION
    )
    poc = poc_source_status()
    return {
        "classic_count": classic_count(),
        "classic_expected": 86,
        "classic_ok": classic_count() == 86,
        "current_pillow": PILLOW_VERSION,
        "pinned_pillow": PINNED_PILLOW_VERSION,
        "pillow_ok": PILLOW_VERSION == PINNED_PILLOW_VERSION,
        "baseline_path": str(baseline),
        "baseline_exists": baseline.is_file(),
        "baseline_ok": baseline_ok,
        "run_report_path": str(run_report),
        "run_report_exists": run_report.is_file(),
        "poc_selection": poc,
    }


def realesrgan_status(runtime_dir: Path) -> dict:
    paths = runtime_paths(runtime_dir)
    source = paths["source"]
    model = paths["model"]
    python = paths["python"]
    python_present = python.is_file()
    contract_probe = (
        probe_python(
            python,
            load_runtime_contract(),
            require_basicsr=False,
            require_realesrgan=False,
        )
        if python_present
        else {"status": "MISSING"}
    )
    return {
        "runtime_dir": str(runtime_dir),
        "source_path": str(source),
        "source_present": (source / "inference_realesrgan.py").is_file(),
        "model_path": str(model),
        "model_present": model.is_file(),
        "python_path": str(python),
        "python_present": python_present,
        "runtime_contract_probe": contract_probe,
        "runtime_contract_ok": contract_probe.get("status") == "PASS",
    }


def build_status(runtime_dir: Path) -> dict:
    baseline = baseline_status()
    realesrgan = realesrgan_status(runtime_dir)
    blockers: list[str] = []
    if not baseline["classic_ok"]:
        blockers.append("classic_corpus")
    if baseline["poc_selection"]["status"] != "PASS":
        blockers.append("poc_source_identity")
    if not baseline["pillow_ok"]:
        blockers.append("pinned_pillow")
    if not baseline["baseline_ok"]:
        blockers.append("deterministic_baseline")
    if not realesrgan["source_present"]:
        blockers.append("realesrgan_source")
    if not realesrgan["model_present"]:
        blockers.append("realesrgan_model")
    if not realesrgan["python_present"]:
        blockers.append("realesrgan_venv")
    elif not realesrgan["runtime_contract_ok"]:
        blockers.append("realesrgan_runtime_contract")

    return {
        "schema": "openazrael.texture_lab.first_run_launchpad.v1",
        "command": "status",
        "source_ready_for_smoke_preflight": not blockers,
        "blockers": blockers,
        "baseline": baseline,
        "realesrgan": realesrgan,
        "notes": [
            "A source-ready launchpad status does not prove Python/Torch/backend runtime readiness.",
            "restored-smoke-1 still requires the Real-ESRGAN doctor to PASS.",
            "PyTorch/CUDA installation is intentionally explicit because the correct build depends on the development machine.",
            "The launchpad refuses dependency installation until torch and torchvision already import successfully inside the isolated venv.",
        ],
    }


def run_commands(
    commands: list[dict],
    dry_run: bool,
    stop_on_failure: bool = True,
) -> tuple[int, list[dict]]:
    results = []
    for record in commands:
        print(("PLAN" if dry_run else "RUN"), record["name"], record["command"])
        if dry_run:
            results.append({**record, "status": "PLANNED"})
            continue
        completed = subprocess.run(record["argv"], check=False)
        row = {**record, "returncode": completed.returncode}
        row["status"] = "PASS" if completed.returncode == 0 else "FAIL"
        results.append(row)
        if completed.returncode != 0 and stop_on_failure:
            return completed.returncode, results
    return 0, results


def write_launch_report(command: str, runtime_dir: Path, results: list[dict], rc: int) -> Path:
    DEFAULT_LAUNCHPAD_DIR.mkdir(parents=True, exist_ok=True)
    path = DEFAULT_LAUNCHPAD_DIR / f"{command}.json"
    payload = {
        "schema": "openazrael.texture_lab.first_run_execution.v1",
        "command": command,
        "status": "PASS" if rc == 0 else "HOLD",
        "runtime_dir": str(runtime_dir),
        "results": results,
    }
    write_json(path, payload)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-platform launchpad for the first OpenAzrael Texture Lab Real-ESRGAN experiment."
    )
    parser.add_argument(
        "command",
        choices=[
            "status",
            "prepare-baseline",
            "bootstrap-realesrgan",
            "restored-smoke-1",
        ],
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=DEFAULT_RUNTIME,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--runtime-python",
        default=None,
        help=(
            "Base Python used to create the Real-ESRGAN venv. RT-POC-01 "
            "currently requires Python 3.11."
        ),
    )
    parser.add_argument(
        "--install-python-deps",
        action="store_true",
        help=(
            "During bootstrap, install the pinned Real-ESRGAN Python packages. "
            "PyTorch/CUDA remains an explicit machine-specific prerequisite."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_LAUNCHPAD_DIR / "status.json",
    )
    args = parser.parse_args()

    runtime_dir = args.runtime_dir.resolve()

    if args.command == "status":
        payload = build_status(runtime_dir)
        write_json(args.out, payload)
        state = "PASS" if payload["source_ready_for_smoke_preflight"] else "HOLD"
        print(
            f"{state} launchpad_status blockers="
            + (",".join(payload["blockers"]) if payload["blockers"] else "none")
            + f" report={args.out}"
        )
        return 0 if state == "PASS" else 1

    if args.command == "prepare-baseline":
        if PILLOW_VERSION != PINNED_PILLOW_VERSION:
            print(
                "HOLD prepare-baseline: install "
                "tools/texture_lab/requirements-source-safe.txt first"
            )
            return 1
        commands = baseline_plan()
    elif args.command == "bootstrap-realesrgan":
        runtime_python = args.runtime_python
        existing_runtime_python = runtime_paths(runtime_dir)["python"]
        if runtime_python is None:
            if existing_runtime_python.is_file():
                # The base interpreter is irrelevant once the isolated venv
                # already exists; bootstrap will select the venv executable.
                runtime_python = sys.executable
            else:
                required = str(load_runtime_contract()["python"]["major_minor"])
                current = f"{sys.version_info.major}.{sys.version_info.minor}"
                if current != required:
                    print(
                        "HOLD bootstrap-realesrgan: provide --runtime-python pointing "
                        f"to Python {required}; current launcher is Python {current}"
                    )
                    return 1
                runtime_python = sys.executable
        commands = bootstrap_plan(
            runtime_dir,
            args.install_python_deps,
            runtime_python,
        )
    else:
        status = build_status(runtime_dir)
        if not args.dry_run and not status["source_ready_for_smoke_preflight"]:
            write_json(args.out, status)
            print(
                "HOLD restored-smoke-1 source prerequisites: "
                + ",".join(status["blockers"])
                + f" report={args.out}"
            )
            return 1
        commands = restored_smoke_plan(runtime_dir)

    rc, results = run_commands(commands, args.dry_run)
    report = write_launch_report(args.command, runtime_dir, results, rc)
    print(
        f"{'PASS' if rc == 0 else 'HOLD'} launchpad command={args.command} report={report}"
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
