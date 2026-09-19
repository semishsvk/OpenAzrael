#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from oa_tex_prompt import build_prompt_pair

from common import (
    ROOT,
    named_candidate_root,
    path_is_within,
    sha256_file,
    write_json,
)

SMOKE_SETS = ROOT / "tools/texture_lab/config/ai_smoke_sets.json"
SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
AI_POLICY = ROOT / "tools/texture_lab/config/ai_review_policy.json"
AI_BACKENDS = ROOT / "tools/texture_lab/config/ai_backends.json"
QWEN_CONTRACT = ROOT / "tools/texture_lab/config/qwen_2511_contract.json"
QWEN_WORKFLOW = ROOT / "tools/texture_lab/workflows/qwen_2511_openazrael_api.json"
RECREATE_PROFILES = ROOT / "tools/texture_lab/profiles/recreate_profiles.json"
DEFAULT_RUN_ROOT = ROOT / ".local/texture_lab/runs/rt_poc_01"
DEFAULT_APPROVAL_ROOT = ROOT / ".local/texture_lab/approvals/rt_poc_01"
DEFAULT_MANUAL_REVIEW_ROOT = ROOT / ".local/texture_lab/manual_reviews/rt_poc_01"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def preset_record(name: str) -> dict:
    cfg = load_json(SMOKE_SETS)
    preset = cfg.get("presets", {}).get(name)
    if not isinstance(preset, dict):
        raise SystemExit(f"unknown AI smoke preset: {name}")
    return preset


def valid_run_instance_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(hex=value)
    except (ValueError, AttributeError):
        return False
    return parsed.hex == value.lower()


def run_dir_for(preset: str, run_root: Path) -> Path:
    return run_root / preset


def review_filename(mode: str) -> str:
    return f"ai_{mode}_review_queue.json"


def plan_filename(mode: str) -> str:
    return f"{mode}_plan.json"


def technical_filename(mode: str) -> str:
    return f"ai_{mode}_validation.json"


def structural_filename(mode: str) -> str:
    return f"ai_{mode}_structural_drift.json"


def review_pack_filename(mode: str) -> str:
    return f"ai_{mode}_review_pack.json"


def review_pack_markdown_filename(mode: str) -> str:
    return f"ai_{mode}_review_pack.md"


