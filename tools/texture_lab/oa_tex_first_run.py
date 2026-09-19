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
QWEN_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
DEFAULT_COMFY_SERVER = "http://127.0.0.1:8188"


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


def restored_smoke_check_plan(runtime_dir: Path) -> list[dict]:
    paths = runtime_paths(runtime_dir)
    launch_dir = DEFAULT_LAUNCHPAD_DIR

    runtime_probe = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_realesrgan_runtime.py"),
        "check",
        "--python-exe",
        str(paths["python"]),
        "--require-basicsr",
        "--require-realesrgan",
        "--out",
        str(launch_dir / "restored_smoke_1_runtime_contract.json"),
    ]
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
    dry_run = [
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
        "--dry-run",
    ]
    return [
        command_record("runtime_contract", runtime_probe),
        command_record("local_preflight", preflight),
        command_record("runtime_doctor", doctor),
        command_record("canonical_bakeoff_dry_run", dry_run),
    ]


def restored_smoke_plan(
    runtime_dir: Path,
    replace_existing_run: bool = False,
) -> list[dict]:
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
    if replace_existing_run:
        bakeoff.append("--replace-existing-run")
    return [
        command_record("local_preflight", preflight),
        command_record("runtime_doctor", doctor),
        command_record("canonical_bakeoff", bakeoff),
    ]


def recreated_smoke_check_plan(
    comfy_root: Path,
    server: str = DEFAULT_COMFY_SERVER,
) -> list[dict]:
    launch_dir = DEFAULT_LAUNCHPAD_DIR
    preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_local_preflight.py"),
        "--preset",
        "recreated_smoke_1",
        "--comfy-root",
        str(comfy_root),
        "--out",
        str(launch_dir / "recreated_smoke_1_preflight.json"),
    ]
    doctor = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_comfy_doctor.py"),
        "--server",
        server,
        "--out",
        str(launch_dir / "recreated_smoke_1_comfy_doctor.json"),
    ]
    qwen_preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_qwen_preflight.py"),
        str(QWEN_WORKFLOW),
        "--comfy-root",
        str(comfy_root),
        "--require-model-files",
        "--out",
        str(launch_dir / "recreated_smoke_1_qwen_preflight.json"),
    ]
    dry_run = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_ai_bakeoff.py"),
        "recreated",
        "--preset",
        "recreated_smoke_1",
        "--comfy-root",
        str(comfy_root),
        "--server",
        server,
        "--dry-run",
    ]
    return [
        command_record("local_preflight", preflight),
        command_record("comfy_doctor", doctor),
        command_record("qwen_preflight", qwen_preflight),
        command_record("canonical_bakeoff_dry_run", dry_run),
    ]


