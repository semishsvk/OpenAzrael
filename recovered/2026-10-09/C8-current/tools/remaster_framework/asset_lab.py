from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


LAB_DESCRIPTOR_SCHEMA = "remaster.asset_lab_descriptor"
LAB_DESCRIPTOR_VERSION = 1
SELECTION_SCHEMA = "remaster.production_selection"
SELECTION_VERSION = 1


class LabDomain(str, Enum):
    TEXTURE = "texture"
    AUDIO = "audio"
    LOCALIZATION = "localization"
    GENERIC = "generic"


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"
    STALE = "STALE"
    PENDING = "PENDING"


class ReviewDecision(str, Enum):
    ACCEPTED_FOR_STAGE = "ACCEPTED_FOR_STAGE"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class SourceSafetyPolicy:
    source_mutation_allowed: bool = False
    output_inside_source_allowed: bool = False
    runtime_mutation_allowed: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.source_mutation_allowed:
            errors.append("source mutation must remain disabled")
        if self.output_inside_source_allowed:
            errors.append("generated output must remain outside source root")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabDescriptor:
    lab_id: str
    domain: LabDomain
    milestone: str
    title: str
    source_safety: SourceSafetyPolicy
    acceptance_gates: tuple[str, ...] = field(default_factory=tuple)
    required_outputs: tuple[str, ...] = field(default_factory=tuple)
    deferred: tuple[str, ...] = field(default_factory=tuple)
    automatic_quality_verdict: bool = False
    automatic_production_selection: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = self.source_safety.validate()
        if not self.lab_id.strip():
            errors.append("lab_id must not be empty")
        if not self.milestone.strip():
            errors.append(f"{self.lab_id}: milestone must not be empty")
        if self.automatic_quality_verdict:
            errors.append(
                f"{self.lab_id}: automatic subjective quality verdict is forbidden"
            )
        if self.automatic_production_selection:
            errors.append(
                f"{self.lab_id}: automatic production selection is forbidden"
            )
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": LAB_DESCRIPTOR_SCHEMA,
            "version": LAB_DESCRIPTOR_VERSION,
            "lab_id": self.lab_id,
            "domain": self.domain.value,
            "milestone": self.milestone,
            "title": self.title,
            "source_safety": self.source_safety.to_dict(),
            "acceptance_gates": list(self.acceptance_gates),
            "required_outputs": list(self.required_outputs),
            "deferred": list(self.deferred),
            "automatic_quality_verdict": self.automatic_quality_verdict,
            "automatic_production_selection": self.automatic_production_selection,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class EvidenceBinding:
    evidence_id: str
    evidence_sha256: str
    source_sha256: str
    candidate_sha256: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, value in (
            ("evidence_sha256", self.evidence_sha256),
            ("source_sha256", self.source_sha256),
        ):
            if len(value) != 64:
                errors.append(f"{self.evidence_id}: invalid {name}")
        if self.candidate_sha256 is not None and len(self.candidate_sha256) != 64:
            errors.append(f"{self.evidence_id}: invalid candidate_sha256")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass(frozen=True)
class ProductionSelection:
    selection_id: str
    asset_id: str
    domain: LabDomain
    selected_variant: str
    decision: ReviewDecision
    reviewer_note: str
    evidence: tuple[EvidenceBinding, ...]
    automatic: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.automatic:
            errors.append(
                f"{self.selection_id}: production selection must be explicit/manual"
            )
        if self.decision == ReviewDecision.ACCEPTED_FOR_STAGE:
            if not self.reviewer_note.strip():
                errors.append(
                    f"{self.selection_id}: accepted selection requires reviewer_note"
                )
            if not self.evidence:
                errors.append(
                    f"{self.selection_id}: accepted selection requires evidence"
                )
        for item in self.evidence:
            errors.extend(item.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SELECTION_SCHEMA,
            "version": SELECTION_VERSION,
            "selection_id": self.selection_id,
            "asset_id": self.asset_id,
            "domain": self.domain.value,
            "selected_variant": self.selected_variant,
            "decision": self.decision.value,
            "reviewer_note": self.reviewer_note,
            "automatic": self.automatic,
            "evidence": [item.to_dict() for item in self.evidence],
        }


def sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_selection_payload(payload: dict[str, Any]) -> list[str]:
    if payload.get("schema") != SELECTION_SCHEMA:
        return ["unsupported production selection schema"]
    if payload.get("version") != SELECTION_VERSION:
        return ["unsupported production selection version"]

    try:
        evidence = tuple(
            EvidenceBinding(
                evidence_id=str(item["evidence_id"]),
                evidence_sha256=str(item["evidence_sha256"]),
                source_sha256=str(item["source_sha256"]),
                candidate_sha256=(
                    str(item["candidate_sha256"])
                    if item.get("candidate_sha256") is not None
                    else None
                ),
            )
            for item in payload.get("evidence", [])
        )
        selection = ProductionSelection(
            selection_id=str(payload["selection_id"]),
            asset_id=str(payload["asset_id"]),
            domain=LabDomain(payload["domain"]),
            selected_variant=str(payload["selected_variant"]),
            decision=ReviewDecision(payload["decision"]),
            reviewer_note=str(payload.get("reviewer_note", "")),
            evidence=evidence,
            automatic=bool(payload.get("automatic", False)),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return [f"invalid production selection payload: {exc}"]
    return selection.validate()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generic remaster Asset Lab production selections."
    )
    parser.add_argument("selection", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.selection.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print("ERROR: selection JSON root must be an object")
        return 1
    errors = validate_selection_payload(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("production selection OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
