from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "openazrael.remaster_lab_compatibility"
VERSION = 1


def audit_audio_contract(payload: dict[str, Any]) -> dict[str, Any]:
    schema = str(payload.get("schema", ""))
    scope = payload.get("scope", {})
    if not isinstance(scope, dict):
        scope = {}

    checks = {
        "recognized_audio_lab_contract": schema.startswith(
            "openazrael.audio_lab."
        ),
        "source_mutation_disabled": (
            scope.get("source_mutation_allowed") is False
        ),
        "output_inside_source_disabled": (
            scope.get("output_inside_source_allowed") is False
        ),
        "runtime_mutation_disabled": (
            scope.get("runtime_mutation_allowed") is False
        ),
        "acceptance_gates_present": bool(payload.get("acceptance_gates")),
        "required_outputs_present": bool(payload.get("required_outputs")),
    }

    review_policy = payload.get("review_policy", {})
    if isinstance(review_policy, dict):
        checks["spectral_outliers_are_review_only"] = (
            "spectral_outliers" not in review_policy
            or "review" in str(review_policy["spectral_outliers"]).casefold()
        )

    return {
        "lab": "audio",
        "schema": schema,
        "milestone": payload.get("milestone"),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def audit_texture_policy(
    source_status: dict[str, Any],
    production_selection: dict[str, Any],
) -> dict[str, Any]:
    source_schema = str(source_status.get("schema", ""))
    selection_schema = str(production_selection.get("schema", ""))
    review = source_status.get("review_evidence", {})
    if not isinstance(review, dict):
        review = {}
    structured = review.get("structured_manual_review", {})
    if not isinstance(structured, dict):
        structured = {}

    checks = {
        "recognized_texture_source_status": source_schema.startswith(
            "openazrael.texture_lab."
        ),
        "recognized_production_selection": selection_schema.startswith(
            "openazrael.texture_lab.production_selection."
        ),
        "source_safe_status": (
            "SOURCE_SAFE" in str(source_status.get("source_status", ""))
        ),
        "automatic_selection_disabled": (
            production_selection.get("automatic_selection") is False
        ),
        "manual_review_required": (
            structured.get("required_before_stage_approval") is True
        ),
        "approval_binds_evidence_hash": (
            structured.get("binds_complete_stage_evidence_sha256") is True
        ),
        "approval_requires_note": (
            structured.get("stage_approval_requires_nonempty_note") is True
        ),
    }

    return {
        "lab": "texture",
        "schema": source_schema,
        "selection_schema": selection_schema,
        "branch": source_status.get("branch"),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def build_compatibility_report(
    *,
    audio_contracts: list[dict[str, Any]] | None = None,
    texture_source_status: dict[str, Any] | None = None,
    texture_production_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labs: list[dict[str, Any]] = []
    for payload in audio_contracts or []:
        labs.append(audit_audio_contract(payload))

    if (
        texture_source_status is not None
        and texture_production_selection is not None
    ):
        labs.append(
            audit_texture_policy(
                texture_source_status,
                texture_production_selection,
            )
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": (
            "PASS"
            if labs and all(item["status"] == "PASS" for item in labs)
            else ("EMPTY" if not labs else "FAIL")
        ),
        "labs": labs,
        "boundary": (
            "Compatibility checks architecture/source-safety/review invariants "
            "only. It never ranks candidates or makes a subjective quality verdict."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit existing OpenAzrael labs against shared framework invariants."
    )
    parser.add_argument("--audio-contract", type=Path, action="append", default=[])
    parser.add_argument("--texture-source-status", type=Path)
    parser.add_argument("--texture-production-selection", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_compatibility_report(
        audio_contracts=[_load(path) for path in args.audio_contract],
        texture_source_status=(
            _load(args.texture_source_status)
            if args.texture_source_status is not None
            else None
        ),
        texture_production_selection=(
            _load(args.texture_production_selection)
            if args.texture_production_selection is not None
            else None
        ),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
