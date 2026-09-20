#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.error
import urllib.request

from common import ROOT, write_json

CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
DEFAULT_REPORT = ROOT / ".local/texture_lab/qwen_2511_bootstrap.json"
DISK_SAFETY_BYTES = 5 * 1024 ** 3
CHUNK_BYTES = 8 * 1024 ** 2


def load_contract(path: Path = CONTRACT) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(path: Path, spec: dict) -> dict:
    expected_size = int(spec["size_bytes"])
    expected_sha = str(spec["sha256"]).lower()
    if not path.is_file():
        return {
            "status": "MISSING",
            "path": str(path),
            "expected_size_bytes": expected_size,
            "expected_sha256": expected_sha,
        }

    size = path.stat().st_size
    if size != expected_size:
        return {
            "status": "FAIL",
            "path": str(path),
            "size_bytes": size,
            "expected_size_bytes": expected_size,
            "size_ok": False,
            "sha256": None,
            "expected_sha256": expected_sha,
            "sha256_ok": False,
        }

    actual_sha = sha256_file(path).lower()
    return {
        "status": "PASS" if actual_sha == expected_sha else "FAIL",
        "path": str(path),
        "size_bytes": size,
        "expected_size_bytes": expected_size,
        "size_ok": True,
        "sha256": actual_sha,
        "expected_sha256": expected_sha,
        "sha256_ok": actual_sha == expected_sha,
    }


def selected_specs(contract: dict, roles: list[str] | None) -> list[tuple[str, dict]]:
    required = contract.get("required_models", {})
    if roles is None:
        return [(str(role), dict(spec)) for role, spec in required.items()]

    unknown = sorted(set(roles) - set(required))
    if unknown:
        raise SystemExit("unknown required Qwen model role(s): " + ", ".join(unknown))
    return [(role, dict(required[role])) for role in roles]


def destination_for(comfy_root: Path, spec: dict) -> Path:
    return comfy_root / str(spec["relative_path"])


def build_plan(
    comfy_root: Path,
    contract: dict,
    roles: list[str] | None = None,
) -> dict:
    rows = []
    download_bytes = 0
    for role, spec in selected_specs(contract, roles):
        destination = destination_for(comfy_root, spec)
        verification = verify_model(destination, spec)
        if verification["status"] != "PASS":
            download_bytes += int(spec["size_bytes"])
        rows.append(
            {
                "role": role,
                "destination": str(destination),
                "source_repo": spec.get("source_repo"),
                "source_path": spec.get("source_path"),
                "download_url": spec.get("download_url"),
                "verification": verification,
            }
        )

    probe = comfy_root.resolve()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    disk = shutil.disk_usage(probe)
    required_free = download_bytes + DISK_SAFETY_BYTES
    return {
        "schema": "openazrael.texture_lab.qwen_bootstrap_plan.v1",
        "comfy_root": str(comfy_root),
        "models": rows,
        "download_bytes": download_bytes,
        "disk_safety_bytes": DISK_SAFETY_BYTES,
        "required_free_bytes": required_free,
        "disk_free_bytes": disk.free,
        "disk_capacity_ok": disk.free >= required_free,
        "all_models_ready": all(
            row["verification"]["status"] == "PASS" for row in rows
        ),
    }


def _request(url: str, start: int, token: str | None):
    headers = {"User-Agent": "OpenAzrael-TextureLab/RT-POC-01"}
    if start > 0:
        headers["Range"] = f"bytes={start}-"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers, method="GET")


def download_resumable(
    url: str,
    destination: Path,
    expected_size: int,
    token: str | None = None,
) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")

    if partial.is_file() and partial.stat().st_size > expected_size:
        raise SystemExit(
            f"partial file is larger than expected; remove it before retrying: {partial}"
        )

    start = partial.stat().st_size if partial.is_file() else 0
    request = _request(url, start, token)

    try:
        response = urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and start == expected_size:
            return {
                "partial": str(partial),
                "resumed_from_bytes": start,
                "downloaded_bytes": 0,
                "http_status": 416,
            }
        raise

    status = int(getattr(response, "status", response.getcode()))
    if start > 0 and status != 206:
        # The server ignored Range. Restart rather than append a second copy.
        start = 0
        mode = "wb"
    else:
        mode = "ab" if start > 0 else "wb"

    downloaded = 0
    with response, partial.open(mode) as out:
        while True:
            chunk = response.read(CHUNK_BYTES)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)

    actual_size = partial.stat().st_size
    if actual_size != expected_size:
        raise SystemExit(
            f"incomplete Qwen model download: {partial} "
            f"size={actual_size} expected={expected_size}; rerun to resume"
        )

    return {
        "partial": str(partial),
        "resumed_from_bytes": start,
        "downloaded_bytes": downloaded,
        "http_status": status,
    }


