#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, write_json

DEFAULT_SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
DEFAULT_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"
DEFAULT_SMOKE = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"
DEFAULT_BACKENDS = ROOT / "tools/texture_lab/config/ai_backends.json"
DEFAULT_MODELS = ROOT / "tools/texture_lab/config/model_registry.json"
DEFAULT_QWEN = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
DEFAULT_REALESRGAN_RUNTIME = ROOT / "tools/texture_lab/config/realesrgan_runtime_contract.json"
DEFAULT_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
DEFAULT_POLICY_SUMMARY = ROOT / "data/texture_lab/rt_poc_01_ai_policy_summary.json"
DEFAULT_PRODUCTION_REGISTRY = ROOT / "data/texture_lab/production_selection.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def eligible_ids(selection: dict, policy: dict, key: str) -> list[str]:
    defaults = policy.get("defaults", {})
    classes = policy.get("classes", {})
    rows = []
    for entry in selection.get("textures", []):
        rules = dict(defaults)
        rules.update(classes.get(str(entry.get("content_class", "")), {}))
        if bool(rules.get(key, False)):
            rows.append(str(entry["id"]))
    return rows


def _acyclic(presets: dict) -> tuple[bool, list[str]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: list[str] = []

    def visit(name: str, stack: list[str]) -> bool:
        nonlocal cycle
        if name in visited:
            return True
        if name in visiting:
            start = stack.index(name) if name in stack else 0
            cycle = stack[start:] + [name]
            return False
        visiting.add(name)
        stack.append(name)
        for dep in presets.get(name, {}).get("requires_approval", []):
            if dep in presets and not visit(str(dep), stack):
                return False
        stack.pop()
        visiting.remove(name)
        visited.add(name)
        return True

    ok = all(visit(name, []) for name in presets)
    return ok, cycle


def validate_contracts(
    selection: dict,
    policy: dict,
    smoke: dict,
    backends: dict,
    models: dict,
    qwen: dict,
    workflow: dict,
    policy_summary: dict,
    realesrgan_runtime: dict | None = None,
    production_registry: dict | None = None,
) -> dict:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    if realesrgan_runtime is None:
        realesrgan_runtime = load_json(DEFAULT_REALESRGAN_RUNTIME)
    if production_registry is None:
        production_registry = load_json(DEFAULT_PRODUCTION_REGISTRY)

    checks["production_registry_schema_v2"] = (
        production_registry.get("schema")
        == "openazrael.texture_lab.production_selection.v2"
    )
    checks["production_registry_manual_only"] = (
        production_registry.get("automatic_selection") is False
    )
    checks["production_registry_remastered_profile"] = isinstance(
        production_registry.get("profiles", {}).get("remastered"),
        dict,
    )
    checks["production_registry_history_lists"] = (
        isinstance(production_registry.get("superseded_selections"), list)
        and isinstance(production_registry.get("revocations"), list)
    )

    textures = [
        row for row in selection.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    ]
    ids = [str(row["id"]) for row in textures]
    classes = policy.get("classes", {})

    checks["selection_schema"] = (
        selection.get("schema") == "openazrael.texture_lab.rt_poc_01_selection.v1"
    )
    checks["selection_count_12"] = len(textures) == 12
    checks["selection_ids_unique"] = len(ids) == len(set(ids))
    checks["selection_dimensions_valid"] = all(
        isinstance(row.get("expected_size"), list)
        and len(row["expected_size"]) == 2
        and all(isinstance(v, int) and v > 0 for v in row["expected_size"])
        for row in textures
    )
    checks["selection_classes_have_policy"] = all(
        str(row.get("content_class", "")) in classes for row in textures
    )
    checks["selection_no_automatic_winner"] = selection.get("automatic_winner") is False

    defaults = policy.get("defaults", {})
    checks["policy_schema"] = (
        policy.get("schema") == "openazrael.texture_lab.ai_review_policy.v1"
    )
    checks["policy_manual_review_default"] = defaults.get("manual_visual_review") is True
    checks["policy_no_auto_promotion"] = (
        defaults.get("automatic_production_promotion") is False
    )

    restored = eligible_ids(selection, policy, "ai_restored")
    recreated = eligible_ids(selection, policy, "ai_recreated")
    details["eligible_restored"] = restored
    details["eligible_recreated"] = recreated

    presets = smoke.get("presets", {})
    checks["smoke_schema"] = (
        smoke.get("schema") == "openazrael.texture_lab.ai_smoke_sets.v2"
    )
    checks["all_preset_texture_ids_known"] = all(
        str(texture_id) in set(ids)
        for preset in presets.values()
        if isinstance(preset, dict)
        for texture_id in preset.get("textures", [])
    )
    checks["all_prerequisites_exist"] = all(
        str(dep) in presets
        for preset in presets.values()
        if isinstance(preset, dict)
        for dep in preset.get("requires_approval", [])
    )
    dag_ok, cycle = _acyclic(presets)
    checks["approval_graph_acyclic"] = dag_ok
    details["approval_cycle"] = cycle

    order = [str(value) for value in smoke.get("recommended_order", [])]
    checks["recommended_order_exactly_all_presets"] = (
        len(order) == len(presets)
        and len(order) == len(set(order))
        and set(order) == set(presets)
    )
    position = {name: index for index, name in enumerate(order)}
    checks["recommended_order_respects_dependencies"] = all(
        position.get(str(dep), 10**9) < position.get(name, -1)
        for name, preset in presets.items()
        if isinstance(preset, dict)
        for dep in preset.get("requires_approval", [])
    )

    restored_full = presets.get("restored_full", {})
    recreated_full = presets.get("recreated_full", {})
    checks["restored_full_matches_policy_eligibility"] = (
        restored_full.get("mode") == "restored"
        and [str(v) for v in restored_full.get("textures", [])] == restored
    )
    checks["recreated_full_matches_policy_eligibility"] = (
        recreated_full.get("mode") == "recreated"
        and [str(v) for v in recreated_full.get("textures", [])] == recreated
    )

    for preset_name, preset in presets.items():
        if not isinstance(preset, dict):
            checks[f"{preset_name}_valid_record"] = False
            continue
        mode = str(preset.get("mode", ""))
        eligible = set(restored if mode == "restored" else recreated if mode == "recreated" else [])
        checks[f"{preset_name}_mode_valid"] = mode in {"restored", "recreated"}
        checks[f"{preset_name}_subset_of_mode_eligibility"] = set(
            str(v) for v in preset.get("textures", [])
        ).issubset(eligible)

    summary_restored = policy_summary.get("ai_restored", {})
    summary_recreated = policy_summary.get("ai_recreated", {})
    summary_restored_skipped = [
        str(row.get("id"))
        for row in summary_restored.get("skipped", [])
        if isinstance(row, dict)
    ]
    summary_recreated_skipped = [
        str(row.get("id"))
        for row in summary_recreated.get("skipped", [])
        if isinstance(row, dict)
    ]
    restored_skipped = [texture_id for texture_id in ids if texture_id not in set(restored)]
    recreated_skipped = [texture_id for texture_id in ids if texture_id not in set(recreated)]
    checks["policy_summary_selection_count"] = policy_summary.get("selection_count") == len(ids)
    checks["policy_summary_restored_count"] = summary_restored.get("eligible_count") == len(restored)
    checks["policy_summary_recreated_count"] = summary_recreated.get("eligible_count") == len(recreated)
    checks["policy_summary_restored_skips"] = summary_restored_skipped == restored_skipped
    checks["policy_summary_recreated_skips"] = summary_recreated_skipped == recreated_skipped
    checks["policy_summary_no_auto_promotion"] = (
        policy_summary.get("automatic_production_promotion") is False
    )

    restored_backend = backends.get("ai_restored", {}).get("primary", {})
    restored_model_name = str(restored_backend.get("model", ""))
    restored_model = models.get("models", {}).get(restored_model_name)
    checks["restored_primary_model_registered"] = isinstance(restored_model, dict)
    if isinstance(restored_model, dict):
        checks["restored_scale_matches_registry"] = (
            restored_backend.get("factor") == restored_model.get("scale")
        )
        checks["restored_tile_matches_registry"] = (
            restored_backend.get("tile") == restored_model.get("default_tile")
        )
        checks["restored_fp32_matches_registry"] = (
            restored_backend.get("fp32") == restored_model.get("default_fp32")
        )
        checks["restored_registry_has_checkpoint_identity"] = (
            isinstance(restored_model.get("checkpoint_size_bytes"), int)
            and restored_model.get("checkpoint_size_bytes", 0) > 0
            and isinstance(restored_model.get("checkpoint_sha256"), str)
            and len(restored_model.get("checkpoint_sha256", "")) == 64
        )
    else:
        checks["restored_scale_matches_registry"] = False
        checks["restored_tile_matches_registry"] = False
        checks["restored_fp32_matches_registry"] = False
        checks["restored_registry_has_checkpoint_identity"] = False

    runtime_packages = realesrgan_runtime.get("packages", {})
    excluded_runtime_packages = set(
        str(v)
        for v in realesrgan_runtime.get(
            "excluded_texture_runtime_packages", []
        )
    )
    checks["realesrgan_runtime_schema"] = (
        realesrgan_runtime.get("schema")
        == "openazrael.texture_lab.realesrgan_runtime_contract.v1"
    )
    checks["realesrgan_runtime_python_311"] = (
        str(realesrgan_runtime.get("python", {}).get("major_minor")) == "3.11"
    )
    checks["realesrgan_runtime_torch_212"] = (
        str(runtime_packages.get("torch", {}).get("version")) == "2.1.2"
    )
    checks["realesrgan_runtime_torchvision_0162"] = (
        str(runtime_packages.get("torchvision", {}).get("version")) == "0.16.2"
    )
    checks["realesrgan_runtime_basicsr_142"] = (
        str(runtime_packages.get("basicsr", {}).get("version")) == "1.4.2"
    )
    checks["realesrgan_runtime_functional_tensor_probe"] = (
        runtime_packages.get("torchvision", {}).get("compatibility_probe")
        == "torchvision.transforms.functional_tensor"
    )
    checks["realesrgan_runtime_no_face_stack"] = (
        realesrgan_runtime.get("face_enhancement") is False
        and {"gfpgan", "facexlib"}.issubset(excluded_runtime_packages)
    )
    checks["realesrgan_runtime_official_indexes"] = (
        {"cu118", "cu121", "cpu"}.issubset(
            set(
                str(v)
                for v in realesrgan_runtime.get(
                    "supported_torch_indexes", []
                )
            )
        )
    )

    qwen_backend = backends.get("ai_recreated", {}).get("primary", {})
    sampling = qwen.get("poc_sampling", {})
    checks["qwen_label_matches_backend"] = (
        qwen_backend.get("model_label") == qwen.get("model_label")
    )
    checks["qwen_seed_matches_backend"] = (
        qwen_backend.get("fixed_seed") == sampling.get("seed")
    )
    checks["backends_no_auto_promotion"] = (
        backends.get("automatic_production_promotion") is False
    )
    api_policy = qwen.get("api_workflow_policy", {})
    checks["qwen_no_auto_promotion"] = (
        api_policy.get("automatic_production_promotion") is False
    )
    checks["qwen_no_lightning"] = (
        sampling.get("lightning_lora_enabled") is False
        and api_policy.get("no_lightning_lora") is True
    )

    bindings = qwen.get("canonical_openazrael_workflow", {}).get("bindings", {})
    seed_node = str(bindings.get("seed_node", ""))
    load_node = str(bindings.get("load_image_node", ""))
    prompt_node = str(bindings.get("prompt_node", ""))
    negative_node = str(bindings.get("negative_prompt_node", ""))
    sampler_node = workflow.get(seed_node, {})
    checks["qwen_bound_nodes_exist"] = all(
        node_id in workflow
        for node_id in [seed_node, load_node, prompt_node, negative_node]
    )
    sampler_inputs = sampler_node.get("inputs", {}) if isinstance(sampler_node, dict) else {}
    checks["qwen_workflow_sampling_matches_contract"] = (
        sampler_inputs.get("seed") == sampling.get("seed")
        and sampler_inputs.get("steps") == sampling.get("steps")
        and float(sampler_inputs.get("cfg", -1)) == float(sampling.get("cfg", -2))
        and sampler_inputs.get("sampler_name") == sampling.get("sampler")
        and sampler_inputs.get("scheduler") == sampling.get("scheduler")
    )

    required_models = qwen.get("required_models", {})
    loader_expectations = {
        "diffusion": ("2", "unet_name"),
        "text_encoder": ("3", "clip_name"),
        "vae": ("4", "vae_name"),
    }
    model_loader_checks = {}
    for role, (node_id, field) in loader_expectations.items():
        spec = required_models.get(role, {})
        node = workflow.get(node_id, {})
        actual = node.get("inputs", {}).get(field) if isinstance(node, dict) else None
        model_loader_checks[role] = bool(
            spec
            and actual == spec.get("filename")
            and isinstance(spec.get("size_bytes"), int)
            and spec.get("size_bytes", 0) > 0
            and isinstance(spec.get("sha256"), str)
            and len(spec.get("sha256", "")) == 64
        )
    checks["qwen_required_model_loaders_match_contract"] = all(model_loader_checks.values())
    details["qwen_model_loader_checks"] = model_loader_checks

    load_image_nodes = [
        node_id for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == "LoadImage"
    ]
    checks["qwen_single_primary_input"] = (
        qwen.get("api_workflow_policy", {}).get("single_primary_load_image") is True
        and len(load_image_nodes) == 1
        and load_image_nodes[0] == load_node
    )

    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "schema": "openazrael.texture_lab.contract_validation.v1",
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed": failed,
        "checks": checks,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate cross-file invariants across the OpenAzrael Texture Lab contracts."
    )
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument("--backends", type=Path, default=DEFAULT_BACKENDS)
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--qwen", type=Path, default=DEFAULT_QWEN)
    parser.add_argument(
        "--realesrgan-runtime",
        type=Path,
        default=DEFAULT_REALESRGAN_RUNTIME,
    )
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--policy-summary", type=Path, default=DEFAULT_POLICY_SUMMARY)
    parser.add_argument(
        "--production-registry",
        type=Path,
        default=DEFAULT_PRODUCTION_REGISTRY,
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = validate_contracts(
        load_json(args.selection),
        load_json(args.policy),
        load_json(args.smoke),
        load_json(args.backends),
        load_json(args.models),
        load_json(args.qwen),
        load_json(args.workflow),
        load_json(args.policy_summary),
        load_json(args.realesrgan_runtime),
        load_json(args.production_registry),
    )
    if args.out:
        write_json(args.out, result)
    print(
        f"{result['status']} texture_lab_contracts "
        f"checks={result['check_count']} failed={result['failed_count']}"
    )
    if result["failed"]:
        print("failed: " + ", ".join(result["failed"]))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
