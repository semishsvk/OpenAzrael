from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


PLAYTHROUGH_SCHEMA = "remaster.playthrough_plan"
PLAYTHROUGH_VERSION = 1


class StepKind(str, Enum):
    SCENARIO = "scenario"
    TRANSITION = "transition"
    CHECKPOINT = "checkpoint"


class StepStatus(str, Enum):
    READY = "READY"
    AUTHORING_REQUIRED = "AUTHORING_REQUIRED"
    BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"


@dataclass(frozen=True)
class PlaythroughStep:
    step_id: str
    kind: StepKind
    status: StepStatus
    room: str | None = None
    scenario_id: str | None = None
    source_room: str | None = None
    destination_room: str | None = None
    trigger: str | None = None
    checkpoint_id: str | None = None
    required_state_paths: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.step_id:
            errors.append("step_id must not be empty")
        if self.kind == StepKind.SCENARIO and self.status == StepStatus.READY:
            if not self.scenario_id:
                errors.append(f"{self.step_id}: ready scenario requires scenario_id")
        if self.kind == StepKind.TRANSITION:
            if not self.source_room or not self.destination_room or not self.trigger:
                errors.append(
                    f"{self.step_id}: transition requires source/destination/trigger"
                )
        if self.kind == StepKind.CHECKPOINT and not self.checkpoint_id:
            errors.append(f"{self.step_id}: checkpoint requires checkpoint_id")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["status"] = self.status.value
        payload["required_state_paths"] = list(self.required_state_paths)
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, {}, [])
        }


def build_playthrough_plan(
    *,
    project: str,
    plan_id: str,
    steps: list[PlaythroughStep],
    success_state_sha256: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    ids: set[str] = set()
    for step in steps:
        if step.step_id in ids:
            errors.append(f"duplicate step_id: {step.step_id}")
        ids.add(step.step_id)
        errors.extend(step.validate())
    if errors:
        raise ValueError("; ".join(errors))

    blocked = [
        step.step_id
        for step in steps
        if step.status != StepStatus.READY
    ]
    payload = {
        "schema": PLAYTHROUGH_SCHEMA,
        "version": PLAYTHROUGH_VERSION,
        "project": project,
        "plan_id": plan_id,
        "status": "READY" if not blocked else "AUTHORING_REQUIRED",
        "step_count": len(steps),
        "blocked_steps": blocked,
        "steps": [step.to_dict() for step in steps],
        "success_state_sha256": success_state_sha256,
        "metadata": metadata or {},
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def validate_checkpoint_roundtrip(
    *,
    before_save_sha256: str,
    after_restore_sha256: str,
    expected_sha256: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if before_save_sha256 != after_restore_sha256:
        errors.append(
            "save/load roundtrip hash mismatch: "
            f"{before_save_sha256} != {after_restore_sha256}"
        )
    if expected_sha256 is not None and after_restore_sha256 != expected_sha256:
        errors.append(
            "restored hash does not match expected checkpoint hash: "
            f"{after_restore_sha256} != {expected_sha256}"
        )
    return errors