def finalize_download(partial: Path, destination: Path, spec: dict) -> dict:
    verification = verify_model(partial, spec)
    if verification["status"] != "PASS":
        raise SystemExit(
            f"downloaded Qwen model failed identity verification: {partial}"
        )
    partial.replace(destination)
    return verify_model(destination, spec)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, resumably download and cryptographically verify the pinned "
            "OpenAzrael Qwen-Image-Edit-2511 ComfyUI model set."
        )
    )
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument(
        "--roles",
        nargs="+",
        default=None,
        choices=["diffusion", "text_encoder", "vae"],
        help="Optional subset. Default is all required Qwen models.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download missing/invalid required files. Otherwise verify/plan only.",
    )
    parser.add_argument(
        "--replace-invalid",
        action="store_true",
        help=(
            "Permit replacement of an existing final model file whose pinned "
            "size/hash verification fails. Without this flag, invalid final "
            "files are never overwritten."
        ),
    )
    parser.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="Environment variable containing an optional Hugging Face token.",
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    contract = load_contract(args.contract)
    comfy_root = args.comfy_root.resolve()
    plan = build_plan(comfy_root, contract, args.roles)

    actions = []
    if args.download:
        if not plan["disk_capacity_ok"]:
            write_json(args.report, {**plan, "status": "HOLD_DISK"})
            raise SystemExit(
                "insufficient free disk space for missing Qwen models plus 5 GiB safety margin"
            )

        token = os.environ.get(args.token_env)
        for role, spec in selected_specs(contract, args.roles):
            destination = destination_for(comfy_root, spec)
            before = verify_model(destination, spec)
            if before["status"] == "PASS":
                actions.append(
                    {
                        "role": role,
                        "action": "SKIP_ALREADY_VERIFIED",
                        "verification": before,
                    }
                )
                continue

            if destination.exists():
                if not args.replace_invalid:
                    write_json(
                        args.report,
                        {
                            **plan,
                            "status": "HOLD_INVALID_EXISTING_FILE",
                            "blocked_role": role,
                            "blocked_path": str(destination),
                            "actions": actions,
                        },
                    )
                    raise SystemExit(
                        f"existing Qwen model is invalid and will not be overwritten: "
                        f"{destination}; inspect/remove it or rerun with --replace-invalid"
                    )
                invalid = destination.with_name(destination.name + ".invalid")
                if invalid.exists():
                    invalid.unlink()
                destination.replace(invalid)

            url = spec.get("download_url")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise SystemExit(f"pinned HTTPS download URL missing for Qwen role={role}")

            transfer = download_resumable(
                url,
                destination,
                int(spec["size_bytes"]),
                token,
            )
            partial = Path(transfer["partial"])
            final_verification = finalize_download(partial, destination, spec)
            actions.append(
                {
                    "role": role,
                    "action": "DOWNLOADED_AND_VERIFIED",
                    "transfer": transfer,
                    "verification": final_verification,
                }
            )

    final_plan = build_plan(comfy_root, contract, args.roles)
    ready = final_plan["all_models_ready"]
    report = {
        "schema": "openazrael.texture_lab.qwen_bootstrap.v1",
        "status": "PASS" if ready else ("PLAN_ONLY" if not args.download else "HOLD"),
        "download_requested": bool(args.download),
        "replace_invalid": bool(args.replace_invalid),
        "token_env": args.token_env,
        "plan": final_plan,
        "actions": actions,
        "qwen_preflight_still_required": True,
    }
    write_json(args.report, report)

    if ready:
        print(
            f"PASS Qwen model bootstrap roles={len(final_plan['models'])} "
            f"report={args.report}"
        )
        return 0

    print(
        f"PLAN Qwen model bootstrap missing_bytes={final_plan['download_bytes']} "
        f"disk_ok={final_plan['disk_capacity_ok']} report={args.report}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
