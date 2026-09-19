#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from common import ROOT, write_json

CONTRACT_PATH = ROOT / "tools/texture_lab/config/realesrgan_runtime_contract.json"


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def probe_code(require_basicsr: bool, require_realesrgan: bool) -> str:
    lines = [
        "import json, sys",
        "payload = {'python_major_minor': f'{sys.version_info.major}.{sys.version_info.minor}'}",
        "try:",
        " import torch",
        " payload['torch'] = getattr(torch, '__version__', 'unknown').split('+', 1)[0]",
        " payload['cuda_available'] = bool(torch.cuda.is_available())",
        " payload['cuda_version'] = getattr(torch.version, 'cuda', None)",
        "except Exception as exc:",
        " payload['torch_error'] = f'{type(exc).__name__}: {exc}'",
        "try:",
        " import torchvision",
        " payload['torchvision'] = getattr(torchvision, '__version__', 'unknown').split('+', 1)[0]",
        " try:",
        "  from torchvision.transforms.functional_tensor import rgb_to_grayscale as _rgb_to_grayscale",
        "  payload['functional_tensor_import'] = True",
        " except Exception as exc:",
        "  payload['functional_tensor_import'] = False",
        "  payload['functional_tensor_error'] = f'{type(exc).__name__}: {exc}'",
        "except Exception as exc:",
        " payload['torchvision_error'] = f'{type(exc).__name__}: {exc}'",
    ]
    if require_basicsr:
        lines.extend([
            "try:",
            " import basicsr",
            " payload['basicsr'] = getattr(basicsr, '__version__', 'unknown')",
            "except Exception as exc:",
            " payload['basicsr_error'] = f'{type(exc).__name__}: {exc}'",
        ])
    if require_realesrgan:
        lines.extend([
            "try:",
            " import realesrgan",
            " payload['realesrgan'] = getattr(realesrgan, '__version__', 'unknown')",
            "except Exception as exc:",
            " payload['realesrgan_error'] = f'{type(exc).__name__}: {exc}'",
        ])
    lines.append("print(json.dumps(payload, sort_keys=True))")
    return "\n".join(lines)


def evaluate_probe(
    payload: dict,
    contract: dict,
    require_basicsr: bool,
    require_realesrgan: bool,
) -> dict:
    packages = contract["packages"]
    checks = {
        "python_ok": payload.get("python_major_minor")
        == str(contract["python"]["major_minor"]),
        "torch_ok": payload.get("torch")
        == str(packages["torch"]["version"]),
        "torchvision_ok": payload.get("torchvision")
        == str(packages["torchvision"]["version"]),
        "functional_tensor_ok": payload.get("functional_tensor_import") is True,
    }
    if require_basicsr:
        checks["basicsr_ok"] = payload.get("basicsr") == str(
            packages["basicsr"]["version"]
        )
    if require_realesrgan:
        checks["realesrgan_import_ok"] = (
            isinstance(payload.get("realesrgan"), str)
            and payload.get("realesrgan") not in {"", "unknown"}
        )
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "observed": payload,
        "expected": {
            "python_major_minor": contract["python"]["major_minor"],
            "torch": packages["torch"]["version"],
            "torchvision": packages["torchvision"]["version"],
            "basicsr": packages["basicsr"]["version"] if require_basicsr else None,
            "functional_tensor_import": True,
            "realesrgan_import": True if require_realesrgan else None,
        },
    }


def probe_python(
    python_exe: str | Path,
    contract: dict,
    require_basicsr: bool = False,
    require_realesrgan: bool = False,
) -> dict:
    argv = [
        str(python_exe),
        "-c",
        probe_code(require_basicsr, require_realesrgan),
    ]
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "status": "FAIL",
            "checks": {"probe_process_ok": False},
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        payload = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL",
            "checks": {"probe_json_ok": False},
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "error": f"{type(exc).__name__}: {exc}",
        }
    result = evaluate_probe(
        payload,
        contract,
        require_basicsr,
        require_realesrgan,
    )
    result["argv"] = argv
    return result


def pip_freeze_snapshot(python_exe: str | Path) -> dict:
    argv = [str(python_exe), "-m", "pip", "freeze", "--all"]
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "status": "FAIL",
            "argv": argv,
            "returncode": completed.returncode,
            "stderr": completed.stderr,
        }
    lines = sorted(
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    )
    normalized = "\n".join(lines) + ("\n" if lines else "")
    return {
        "status": "PASS",
        "packages": lines,
        "package_count": len(lines),
        "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the pinned OpenAzrael Real-ESRGAN texture-only Python runtime."
    )
    parser.add_argument("command", choices=["check", "freeze"])
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--require-basicsr", action="store_true")
    parser.add_argument("--require-realesrgan", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "check":
        result = probe_python(
            args.python_exe,
            load_contract(),
            args.require_basicsr,
            args.require_realesrgan,
        )
    else:
        result = pip_freeze_snapshot(args.python_exe)

    if args.out:
        write_json(args.out, result)
    print(
        f"{result.get('status', 'FAIL')} realesrgan_runtime "
        f"command={args.command} python={args.python_exe}"
    )
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