def file_evidence(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def review_pack_snapshot(mode: str, run_dir: Path, expected: list[str]) -> dict:
    manifest_path = run_dir / review_pack_filename(mode)
    markdown_path = run_dir / review_pack_markdown_filename(mode)
    if not manifest_path.is_file() or not markdown_path.is_file():
        return {
            "status": "MISSING",
            "manifest": str(manifest_path),
            "markdown": str(markdown_path),
        }

    manifest = load_json(manifest_path)
    rows = [row for row in manifest.get("rows", []) if isinstance(row, dict)]
    ids = [str(row.get("id")) for row in rows]
    artifact_records = []
    artifacts_ok = True

    expected_candidate_root = named_candidate_root(mode, run_dir.name)
    expected_review_root = run_dir / "review_pack"

    for row in rows:
        texture_id = str(row.get("id", ""))
        for key in ["source", "candidate", "comparison", "detail_comparison", "tile_preview"]:
            record = row.get(key)
            if not isinstance(record, dict):
                continue
            path = Path(str(record.get("path", "")))
            if not path.is_file():
                artifacts_ok = False
                continue

            if key == "source":
                classic_root = ROOT / "assets/textures/classic"
                if (
                    not path_is_within(path, classic_root)
                    or path.name != f"{texture_id}.png"
                ):
                    artifacts_ok = False
            elif key == "candidate":
                if not path_is_within(path, expected_candidate_root):
                    artifacts_ok = False
            else:
                if not path_is_within(path, expected_review_root):
                    artifacts_ok = False

            current = file_evidence(path)
            artifact_records.append(current)
            if current != record:
                artifacts_ok = False

    checks = {
        "schema_ok": manifest.get("schema") == "openazrael.texture_lab.visual_review_pack.v2",
        "status_ok": manifest.get("status") == "READY_FOR_MANUAL_REVIEW",
        "mode_ok": manifest.get("mode") == mode,
        "texture_count_ok": manifest.get("texture_count") == len(expected),
        "automatic_promotion_off": manifest.get("automatic_promotion") is False,
        "ids_ok": len(ids) == len(expected) and set(ids) == set(expected),
        "artifacts_ok": artifacts_ok,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "manifest": file_evidence(manifest_path),
        "markdown": file_evidence(markdown_path),
        "artifacts": artifact_records,
        "checks": checks,
    }


def runtime_evidence_paths(mode: str, run_dir: Path) -> list[Path]:
    common = [
        run_dir / "local_preflight.json",
        run_dir / "stage_gate.json",
    ]
    if mode == "restored":
        return common + [
            run_dir / "realesrgan_doctor.json",
            run_dir / "ai_restore_run.json",
        ]
    return common + [
        run_dir / "comfy_doctor.json",
        run_dir / "qwen_preflight.json",
    ]


def expected_recreated_job_records(preset: str, run_dir: Path) -> list[Path]:
    spec = preset_record(preset)
    expected_ids = [str(value) for value in spec.get("textures", [])]
    selection = load_json(SELECTION)
    policy = load_json(AI_POLICY)
    by_id = {
        str(row["id"]): row
        for row in selection.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    }
    records: list[Path] = []

    for texture_id in expected_ids:
        entry = by_id.get(texture_id)
        if not isinstance(entry, dict):
            continue
        rules = dict(policy.get("defaults", {}))
        rules.update(
            policy.get("classes", {}).get(
                str(entry.get("content_class", "")),
                {},
            )
        )
        atlas = rules.get("atlas_split")
        if isinstance(atlas, dict):
            segments = int(atlas.get("segments", 0))
            atlas_root = run_dir / "atlas_parts" / texture_id
            records.extend(
                [
                    run_dir
                    / "recreated_jobs"
                    / f"{texture_id}_part_{index:02d}.job.json"
                    for index in range(segments)
                ]
            )
            records.extend(
                [
                    atlas_root / "classic_split.json",
                    atlas_root / "enhanced_split.json",
                    atlas_root / "stitch.json",
                ]
            )
        else:
            safe_id = texture_id.replace("#", "_")
            records.append(
                run_dir / "recreated_jobs" / f"{safe_id}.job.json"
            )

    return sorted(records)


def recreated_job_records(run_dir: Path) -> list[Path]:
    jobs = sorted((run_dir / "recreated_jobs").glob("*.job.json"))
    atlases = sorted((run_dir / "atlas_parts").glob("**/*.json"))
    return jobs + atlases


def _safe_sha(path: Path) -> str:
    return sha256_file(path) if path.is_file() else ""


def _int_equal(value: object, expected: object) -> bool:
    try:
        return int(value) == int(expected)
    except (TypeError, ValueError):
        return False


def _pack_rows_by_id(pack_manifest: dict) -> dict[str, dict]:
    return {
        str(row["id"]): row
        for row in pack_manifest.get("rows", [])
        if isinstance(row, dict) and row.get("id")
    }


def restored_generation_provenance(
    restore_run: dict,
    pack_manifest: dict,
    expected: list[str],
) -> dict:
    primary = load_json(AI_BACKENDS)["ai_restored"]["primary"]
    pack_rows = _pack_rows_by_id(pack_manifest)
    rows = [
        row
        for row in restore_run.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    ]
    by_id = {str(row["id"]): row for row in rows}
    row_checks = []

    for texture_id in expected:
        generation = by_id.get(texture_id)
        pack = pack_rows.get(texture_id)
        source = pack.get("source") if isinstance(pack, dict) else None
        candidate = pack.get("candidate") if isinstance(pack, dict) else None
        checks = {
            "generation_row_present": isinstance(generation, dict),
            "pack_row_present": isinstance(pack, dict),
            "source_hash_matches_review": bool(
                isinstance(generation, dict)
                and isinstance(source, dict)
                and generation.get("source_sha256") == source.get("sha256")
            ),
            "output_hash_matches_review": bool(
                isinstance(generation, dict)
                and isinstance(candidate, dict)
                and generation.get("output_sha256") == candidate.get("sha256")
            ),
            "model_ok": bool(
                isinstance(generation, dict)
                and generation.get("model") == primary.get("model")
            ),
            "factor_ok": bool(
                isinstance(generation, dict)
                and _int_equal(
                    generation.get("factor"),
                    primary.get("factor"),
                )
            ),
            "backend_ok": bool(
                isinstance(generation, dict)
                and generation.get("backend") == "realesrgan-python"
            ),
        }
        row_checks.append(
            {
                "id": texture_id,
                "status": "PASS" if all(checks.values()) else "FAIL",
                "checks": checks,
            }
        )

    reproducibility = restore_run.get("reproducibility", {})
    global_checks = {
        "schema_ok": restore_run.get("schema")
        == "openazrael.texture_lab.ai_restore_run.v4",
        "mode_ok": restore_run.get("mode") == "ai_restored",
        "ids_exact": (
            len(rows) == len(expected)
            and set(by_id) == set(expected)
        ),
        "runtime_identity_ok": (
            isinstance(reproducibility, dict)
            and isinstance(reproducibility.get("runtime_identity"), dict)
            and reproducibility["runtime_identity"].get("status") == "PASS"
        ),
    }
    status = (
        "PASS"
        if all(global_checks.values())
        and all(row["status"] == "PASS" for row in row_checks)
        else "FAIL"
    )
    return {
        "status": status,
        "checks": global_checks,
        "rows": row_checks,
        "intermediate_files": [],
    }


def _expected_qwen_model_set(contract: dict) -> set[tuple[str, str, int]]:
    return {
        (
            str(spec["filename"]),
            str(spec["sha256"]),
            int(spec["size_bytes"]),
        )
        for spec in contract.get("required_models", {}).values()
    }


def _job_model_set(job: dict) -> set[tuple[str, str, int]]:
    rows = job.get("model_files", [])
    result: set[tuple[str, str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            size = int(row.get("size", -1))
        except (TypeError, ValueError):
            size = -1
        result.add(
            (
                str(row.get("file", "")),
                str(row.get("sha256", "")),
                size,
            )
        )
    return result


def _qwen_job_checks(
    job: dict,
    source_sha: str,
    conditioning_sha: str,
    output_sha: str,
    contract: dict,
    workflow_sha: str,
    expected_positive: str | None = None,
    expected_negative: str | None = None,
) -> dict:
    bindings = contract.get("canonical_openazrael_workflow", {}).get(
        "bindings", {}
    )
    submitted = job.get("submitted_workflow")
    submitted_ok = isinstance(submitted, dict)
    prompt_node = str(bindings.get("prompt_node", ""))
    negative_node = str(bindings.get("negative_prompt_node", ""))
    seed_node = str(bindings.get("seed_node", ""))
    load_node = str(bindings.get("load_image_node", ""))

    def submitted_input(node_id: str, key: str):
        if not submitted_ok:
            return None
        node = submitted.get(node_id)
        if not isinstance(node, dict):
            return None
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            return None
        return inputs.get(key)

    expected_seed = contract.get("poc_sampling", {}).get("seed")
    return {
        "schema_ok": job.get("schema")
        == "openazrael.texture_lab.ai_recreated_job.v4",
        "source_hash_ok": job.get("source_sha256") == source_sha,
        "conditioning_hash_ok": (
            job.get("conditioning_image_sha256") == conditioning_sha
        ),
        "output_hash_ok": job.get("output_sha256") == output_sha,
        "workflow_hash_ok": job.get("workflow_template_sha256") == workflow_sha,
        "model_label_ok": job.get("model_label") == contract.get("model_label"),
        "seed_ok": _int_equal(
            job.get("seed"),
            contract.get("poc_sampling", {}).get("seed"),
        ),
        "model_files_ok": _job_model_set(job)
        == _expected_qwen_model_set(contract),
        "positive_prompt_ok": (
            expected_positive is None
            or job.get("positive_prompt") == expected_positive
        ),
        "negative_prompt_ok": (
            expected_negative is None
            or job.get("negative_prompt") == expected_negative
        ),
        "submitted_positive_prompt_ok": (
            expected_positive is None
            or submitted_input(prompt_node, "prompt") == expected_positive
        ),
        "submitted_negative_prompt_ok": (
            expected_negative is None
            or submitted_input(negative_node, "prompt") == expected_negative
        ),
        "submitted_seed_ok": _int_equal(
            submitted_input(seed_node, "seed"),
            expected_seed,
        ),
        "submitted_image_binding_ok": (
            isinstance(job.get("uploaded_name"), str)
            and bool(job.get("uploaded_name"))
            and submitted_input(load_node, "image")
            == job.get("uploaded_name")
        ),
    }


def recreated_generation_provenance(
    preset: str,
    run_dir: Path,
    pack_manifest: dict,
    expected: list[str],
) -> dict:
    contract = load_json(QWEN_CONTRACT)
    workflow_sha = sha256_file(QWEN_WORKFLOW)
    selection = load_json(SELECTION)
    policy = load_json(AI_POLICY)
    profiles = load_json(RECREATE_PROFILES)
    by_selection = {
        str(row["id"]): row
        for row in selection.get("textures", [])
        if isinstance(row, dict) and row.get("id")
    }
    pack_rows = _pack_rows_by_id(pack_manifest)
    row_results = []
    intermediate_files: list[dict] = []

    for texture_id in expected:
        entry = by_selection.get(texture_id, {})
        rules = dict(policy.get("defaults", {}))
        rules.update(
            policy.get("classes", {}).get(
                str(entry.get("content_class", "")),
                {},
            )
        )
        pack = pack_rows.get(texture_id)
        source = pack.get("source") if isinstance(pack, dict) else None
        candidate = pack.get("candidate") if isinstance(pack, dict) else None
        checks: dict[str, bool] = {
            "pack_row_present": isinstance(pack, dict),
            "source_record_present": isinstance(source, dict),
            "candidate_record_present": isinstance(candidate, dict),
        }

        atlas = rules.get("atlas_split")
        if isinstance(atlas, dict):
            axis = str(atlas.get("axis", ""))
            segments = int(atlas.get("segments", 0))
            atlas_root = run_dir / "atlas_parts" / texture_id
            classic_split_path = atlas_root / "classic_split.json"
            enhanced_split_path = atlas_root / "enhanced_split.json"
            stitch_path = atlas_root / "stitch.json"
            classic_split = load_json(classic_split_path)
            enhanced_split = load_json(enhanced_split_path)
            stitch = load_json(stitch_path)
            enhanced_full = (
                ROOT / "assets/textures/enhanced" / texture_id / "lanczos_x4.png"
            )
            checks.update(
                {
                    "classic_split_schema_ok": classic_split.get("schema")
                    == "openazrael.texture_lab.atlas_split.v1",
                    "enhanced_split_schema_ok": enhanced_split.get("schema")
                    == "openazrael.texture_lab.atlas_split.v1",
                    "stitch_schema_ok": stitch.get("schema")
                    == "openazrael.texture_lab.atlas_stitch.v1",
                    "classic_split_source_ok": bool(
                        isinstance(source, dict)
                        and classic_split.get("source_sha256")
                        == source.get("sha256")
                    ),
                    "enhanced_split_source_ok": bool(
                        enhanced_full.is_file()
                        and enhanced_split.get("source_sha256")
                        == sha256_file(enhanced_full)
                    ),
                    "atlas_axis_ok": (
                        classic_split.get("axis") == axis
                        and enhanced_split.get("axis") == axis
                        and stitch.get("axis") == axis
                    ),
                    "atlas_segments_ok": (
                        _int_equal(classic_split.get("segments"), segments)
                        and _int_equal(enhanced_split.get("segments"), segments)
                        and _int_equal(stitch.get("segments"), segments)
                    ),
                    "stitch_hash_matches_review": bool(
                        isinstance(candidate, dict)
                        and stitch.get("sha256") == candidate.get("sha256")
                    ),
                    "stitch_path_matches_review": bool(
                        isinstance(candidate, dict)
                        and Path(str(stitch.get("file", ""))).resolve()
                        == Path(str(candidate.get("path", ""))).resolve()
                    ),
                }
            )

            part_results = []
            for index in range(segments):
                part_name = f"part_{index:02d}.png"
                classic_part = atlas_root / "classic" / part_name
                enhanced_part = atlas_root / "enhanced" / part_name
                generated_part = atlas_root / "generated" / part_name
                job_path = (
                    run_dir
                    / "recreated_jobs"
                    / f"{texture_id}_part_{index:02d}.job.json"
                )
                job = load_json(job_path)
                prompts = build_prompt_pair(
                    profiles,
                    str(entry.get("content_class", "")),
                )
                part_checks = _qwen_job_checks(
                    job,
                    _safe_sha(classic_part),
                    _safe_sha(enhanced_part),
                    _safe_sha(generated_part),
                    contract,
                    workflow_sha,
                    prompts["positive"],
                    prompts["negative"],
                )
                part_results.append(
                    {
                        "part": index,
                        "status": (
                            "PASS" if all(part_checks.values()) else "FAIL"
                        ),
                        "checks": part_checks,
                    }
                )
                for intermediate in [
                    classic_part,
                    enhanced_part,
                    generated_part,
                ]:
                    if intermediate.is_file():
                        intermediate_files.append(file_evidence(intermediate))
            checks["part_jobs_ok"] = all(
                row["status"] == "PASS" for row in part_results
            )
            row_results.append(
                {
                    "id": texture_id,
                    "status": "PASS" if all(checks.values()) else "FAIL",
                    "checks": checks,
                    "parts": part_results,
                }
            )
            continue

        job_path = (
            run_dir
            / "recreated_jobs"
            / f"{texture_id.replace('#', '_')}.job.json"
        )
        job = load_json(job_path)
        enhanced = (
            ROOT / "assets/textures/enhanced" / texture_id / "lanczos_x4.png"
        )
        prompts = build_prompt_pair(
            profiles,
            str(entry.get("content_class", "")),
        )
        job_checks = _qwen_job_checks(
            job,
            str(source.get("sha256", "")) if isinstance(source, dict) else "",
            _safe_sha(enhanced),
            str(candidate.get("sha256", ""))
            if isinstance(candidate, dict)
            else "",
            contract,
            workflow_sha,
            prompts["positive"],
            prompts["negative"],
        )
        checks["job_ok"] = all(job_checks.values())
        row_results.append(
            {
                "id": texture_id,
                "status": "PASS" if all(checks.values()) else "FAIL",
                "checks": checks,
                "job_checks": job_checks,
            }
        )

    status = (
        "PASS"
        if len(row_results) == len(expected)
        and all(row["status"] == "PASS" for row in row_results)
        else "FAIL"
    )
    return {
        "status": status,
        "rows": row_results,
        "intermediate_files": intermediate_files,
    }


def evidence_snapshot(preset: str, run_root: Path) -> dict:
    spec = preset_record(preset)
    mode = str(spec["mode"])
    run_dir = run_dir_for(preset, run_root)

    plan = run_dir / plan_filename(mode)
    review = run_dir / review_filename(mode)
    technical = run_dir / technical_filename(mode)
    structural = run_dir / structural_filename(mode)
    review_pack_manifest = run_dir / review_pack_filename(mode)
    review_pack_markdown = run_dir / review_pack_markdown_filename(mode)
    runtime_paths = runtime_evidence_paths(mode, run_dir)

    required = [
        plan,
        review,
        technical,
        structural,
        review_pack_manifest,
        review_pack_markdown,
        *runtime_paths,
    ]
    missing = [str(path) for path in required if not path.is_file()]

    job_paths: list[Path] = []
    expected_job_paths: list[Path] = []
    if mode == "recreated":
        job_paths = recreated_job_records(run_dir)
        expected_job_paths = expected_recreated_job_records(
            preset,
            run_dir,
        )
        missing.extend(
            str(path)
            for path in expected_job_paths
            if not path.is_file()
        )

    if missing:
        return {
            "status": "MISSING",
            "preset": preset,
            "mode": mode,
            "missing": missing,
        }

    plan_data = load_json(plan)
    review_data = load_json(review)
    technical_data = load_json(technical)
    structural_data = load_json(structural)
    local_preflight = load_json(run_dir / "local_preflight.json")
    stage_gate = load_json(run_dir / "stage_gate.json")

    selected = [str(value) for value in plan_data.get("selected", [])]
    expected = [str(value) for value in spec.get("textures", [])]
    review_rows = [
        row for row in review_data.get("rows", []) if isinstance(row, dict)
    ]
    review_ids = [str(row.get("id")) for row in review_rows]
    technical_rows = [
        row for row in technical_data.get("results", []) if isinstance(row, dict)
    ]
    technical_ids = [str(row.get("id")) for row in technical_rows]
    structural_rows = [
        row
        for row in structural_data.get("results", [])
        if isinstance(row, dict)
    ]
    structural_ids = [str(row.get("id")) for row in structural_rows]
    pack = review_pack_snapshot(mode, run_dir, expected)

    pack_manifest = load_json(review_pack_manifest)
    generation_provenance: dict
    output_rows = []
    for row in pack_manifest.get("rows", []):
        if not isinstance(row, dict) or not row.get("id"):
            continue
        candidate = row.get("candidate")
        if not isinstance(candidate, dict):
            continue
        output_rows.append({"id": str(row["id"]), **candidate})

    output_ids = [row["id"] for row in output_rows]
    pack_rows_by_id = _pack_rows_by_id(pack_manifest)

    def qa_hashes_match(rows: list[dict]) -> bool:
        if len(rows) != len(expected):
            return False
        for row in rows:
            texture_id = str(row.get("id", ""))
            pack_row = pack_rows_by_id.get(texture_id)
            if not isinstance(pack_row, dict):
                return False
            source = pack_row.get("source")
            candidate = pack_row.get("candidate")
            if not isinstance(source, dict) or not isinstance(candidate, dict):
                return False
            if row.get("source_sha256") != source.get("sha256"):
                return False
            if row.get("candidate_sha256") != candidate.get("sha256"):
                return False
        return True

    expected_variant = (
        "realesrgan_x4.png" if mode == "restored" else "selected.png"
    )
    expected_only = sorted(expected)
    expected_output_root = named_candidate_root(mode, preset)
    output_namespace_ok = all(
        path_is_within(Path(str(row.get("path", ""))), expected_output_root)
        for row in output_rows
    )

    checks = {
        "plan_preset_ok": (
            plan_data.get("schema")
            == "openazrael.texture_lab.ai_bakeoff_plan.v5"
            and isinstance(plan_data.get("preset"), dict)
            and plan_data["preset"].get("name") == preset
            and plan_data.get("dry_run") is False
            and valid_run_instance_id(plan_data.get("run_instance_id"))
        ),
        "selected_ids_ok": selected == expected,
        "review_contract_ok": (
            review_data.get("schema")
            == "openazrael.texture_lab.ai_review_queue.v1"
            and review_data.get("status") == "OBSERVATIONAL_MANUAL_REVIEW"
            and review_data.get("mode") == mode
            and review_data.get("automatic_promotion") is False
            and review_data.get("only") == expected_only
        ),
        "review_ids_ok": (
            len(review_ids) == len(expected)
            and set(review_ids) == set(expected)
        ),
        "review_complete_ok": (
            len(review_rows) == len(expected)
            and all(
                row.get("review_state") == "MANUAL_REVIEW_REQUIRED"
                for row in review_rows
            )
        ),
        "technical_contract_ok": (
            technical_data.get("schema")
            == "openazrael.texture_lab.validation.v5"
            and technical_data.get("variant") == expected_variant
            and _int_equal(technical_data.get("factor"), 4)
            and technical_data.get("only") == expected_only
        ),
        "technical_ids_ok": (
            len(technical_ids) == len(expected)
            and set(technical_ids) == set(expected)
        ),
        "technical_hash_linkage_ok": qa_hashes_match(technical_rows),
        "structural_contract_ok": (
            structural_data.get("schema")
            == "openazrael.texture_lab.structural_drift.v2"
            and structural_data.get("variant") == expected_variant
            and structural_data.get("only") == expected_only
            and structural_data.get("missing") == []
        ),
        "structural_ids_ok": (
            len(structural_ids) == len(expected)
            and set(structural_ids) == set(expected)
        ),
        "structural_hash_linkage_ok": qa_hashes_match(structural_rows),
        "technical_pass_ok": (
            technical_data.get("technical_failures") == 0
            and all(
                row.get("technical_status") == "PASS"
                for row in technical_rows
            )
        ),
        "local_preflight_ok": (
            local_preflight.get("schema")
            == "openazrael.texture_lab.local_preflight.v2"
            and local_preflight.get("preset") == preset
            and local_preflight.get("mode") == mode
            and local_preflight.get("textures") == expected
            and local_preflight.get("ready_for_runtime_doctors") is True
            and local_preflight.get("blocking_checks") == []
        ),
        "stage_prerequisites_ok": (
            stage_gate.get("preset") == preset
            and stage_gate.get("requires_approval")
            == [str(v) for v in spec.get("requires_approval", [])]
            and stage_gate.get("status") == "PASS"
            and len(stage_gate.get("receipts", []))
            == len(spec.get("requires_approval", []))
            and all(
                isinstance(row, dict) and row.get("status") == "PASS"
                for row in stage_gate.get("receipts", [])
            )
        ),
        "review_pack_ok": pack.get("status") == "PASS",
        "reviewed_outputs_ok": (
            len(output_ids) == len(expected)
            and set(output_ids) == set(expected)
        ),
        "candidate_namespace_ok": output_namespace_ok,
    }

    if mode == "restored":
        doctor = load_json(run_dir / "realesrgan_doctor.json")
        restore_run = load_json(run_dir / "ai_restore_run.json")
        checks["runtime_doctor_ok"] = (
            doctor.get("schema")
            == "openazrael.texture_lab.realesrgan_doctor.v3"
            and doctor.get("ready") is True
        )
        generation_provenance = restored_generation_provenance(
            restore_run,
            pack_manifest,
            expected,
        )
        checks["generation_record_ok"] = (
            generation_provenance.get("status") == "PASS"
        )
    else:
        comfy = load_json(run_dir / "comfy_doctor.json")
        qwen = load_json(run_dir / "qwen_preflight.json")
        checks["runtime_doctor_ok"] = (
            comfy.get("schema")
            == "openazrael.texture_lab.comfy_doctor.v1"
            and comfy.get("ready") is True
        )
        checks["qwen_preflight_ok"] = (
            qwen.get("schema")
            == "openazrael.texture_lab.qwen_2511_preflight.v2"
            and qwen.get("ready_for_execution") is True
        )
        checks["generation_records_exact"] = (
            {path.resolve() for path in job_paths}
            == {path.resolve() for path in expected_job_paths}
        )
        generation_provenance = recreated_generation_provenance(
            preset,
            run_dir,
            pack_manifest,
            expected,
        )
        checks["generation_provenance_ok"] = (
            generation_provenance.get("status") == "PASS"
        )

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "preset": preset,
        "mode": mode,
        "run_dir": str(run_dir),
        "plan": file_evidence(plan),
        "review": file_evidence(review),
        "technical": file_evidence(technical),
        "structural": file_evidence(structural),
        "review_pack": pack,
        "runtime": [file_evidence(path) for path in runtime_paths],
        "generation_records": [file_evidence(path) for path in job_paths],
        "generation_provenance": generation_provenance,
        "expected_generation_records": [
            str(path) for path in expected_job_paths
        ],
        "outputs": output_rows,
        "candidate_namespace": str(expected_output_root),
        "checks": checks,
    }


def manual_review_snapshot(
    preset: str,
    run_root: Path,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    from oa_tex_manual_review import validate_manual_review

    return validate_manual_review(preset, run_root, manual_review_root)


def receipt_path(preset: str, approval_root: Path) -> Path:
    return approval_root / f"{preset}.json"


def validate_receipt(
    preset: str,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    path = receipt_path(preset, approval_root)
    if not path.is_file():
        return {"status": "MISSING", "preset": preset, "path": str(path)}

    receipt = load_json(path)
    current = evidence_snapshot(preset, run_root)
    if current.get("status") != "PASS":
        return {
            "status": "STALE",
            "preset": preset,
            "path": str(path),
            "reason": "current evidence is incomplete or invalid",
            "current": current,
        }

    manual_review = manual_review_snapshot(
        preset,
        run_root,
        manual_review_root,
    )
    if manual_review.get("status") != "PASS":
        return {
            "status": "STALE",
            "preset": preset,
            "path": str(path),
            "reason": "manual review is missing, incomplete, or stale",
            "manual_review": manual_review,
        }

    old = receipt.get("evidence", {})
    checks = {
        "plan_hash_ok": old.get("plan") == current["plan"],
        "review_hash_ok": old.get("review") == current["review"],
        "technical_hash_ok": old.get("technical") == current["technical"],
        "structural_hash_ok": old.get("structural") == current["structural"],
        "review_pack_ok": old.get("review_pack") == current["review_pack"],
        "runtime_ok": old.get("runtime") == current["runtime"],
        "generation_records_ok": (
            old.get("generation_records") == current["generation_records"]
        ),
        "generation_provenance_ok": (
            old.get("generation_provenance")
            == current["generation_provenance"]
        ),
        "outputs_ok": old.get("outputs") == current["outputs"],
        "manual_review_ok": old.get("manual_review") == manual_review,
        "schema_ok": (
            receipt.get("schema")
            == "openazrael.texture_lab.stage_approval.v5"
        ),
        "approved_ok": receipt.get("decision") == "APPROVED_FOR_NEXT_STAGE",
    }
    return {
        "status": "PASS" if all(checks.values()) else "STALE",
        "preset": preset,
        "path": str(path),
        "checks": checks,
    }


def check_prerequisites(
    preset: str,
    run_root: Path,
    approval_root: Path,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    spec = preset_record(preset)
    required = [str(v) for v in spec.get("requires_approval", [])]
    rows = [
        validate_receipt(previous, run_root, approval_root, manual_review_root)
        for previous in required
    ]
    return {
        "preset": preset,
        "requires_approval": required,
        "receipts": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "HOLD",
    }


def approve(
    preset: str,
    run_root: Path,
    approval_root: Path,
    note: str | None,
    manual_review_root: Path = DEFAULT_MANUAL_REVIEW_ROOT,
) -> dict:
    if not note or not note.strip():
        raise SystemExit("stage approval requires a non-empty --note")

    evidence = evidence_snapshot(preset, run_root)
    if evidence.get("status") != "PASS":
        raise SystemExit(
            "cannot approve stage: run evidence is incomplete or inconsistent; "
            f"status={evidence.get('status')}"
        )

    manual_review = manual_review_snapshot(
        preset,
        run_root,
        manual_review_root,
    )
    if manual_review.get("status") != "PASS":
        raise SystemExit(
            "cannot approve stage: structured manual review is missing, "
            f"incomplete, or stale; status={manual_review.get('status')}"
        )

    approval_root.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "openazrael.texture_lab.stage_approval.v5",
        "preset": preset,
        "mode": evidence["mode"],
        "decision": "APPROVED_FOR_NEXT_STAGE",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "evidence": {
            "plan": evidence["plan"],
            "review": evidence["review"],
            "technical": evidence["technical"],
            "structural": evidence["structural"],
            "review_pack": evidence["review_pack"],
            "runtime": evidence["runtime"],
            "generation_records": evidence["generation_records"],
            "generation_provenance": evidence["generation_provenance"],
            "outputs": evidence["outputs"],
            "manual_review": manual_review,
        },
    }
    path = receipt_path(preset, approval_root)
    write_json(path, receipt)
    return {"status": "PASS", "path": str(path), "receipt": receipt}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manual approval gate between staged OpenAzrael AI texture runs."
    )
    parser.add_argument("command", choices=["check", "approve", "status"])
    parser.add_argument("preset")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--approval-root", type=Path, default=DEFAULT_APPROVAL_ROOT)
    parser.add_argument(
        "--manual-review-root",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_ROOT,
    )
    parser.add_argument("--note", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "check":
        result = check_prerequisites(
            args.preset,
            args.run_root,
            args.approval_root,
            args.manual_review_root,
        )
    elif args.command == "status":
        result = validate_receipt(
            args.preset,
            args.run_root,
            args.approval_root,
            args.manual_review_root,
        )
    else:
        result = approve(
            args.preset,
            args.run_root,
            args.approval_root,
            args.note,
            args.manual_review_root,
        )

    if args.out:
        write_json(args.out, result)

    print(
        f"{result.get('status', 'HOLD')} stage_gate "
        f"command={args.command} preset={args.preset}"
    )
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