def recreated_smoke_plan(
    comfy_root: Path,
    server: str = DEFAULT_COMFY_SERVER,
    replace_existing_run: bool = False,
) -> list[dict]:
    launch_dir = DEFAULT_LAUNCHPAD_DIR
    preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_local_preflight.py"),
        "--preset",
        "recreated_smoke_1",
        "--comfy-root",
        str(comfy_root),
        "--out",
        str(launch_dir / "recreated_smoke_1_preflight.json"),
    ]
    doctor = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_comfy_doctor.py"),
        "--server",
        server,
        "--out",
        str(launch_dir / "recreated_smoke_1_comfy_doctor.json"),
    ]
    qwen_preflight = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_qwen_preflight.py"),
        str(QWEN_WORKFLOW),
        "--comfy-root",
        str(comfy_root),
        "--require-model-files",
        "--out",
        str(launch_dir / "recreated_smoke_1_qwen_preflight.json"),
    ]
    bakeoff = [
        sys.executable,
        str(ROOT / "tools/texture_lab/oa_tex_ai_bakeoff.py"),
        "recreated",
        "--preset",
        "recreated_smoke_1",
        "--comfy-root",
        str(comfy_root),
        "--server",
        server,
    ]
    if replace_existing_run:
        bakeoff.append("--replace-existing-run")
    return [
        command_record("local_preflight", preflight),
        command_record("comfy_doctor", doctor),
        command_record("qwen_preflight", qwen_preflight),
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


def classify_restored_smoke_1_state(
    plan_present: bool,
    evidence_status: str | None,
    manual_status: str | None,
    receipt_status: str | None,
) -> dict:
    if not plan_present:
        return {
            "state": "NOT_EXECUTED",
            "next_action": (
                "python tools/texture_lab/oa_tex_first_run.py "
                "check-restored-smoke-1"
            ),
        }
    if evidence_status != "PASS":
        return {
            "state": "EVIDENCE_HOLD",
            "next_action": (
                "inspect .local/texture_lab/runs/rt_poc_01/"
                "restored_smoke_1/run_summary.md and repair/re-run the stage"
            ),
        }
    if manual_status == "MISSING":
        return {
            "state": "READY_FOR_MANUAL_REVIEW",
            "next_action": (
                "python tools/texture_lab/oa_tex_manual_review.py "
                "init restored_smoke_1"
            ),
        }
    if manual_status == "STALE":
        return {
            "state": "MANUAL_REVIEW_STALE",
            "next_action": (
                "restart the structured review only after inspecting the "
                "new current review evidence"
            ),
        }
    if manual_status != "PASS":
        return {
            "state": "MANUAL_REVIEW_IN_PROGRESS",
            "next_action": (
                "complete all required CORIROCK checks, then run "
                "oa_tex_manual_review.py status restored_smoke_1"
            ),
        }
    if receipt_status == "PASS":
        return {
            "state": "STAGE_APPROVED",
            "next_action": (
                "capture the non-promoting Real-ESRGAN runtime lock candidate "
                "with oa_tex_realesrgan_lock.py, then restored_smoke_4 is "
                "eligible to begin; production selection remains a separate "
                "manual decision"
            ),
        }
    if receipt_status == "STALE":
        return {
            "state": "APPROVAL_STALE",
            "next_action": (
                "re-approve restored_smoke_1 only after confirming the "
                "current PASS manual review"
            ),
        }
    return {
        "state": "READY_FOR_STAGE_APPROVAL",
        "next_action": (
            "python tools/texture_lab/oa_tex_stage_gate.py approve "
            "restored_smoke_1 --note \"structured manual review PASS\""
        ),
    }


def build_restored_smoke_1_state() -> dict:
    from oa_tex_manual_review import validate_manual_review
    from oa_tex_stage_gate import (
        DEFAULT_APPROVAL_ROOT,
        DEFAULT_MANUAL_REVIEW_ROOT,
        DEFAULT_RUN_ROOT,
        evidence_snapshot,
        validate_receipt,
    )

    preset = "restored_smoke_1"
    run_dir = DEFAULT_RUN_ROOT / preset
    plan_path = run_dir / "restored_plan.json"
    plan_present = plan_path.is_file()

    evidence = (
        evidence_snapshot(preset, DEFAULT_RUN_ROOT)
        if plan_present
        else {"status": "MISSING"}
    )
    manual = (
        validate_manual_review(
            preset,
            DEFAULT_RUN_ROOT,
            DEFAULT_MANUAL_REVIEW_ROOT,
        )
        if evidence.get("status") == "PASS"
        else {"status": "NOT_CHECKED"}
    )
    receipt = (
        validate_receipt(
            preset,
            DEFAULT_RUN_ROOT,
            DEFAULT_APPROVAL_ROOT,
            DEFAULT_MANUAL_REVIEW_ROOT,
        )
        if manual.get("status") == "PASS"
        else {"status": "NOT_CHECKED"}
    )

    classified = classify_restored_smoke_1_state(
        plan_present,
        str(evidence.get("status")),
        str(manual.get("status")),
        str(receipt.get("status")),
    )
    return {
        "schema": "openazrael.texture_lab.first_restored_smoke_state.v1",
        "preset": preset,
        **classified,
        "plan_path": str(plan_path),
        "plan_present": plan_present,
        "evidence": evidence,
        "manual_review": manual,
        "stage_approval": receipt,
        "automatic_action": False,
        "production_selection_implied": False,
    }


def classify_recreated_smoke_1_state(
    plan_present: bool,
    evidence_status: str | None,
    manual_status: str | None,
    receipt_status: str | None,
) -> dict:
    if not plan_present:
        return {
            "state": "NOT_EXECUTED",
            "next_action": (
                "python tools/texture_lab/oa_tex_first_run.py "
                "check-recreated-smoke-1 --comfy-root <COMFYUI_ROOT>"
            ),
        }
    if evidence_status != "PASS":
        return {
            "state": "EVIDENCE_HOLD",
            "next_action": (
                "inspect .local/texture_lab/runs/rt_poc_01/"
                "recreated_smoke_1/run_summary.md and repair/re-run the stage"
            ),
        }
    if manual_status == "MISSING":
        return {
            "state": "READY_FOR_MANUAL_REVIEW",
            "next_action": (
                "python tools/texture_lab/oa_tex_manual_review.py "
                "init recreated_smoke_1"
            ),
        }
    if manual_status == "STALE":
        return {
            "state": "MANUAL_REVIEW_STALE",
            "next_action": (
                "restart the structured review only after inspecting the "
                "new current Recreated review evidence"
            ),
        }
    if manual_status != "PASS":
        return {
            "state": "MANUAL_REVIEW_IN_PROGRESS",
            "next_action": (
                "complete all required Recreated checks, then run "
                "oa_tex_manual_review.py status recreated_smoke_1"
            ),
        }
    if receipt_status == "PASS":
        return {
            "state": "STAGE_APPROVED",
            "next_action": (
                "recreated_smoke_4 is now eligible to begin; production "
                "selection remains a separate manual decision"
            ),
        }
    if receipt_status == "STALE":
        return {
            "state": "APPROVAL_STALE",
            "next_action": (
                "re-approve recreated_smoke_1 only after confirming the "
                "current PASS manual review"
            ),
        }
    return {
        "state": "READY_FOR_STAGE_APPROVAL",
        "next_action": (
            "python tools/texture_lab/oa_tex_stage_gate.py approve "
            "recreated_smoke_1 --note \"structured manual review PASS\""
        ),
    }


def build_recreated_smoke_1_state() -> dict:
    from oa_tex_manual_review import validate_manual_review
    from oa_tex_stage_gate import (
        DEFAULT_APPROVAL_ROOT,
        DEFAULT_MANUAL_REVIEW_ROOT,
        DEFAULT_RUN_ROOT,
        evidence_snapshot,
        validate_receipt,
    )

    preset = "recreated_smoke_1"
    run_dir = DEFAULT_RUN_ROOT / preset
    plan_path = run_dir / "recreated_plan.json"
    plan_present = plan_path.is_file()

    evidence = (
        evidence_snapshot(preset, DEFAULT_RUN_ROOT)
        if plan_present
        else {"status": "MISSING"}
    )
    manual = (
        validate_manual_review(
            preset,
            DEFAULT_RUN_ROOT,
            DEFAULT_MANUAL_REVIEW_ROOT,
        )
        if evidence.get("status") == "PASS"
        else {"status": "NOT_CHECKED"}
    )
    receipt = (
        validate_receipt(
            preset,
            DEFAULT_RUN_ROOT,
            DEFAULT_APPROVAL_ROOT,
            DEFAULT_MANUAL_REVIEW_ROOT,
        )
        if manual.get("status") == "PASS"
        else {"status": "NOT_CHECKED"}
    )
    classified = classify_recreated_smoke_1_state(
        plan_present,
        str(evidence.get("status")),
        str(manual.get("status")),
        str(receipt.get("status")),
    )
    return {
        "schema": "openazrael.texture_lab.first_recreated_smoke_state.v1",
        "preset": preset,
        **classified,
        "plan_path": str(plan_path),
        "plan_present": plan_present,
        "evidence": evidence,
        "manual_review": manual,
        "stage_approval": receipt,
        "automatic_action": False,
        "production_selection_implied": False,
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
            "check-restored-smoke-1",
            "restored-smoke-1-status",
            "restored-smoke-1",
            "check-recreated-smoke-1",
            "recreated-smoke-1-status",
            "recreated-smoke-1",
        ],
    )
    parser.add_argument(
        "--comfy-root",
        type=Path,
        default=None,
        help="ComfyUI root containing the pinned Qwen model files.",
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_COMFY_SERVER,
        help="ComfyUI HTTP API base URL.",
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=DEFAULT_RUNTIME,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace-existing-run",
        action="store_true",
        help=(
            "For a real first-smoke command only: explicitly clear that "
            "preset's local run evidence and preset-scoped candidates before "
            "a clean rerun."
        ),
    )
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
        default=None,
    )
    args = parser.parse_args()

    runtime_dir = args.runtime_dir.resolve()

    if args.command == "status":
        target = args.out or DEFAULT_LAUNCHPAD_DIR / "status.json"
        payload = build_status(runtime_dir)
        write_json(target, payload)
        state = "PASS" if payload["source_ready_for_smoke_preflight"] else "HOLD"
        print(
            f"{state} launchpad_status blockers="
            + (",".join(payload["blockers"]) if payload["blockers"] else "none")
            + f" report={target}"
        )
        return 0 if state == "PASS" else 1

    if args.command == "restored-smoke-1-status":
        target = (
            args.out
            or DEFAULT_LAUNCHPAD_DIR / "restored-smoke-1-status.json"
        )
        payload = build_restored_smoke_1_state()
        write_json(target, payload)
        print(
            f"{payload['state']} restored_smoke_1_status "
            f"next={payload['next_action']} report={target}"
        )
        return 0

    if args.command == "recreated-smoke-1-status":
        target = (
            args.out
            or DEFAULT_LAUNCHPAD_DIR / "recreated-smoke-1-status.json"
        )
        payload = build_recreated_smoke_1_state()
        write_json(target, payload)
        print(
            f"{payload['state']} recreated_smoke_1_status "
            f"next={payload['next_action']} report={target}"
        )
        return 0

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
    elif args.command == "check-recreated-smoke-1":
        if args.replace_existing_run:
            print(
                "HOLD check-recreated-smoke-1: --replace-existing-run is "
                "not valid for the non-generating readiness gate"
            )
            return 1
        if args.comfy_root is None:
            print(
                "HOLD check-recreated-smoke-1: --comfy-root is required"
            )
            return 1
        commands = recreated_smoke_check_plan(
            args.comfy_root.resolve(),
            args.server,
        )
    elif args.command == "recreated-smoke-1":
        if args.comfy_root is None:
            print("HOLD recreated-smoke-1: --comfy-root is required")
            return 1
        commands = recreated_smoke_plan(
            args.comfy_root.resolve(),
            args.server,
            replace_existing_run=args.replace_existing_run,
        )
    elif args.command == "check-restored-smoke-1":
        if args.replace_existing_run:
            print(
                "HOLD check-restored-smoke-1: --replace-existing-run is "
                "not valid for the non-generating readiness gate"
            )
            return 1
        status = build_status(runtime_dir)
        if not status["source_ready_for_smoke_preflight"]:
            target = (
                args.out
                or DEFAULT_LAUNCHPAD_DIR / "check-restored-smoke-1.json"
            )
            write_json(target, status)
            print(
                "HOLD check-restored-smoke-1 source prerequisites: "
                + ",".join(status["blockers"])
                + f" report={target}"
            )
            return 1
        commands = restored_smoke_check_plan(runtime_dir)
    else:
        status = build_status(runtime_dir)
        if not args.dry_run and not status["source_ready_for_smoke_preflight"]:
            target = (
                args.out
                or DEFAULT_LAUNCHPAD_DIR / "restored-smoke-1.json"
            )
            write_json(target, status)
            print(
                "HOLD restored-smoke-1 source prerequisites: "
                + ",".join(status["blockers"])
                + f" report={target}"
            )
            return 1
        commands = restored_smoke_plan(
            runtime_dir,
            replace_existing_run=args.replace_existing_run,
        )

    rc, results = run_commands(commands, args.dry_run)
    report = write_launch_report(args.command, runtime_dir, results, rc)
    print(
        f"{'PASS' if rc == 0 else 'HOLD'} launchpad command={args.command} report={report}"
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
