#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from common import ROOT, write_json

CONTRACT_PATH = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def class_nodes(workflow: dict, class_type: str) -> list[tuple[str, dict]]:
    return [
        (str(node_id), node)
        for node_id, node in workflow.items()
        if isinstance(node, dict) and str(node.get("class_type", "")) == class_type
    ]


def title(node: dict) -> str:
    meta = node.get("_meta") if isinstance(node.get("_meta"), dict) else {}
    return str(meta.get("title", "")).strip()


def model_name_from(nodes: list[tuple[str, dict]], keys: list[str]) -> list[dict]:
    rows = []
    for node_id, node in nodes:
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        found = None
        found_key = None
        for key in keys:
            value = inputs.get(key)
            if isinstance(value, str):
                found = value
                found_key = key
                break
        rows.append({"node": node_id, "title": title(node), "key": found_key, "value": found})
    return rows


def verify_model_file(comfy_root: Path, spec: dict) -> dict:
    path = comfy_root / str(spec["relative_path"])
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    size = path.stat().st_size
    digest = sha256_file(path)
    return {
        "status": "PASS" if (
            size == int(spec["size_bytes"]) and digest == str(spec["sha256"])
        ) else "FAIL",
        "path": str(path),
        "size_bytes": size,
        "expected_size_bytes": int(spec["size_bytes"]),
        "sha256": digest,
        "expected_sha256": str(spec["sha256"]),
    }


def inspect_workflow(workflow: dict, contract: dict) -> dict:
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("API workflow must be a non-empty node dictionary")

    classes: dict[str, list[str]] = {}
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        cls = str(node.get("class_type", ""))
        if cls:
            classes.setdefault(cls, []).append(str(node_id))

    required = {cls: classes.get(cls, []) for cls in contract["required_nodes"]}
    missing_classes = [cls for cls, ids in required.items() if not ids]

    load_images = class_nodes(workflow, "LoadImage")
    prompt_nodes = class_nodes(workflow, "TextEncodeQwenImageEditPlus")
    samplers = class_nodes(workflow, "KSampler")
    unets = class_nodes(workflow, "UNETLoader")
    clips = class_nodes(workflow, "CLIPLoader")
    vaes = class_nodes(workflow, "VAELoader")
    loras = class_nodes(workflow, "LoraLoaderModelOnly")

    prompt_rows = []
    for node_id, node in prompt_nodes:
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        prompt_rows.append(
            {
                "node": node_id,
                "title": title(node),
                "has_image1": "image1" in inputs,
                "has_image2": "image2" in inputs,
                "has_image3": "image3" in inputs,
                "prompt_is_string": isinstance(inputs.get("prompt"), str),
            }
        )

    sampler_rows = []
    for node_id, node in samplers:
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        sampler_rows.append(
            {
                "node": node_id,
                "title": title(node),
                "seed": inputs.get("seed"),
                "steps": inputs.get("steps"),
                "cfg": inputs.get("cfg"),
                "sampler_name": inputs.get("sampler_name"),
                "scheduler": inputs.get("scheduler"),
                "denoise": inputs.get("denoise"),
            }
        )

    return {
        "node_count": len(workflow),
        "classes": classes,
        "required_node_ids": required,
        "missing_required_classes": missing_classes,
        "load_image_nodes": [{"node": node_id, "title": title(node)} for node_id, node in load_images],
        "prompt_nodes": prompt_rows,
        "samplers": sampler_rows,
        "unet_loaders": model_name_from(unets, ["unet_name", "model_name"]),
        "clip_loaders": model_name_from(clips, ["clip_name"]),
        "vae_loaders": model_name_from(vaes, ["vae_name"]),
        "lora_nodes": [{"node": node_id, "title": title(node)} for node_id, node in loras],
    }


def exact_loader_check(inspection: dict, contract: dict) -> dict:
    expected = contract["required_models"]

    def values(key: str) -> list[str]:
        return [str(row["value"]) for row in inspection[key] if row.get("value") is not None]

    return {
        "diffusion_filename_ok": expected["diffusion"]["filename"] in values("unet_loaders"),
        "text_encoder_filename_ok": expected["text_encoder"]["filename"] in values("clip_loaders"),
        "vae_filename_ok": expected["vae"]["filename"] in values("vae_loaders"),
    }


def sampling_check(inspection: dict, contract: dict) -> dict:
    if len(inspection["samplers"]) != 1:
        return {"status": "FAIL", "reason": "expected exactly one KSampler"}
    actual = inspection["samplers"][0]
    expected = contract["poc_sampling"]
    checks = {
        "seed": actual["seed"] == int(expected["seed"]),
        "steps": actual["steps"] == int(expected["steps"]),
        "cfg": float(actual["cfg"]) == float(expected["cfg"]) if isinstance(actual["cfg"], (int, float)) else False,
        "sampler": actual["sampler_name"] == expected["sampler"],
        "scheduler": actual["scheduler"] == expected["scheduler"],
        "denoise": float(actual["denoise"]) == 1.0 if isinstance(actual["denoise"], (int, float)) else False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "actual": actual,
        "expected": expected,
    }


