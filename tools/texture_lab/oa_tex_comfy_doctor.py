#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import urllib.error
import urllib.request

from common import ROOT, write_json

CONTRACT_PATH = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"

EXPECTED_INPUTS = {
    "LoadImage": {"image"},
    "UNETLoader": {"unet_name", "weight_dtype"},
    "CLIPLoader": {"clip_name", "type"},
    "VAELoader": {"vae_name"},
    "ModelSamplingAuraFlow": {"model", "shift"},
    "CFGNorm": {"model", "strength"},
    "TextEncodeQwenImageEditPlus": {"clip", "prompt", "vae", "image1"},
    "VAEEncode": {"pixels", "vae"},
    "KSampler": {
        "model", "seed", "steps", "cfg", "sampler_name", "scheduler",
        "positive", "negative", "latent_image", "denoise",
    },
    "VAEDecode": {"samples", "vae"},
    "SaveImage": {"images", "filename_prefix"},
}


def get_json(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def input_names(node_info: dict) -> set[str]:
    inp = node_info.get("input")
    if not isinstance(inp, dict):
        return set()
    names: set[str] = set()
    for group in ("required", "optional", "hidden"):
        values = inp.get(group)
        if isinstance(values, dict):
            names.update(str(k) for k in values.keys())
    return names


def evaluate_object_info(object_info: dict, required_classes: list[str]) -> dict:
    class_rows = {}
    for cls in required_classes:
        info = object_info.get(cls)
        if not isinstance(info, dict):
            class_rows[cls] = {
                "status": "MISSING",
                "expected_inputs": sorted(EXPECTED_INPUTS.get(cls, set())),
                "actual_inputs": [],
                "missing_inputs": sorted(EXPECTED_INPUTS.get(cls, set())),
            }
            continue

        actual = input_names(info)
        expected = EXPECTED_INPUTS.get(cls, set())
        missing = expected - actual
        class_rows[cls] = {
            "status": "PASS" if not missing else "FAIL",
            "expected_inputs": sorted(expected),
            "actual_inputs": sorted(actual),
            "missing_inputs": sorted(missing),
        }

    return {
        "classes": class_rows,
        "all_required_classes_present": all(
            row["status"] != "MISSING" for row in class_rows.values()
        ),
        "all_expected_inputs_present": all(
            row["status"] == "PASS" for row in class_rows.values()
        ),
    }


def summarize_system_stats(stats: dict) -> dict:
    system = stats.get("system") if isinstance(stats.get("system"), dict) else {}
    devices = stats.get("devices") if isinstance(stats.get("devices"), list) else []
    return {
        "os": system.get("os"),
        "python_version": system.get("python_version"),
        "embedded_python": system.get("embedded_python"),
        "pytorch_version": system.get("pytorch_version"),
        "comfyui_version": system.get("comfyui_version"),
        "required_frontend_version": system.get("required_frontend_version"),
        "devices": [
            {
                "name": row.get("name"),
                "type": row.get("type"),
                "index": row.get("index"),
                "vram_total": row.get("vram_total"),
                "vram_free": row.get("vram_free"),
                "torch_vram_total": row.get("torch_vram_total"),
                "torch_vram_free": row.get("torch_vram_free"),
            }
            for row in devices
            if isinstance(row, dict)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a running ComfyUI server exposes the node API required by OpenAzrael Qwen 2511."
    )
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/texture_lab/runs/rt_poc_01/comfy_doctor.json",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    base = args.server.rstrip("/")

    try:
        stats = get_json(base + "/system_stats", args.timeout)
        object_info = get_json(base + "/object_info", args.timeout)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        write_json(
            args.out,
            {
                "schema": "openazrael.texture_lab.comfy_doctor.v1",
                "server": base,
                "status": "HOLD",
                "ready": False,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        print(f"HOLD ComfyUI unavailable report={args.out}")
        return 1

    evaluation = evaluate_object_info(object_info, list(contract["required_nodes"]))
    ready = (
        evaluation["all_required_classes_present"]
        and evaluation["all_expected_inputs_present"]
    )
    report = {
        "schema": "openazrael.texture_lab.comfy_doctor.v1",
        "server": base,
        "status": "PASS" if ready else "HOLD",
        "ready": ready,
        "system": summarize_system_stats(stats),
        "node_contract": evaluation,
    }
    write_json(args.out, report)
    print(("PASS" if ready else "HOLD") + f" ComfyUI runtime report={args.out}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
