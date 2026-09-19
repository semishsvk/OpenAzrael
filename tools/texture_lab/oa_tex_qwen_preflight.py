#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

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

    classes = {}
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        cls = str(node.get("class_type", ""))
        if cls:
            classes.setdefault(cls, []).append(str(node_id))

    required = {
        cls: classes.get(cls, [])
        for cls in contract["required_nodes"]
    }
    missing_classes = [cls for cls, ids in required.items() if not ids]

    load_images = class_nodes(workflow, "LoadImage")
    prompt_nodes = class_nodes(workflow, "TextEncodeQwenImageEditPlus")
    samplers = class_nodes(workflow, "KSampler")
    unets = class_nodes(workflow, "UNETLoader")
    clips = class_nodes(workflow, "CLIPLoader")
    vaes = class_nodes(workflow, "VAELoader")

    positive = [
        {"node": node_id, "title": title(node)}
        for node_id, node in prompt_nodes
        if "positive" in title(node).lower()
    ]
    negative = [
        {"node": node_id, "title": title(node)}
        for node_id, node in prompt_nodes
        if "negative" in title(node).lower()
    ]

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
            }
        )

    return {
        "node_count": len(workflow),
        "classes": classes,
        "required_node_ids": required,
        "missing_required_classes": missing_classes,
        "load_image_nodes": [
            {"node": node_id, "title": title(node)}
            for node_id, node in load_images
        ],
        "positive_prompt_candidates": positive,
        "negative_prompt_candidates": negative,
        "all_prompt_nodes": [
            {"node": node_id, "title": title(node)}
            for node_id, node in prompt_nodes
        ],
        "samplers": sampler_rows,
        "unet_loaders": model_name_from(unets, ["unet_name", "model_name"]),
        "clip_loaders": model_name_from(clips, ["clip_name"]),
        "vae_loaders": model_name_from(vaes, ["vae_name"]),
    }


def exact_loader_check(inspection: dict, contract: dict) -> dict:
    expected = contract["required_models"]
    checks = {}

    def values(key: str) -> list[str]:
        return [
            str(row["value"])
            for row in inspection[key]
            if row.get("value") is not None
        ]

    checks["diffusion_filename_ok"] = expected["diffusion"]["filename"] in values("unet_loaders")
    checks["text_encoder_filename_ok"] = expected["text_encoder"]["filename"] in values("clip_loaders")
    checks["vae_filename_ok"] = expected["vae"]["filename"] in values("vae_loaders")
    return checks


def node_binding_check(
    workflow: dict,
    load_image_node: str | None,
    prompt_node: str | None,
    negative_prompt_node: str | None,
    seed_node: str | None,
) -> dict:
    checks = {}
    for label, node_id, expected_class in [
        ("load_image_node", load_image_node, "LoadImage"),
        ("prompt_node", prompt_node, "TextEncodeQwenImageEditPlus"),
        ("negative_prompt_node", negative_prompt_node, "TextEncodeQwenImageEditPlus"),
        ("seed_node", seed_node, "KSampler"),
    ]:
        if node_id is None:
            checks[label] = {"status": "UNBOUND"}
            continue
        node = workflow.get(str(node_id))
        checks[label] = {
            "status": "PASS" if (
                isinstance(node, dict) and node.get("class_type") == expected_class
            ) else "FAIL",
            "node": str(node_id),
            "expected_class": expected_class,
            "actual_class": node.get("class_type") if isinstance(node, dict) else None,
        }
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight an exported ComfyUI API workflow for OpenAzrael Qwen-Image-Edit-2511."
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
    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    inspection = inspect_workflow(workflow, contract)
    loader_checks = exact_loader_check(inspection, contract)
    binding_checks = node_binding_check(
        workflow,
        args.load_image_node,
        args.prompt_node,
        args.negative_prompt_node,
        args.seed_node,
    )

    structural_checks = {
        "required_classes_ok": not inspection["missing_required_classes"],
        "single_primary_load_image_ok": (
            len(inspection["load_image_nodes"]) == 1
            if contract["api_workflow_policy"]["single_primary_load_image"]
            else len(inspection["load_image_nodes"]) >= 1
        ),
        "at_least_two_prompt_nodes_ok": len(inspection["all_prompt_nodes"]) >= 2,
        "single_ksampler_ok": len(inspection["samplers"]) == 1,
        **loader_checks,
    }

    model_files = {}
    if args.comfy_root is not None:
        for role, spec in contract["required_models"].items():
            model_files[role] = verify_model_file(args.comfy_root, spec)

    bindings_ok = all(
        row["status"] == "PASS"
        for row in binding_checks.values()
    ) if all(
        value is not None
        for value in [
            args.load_image_node,
            args.prompt_node,
            args.negative_prompt_node,
            args.seed_node,
        ]
    ) else False

    model_files_ok = (
        all(row["status"] == "PASS" for row in model_files.values())
        if model_files
        else not args.require_model_files
    )

    ready = (
        all(structural_checks.values())
        and bindings_ok
        and model_files_ok
    )

    report = {
        "schema": "openazrael.texture_lab.qwen_2511_preflight.v1",
        "workflow": str(args.workflow),
        "workflow_sha256": sha256_file(args.workflow),
        "official_template_reference": contract["official_template"],
        "inspection": inspection,
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