def node_binding_check(
    workflow: dict,
    load_image_node: str,
    prompt_node: str,
    negative_prompt_node: str,
    seed_node: str,
) -> dict:
    checks = {}
    for label, node_id, expected_class in [
        ("load_image_node", load_image_node, "LoadImage"),
        ("prompt_node", prompt_node, "TextEncodeQwenImageEditPlus"),
        ("negative_prompt_node", negative_prompt_node, "TextEncodeQwenImageEditPlus"),
        ("seed_node", seed_node, "KSampler"),
    ]:
        node = workflow.get(str(node_id))
        checks[label] = {
            "status": "PASS" if (
                isinstance(node, dict) and node.get("class_type") == expected_class
            ) else "FAIL",
            "node": str(node_id),
            "expected_class": expected_class,
            "actual_class": node.get("class_type") if isinstance(node, dict) else None,
        }
    checks["positive_negative_are_distinct"] = {
        "status": "PASS" if str(prompt_node) != str(negative_prompt_node) else "FAIL"
    }
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight an API-format ComfyUI workflow for OpenAzrael Qwen-Image-Edit-2511."
    )
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--comfy-root", type=Path, default=None)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--load-image-node", default=None)
    parser.add_argument("--prompt-node", default=None)
    parser.add_argument("--negative-prompt-node", default=None)
    parser.add_argument("--seed-node", default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--require-model-files", action="store_true")
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    bindings = contract["canonical_openazrael_workflow"]["bindings"]
    load_image_node = args.load_image_node or str(bindings["load_image_node"])
    prompt_node = args.prompt_node or str(bindings["prompt_node"])
    negative_prompt_node = args.negative_prompt_node or str(bindings["negative_prompt_node"])
    seed_node = args.seed_node or str(bindings["seed_node"])

    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    inspection = inspect_workflow(workflow, contract)
    loader_checks = exact_loader_check(inspection, contract)
    sample_check = sampling_check(inspection, contract)
    binding_checks = node_binding_check(
        workflow,
        load_image_node,
        prompt_node,
        negative_prompt_node,
        seed_node,
    )

    positive_node = workflow.get(str(prompt_node), {})
    negative_node = workflow.get(str(negative_prompt_node), {})
    pos_inputs = positive_node.get("inputs", {}) if isinstance(positive_node, dict) else {}
    neg_inputs = negative_node.get("inputs", {}) if isinstance(negative_node, dict) else {}

    structural_checks = {
        "required_classes_ok": not inspection["missing_required_classes"],
        "single_primary_load_image_ok": len(inspection["load_image_nodes"]) == 1,
        "exactly_two_prompt_nodes_ok": len(inspection["prompt_nodes"]) == 2,
        "single_ksampler_ok": len(inspection["samplers"]) == 1,
        "no_lightning_lora_ok": len(inspection["lora_nodes"]) == 0,
        "single_reference_positive_ok": (
            "image1" in pos_inputs and "image2" not in pos_inputs and "image3" not in pos_inputs
        ),
        "single_reference_negative_ok": (
            "image1" in neg_inputs and "image2" not in neg_inputs and "image3" not in neg_inputs
        ),
        "sampling_contract_ok": sample_check["status"] == "PASS",
        **loader_checks,
    }

    model_files = {}
    if args.comfy_root is not None:
        for role, spec in contract["required_models"].items():
            model_files[role] = verify_model_file(args.comfy_root, spec)

    bindings_ok = all(row["status"] == "PASS" for row in binding_checks.values())
    model_files_ok = (
        all(row["status"] == "PASS" for row in model_files.values())
        if model_files
        else not args.require_model_files
    )
    ready = all(structural_checks.values()) and bindings_ok and model_files_ok

    report = {
        "schema": "openazrael.texture_lab.qwen_2511_preflight.v2",
        "workflow": str(args.workflow),
        "workflow_sha256": sha256_file(args.workflow),
        "official_template_reference": contract["official_template"],
        "canonical_bindings": {
            "load_image_node": load_image_node,
            "prompt_node": prompt_node,
            "negative_prompt_node": negative_prompt_node,
            "seed_node": seed_node,
        },
        "inspection": inspection,
        "sampling_check": sample_check,
        "structural_checks": structural_checks,
        "binding_checks": binding_checks,
        "model_files": model_files,
        "model_files_required": bool(args.require_model_files),
        "ready_for_execution": ready,
    }

    out = args.out or args.workflow.with_suffix(".preflight.json")
    write_json(out, report)
    print(("PASS" if ready else "HOLD") + f" qwen_preflight report={out}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
