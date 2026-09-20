from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


VALIDATION_SCHEMA = "remaster.validation_scenario"
VALIDATION_VERSION = 1


class ActionKind(str, Enum):
    MOVE = "move"
    INTERACT = "interact"
    LOOK = "look"
    WAIT = "wait"


class ExecutionMode(str, Enum):
    INPUT = "input"
    INTERACTION_PROBE = "interaction_probe"
    PHYSICS_WAIT = "physics_wait"


@dataclass(frozen=True)
class PlayerAction:
    action_id: str
    kind: ActionKind
    execution_mode: ExecutionMode
    input_action: str | None = None
    target: str | None = None
    frames: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.action_id:
            errors.append("player action_id must not be empty")

        if self.kind in {ActionKind.MOVE, ActionKind.LOOK}:
            if self.execution_mode != ExecutionMode.INPUT:
                errors.append(
                    f"{self.action_id}: movement/look must use input execution"
                )
            if not self.input_action:
                errors.append(
                    f"{self.action_id}: movement/look requires input_action"
                )

        if self.kind == ActionKind.INTERACT:
            if self.execution_mode != ExecutionMode.INTERACTION_PROBE:
                errors.append(
                    f"{self.action_id}: interaction must use interaction_probe"
                )
            if not self.target:
                errors.append(
                    f"{self.action_id}: interaction requires target"
                )

        if self.kind == ActionKind.WAIT:
            if self.execution_mode != ExecutionMode.PHYSICS_WAIT:
                errors.append(
                    f"{self.action_id}: wait must use physics_wait"
                )

        if self.frames is not None and self.frames <= 0:
            errors.append(f"{self.action_id}: frames must be positive")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["execution_mode"] = self.execution_mode.value
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, {}, [])
        }


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    kind: str
    match: dict[str, Any] = field(default_factory=dict)
    min_count: int = 1
    max_count: int | None = None
    after_requirement: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value not in (None, {}, [])
        }


@dataclass(frozen=True)
class StateExpectation:
    path: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeEvidence:
    event_id: str
    frame: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    room: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value not in (None, {}, [])
        }


@dataclass(frozen=True)
class ValidationScenario:
    scenario_id: str
    room: str
    setup: dict[str, Any]
    actions: tuple[PlayerAction, ...]
    requirements: tuple[EvidenceRequirement, ...]
    forbidden: tuple[EvidenceRequirement, ...] = field(default_factory=tuple)
    state_expectations: tuple[StateExpectation, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.scenario_id:
            errors.append("scenario_id must not be empty")
        if not self.room:
            errors.append(f"{self.scenario_id}: room must not be empty")
        if not self.actions:
            errors.append(f"{self.scenario_id}: at least one player action is required")

        action_ids: set[str] = set()
        for action in self.actions:
            if action.action_id in action_ids:
                errors.append(
                    f"{self.scenario_id}: duplicate action_id {action.action_id}"
                )
            action_ids.add(action.action_id)
            errors.extend(action.validate())

        requirement_ids: set[str] = set()
        for requirement in (*self.requirements, *self.forbidden):
            if not requirement.requirement_id:
                errors.append(
                    f"{self.scenario_id}: evidence requirement_id must not be empty"
                )
            if requirement.requirement_id in requirement_ids:
                errors.append(
                    f"{self.scenario_id}: duplicate requirement_id "
                    f"{requirement.requirement_id}"
                )
            requirement_ids.add(requirement.requirement_id)
            if requirement.min_count < 0:
                errors.append(
                    f"{requirement.requirement_id}: min_count must be >= 0"
                )
            if (
                requirement.max_count is not None
                and requirement.max_count < requirement.min_count
            ):
                errors.append(
                    f"{requirement.requirement_id}: max_count < min_count"
                )

        for requirement in self.requirements:
            if (
                requirement.after_requirement is not None
                and requirement.after_requirement not in requirement_ids
            ):
                errors.append(
                    f"{requirement.requirement_id}: unknown after_requirement "
                    f"{requirement.after_requirement}"
                )

        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": VALIDATION_SCHEMA,
            "version": VALIDATION_VERSION,
            "scenario_id": self.scenario_id,
            "room": self.room,
            "setup": self.setup,
            "actions": [item.to_dict() for item in self.actions],
            "requirements": [item.to_dict() for item in self.requirements],
            "forbidden": [item.to_dict() for item in self.forbidden],
            "state_expectations": [
                item.to_dict() for item in self.state_expectations
            ],
            "metadata": self.metadata,
        }


def _normalize(value: Any, float_places: int) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical state cannot contain NaN/Infinity")
        rounded = round(value, float_places)
        return 0.0 if rounded == -0.0 else rounded
    if isinstance(value, (list, tuple)):
        return [_normalize(item, float_places) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize(value[key], float_places)
            for key in sorted(value, key=lambda item: str(item))
        }
    raise TypeError(f"unsupported canonical state type: {type(value).__name__}")


def canonical_state_bytes(value: Any, *, float_places: int = 6) -> bytes:
    normalized = _normalize(value, float_places)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_state_hash(value: Any, *, float_places: int = 6) -> str:
    return hashlib.sha256(
        canonical_state_bytes(value, float_places=float_places)
    ).hexdigest()


def _subset_match(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            key in actual and _subset_match(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return actual == expected
    return actual == expected


def _state_path(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    if path == "":
        return True, current
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def evaluate_scenario(
    scenario: ValidationScenario,
    evidence: list[RuntimeEvidence],
    before_state: dict[str, Any],
    after_state: dict[str, Any],
) -> list[str]:
    errors = scenario.validate()
    if errors:
        return errors

    ordered = sorted(evidence, key=lambda item: (item.frame, item.event_id))
    if len({item.event_id for item in ordered}) != len(ordered):
        errors.append("runtime evidence event_id values must be unique")

    action_evidence = [
        item for item in ordered if item.kind == "player_action"
    ]
    for action in scenario.actions:
        found = any(
            item.payload.get("action_id") == action.action_id
            and item.payload.get("execution_mode") == action.execution_mode.value
            for item in action_evidence
        )
        if not found:
            errors.append(
                f"{scenario.scenario_id}: missing player_action evidence "
                f"for {action.action_id}"
            )

    first_match_frame: dict[str, int] = {}
    for requirement in scenario.requirements:
        matches = [
            item
            for item in ordered
            if item.kind == requirement.kind
            and _subset_match(item.payload, requirement.match)
        ]
        count = len(matches)
        if count < requirement.min_count:
            errors.append(
                f"{requirement.requirement_id}: expected >= "
                f"{requirement.min_count}, got {count}"
            )
            continue
        if requirement.max_count is not None and count > requirement.max_count:
            errors.append(
                f"{requirement.requirement_id}: expected <= "
                f"{requirement.max_count}, got {count}"
            )
        if matches:
            first_match_frame[requirement.requirement_id] = matches[0].frame

        if requirement.after_requirement is not None:
            prior = first_match_frame.get(requirement.after_requirement)
            if prior is None:
                errors.append(
                    f"{requirement.requirement_id}: prerequisite evidence "
                    f"{requirement.after_requirement} not observed first"
                )
            elif matches and matches[0].frame < prior:
                errors.append(
                    f"{requirement.requirement_id}: occurred before "
                    f"{requirement.after_requirement}"
                )

    for forbidden in scenario.forbidden:
        matches = [
            item
            for item in ordered
            if item.kind == forbidden.kind
            and _subset_match(item.payload, forbidden.match)
        ]
        if len(matches) >= max(1, forbidden.min_count):
            errors.append(
                f"{forbidden.requirement_id}: forbidden evidence observed "
                f"{len(matches)} time(s)"
            )

    for expectation in scenario.state_expectations:
        before_found, before_value = _state_path(before_state, expectation.path)
        after_found, after_value = _state_path(after_state, expectation.path)
        if not before_found:
            errors.append(f"state before missing path: {expectation.path}")
        elif before_value != expectation.before:
            errors.append(
                f"state before mismatch {expectation.path}: "
                f"{before_value!r} != {expectation.before!r}"
            )
        if not after_found:
            errors.append(f"state after missing path: {expectation.path}")
        elif after_value != expectation.after:
            errors.append(
                f"state after mismatch {expectation.path}: "
                f"{after_value!r} != {expectation.after!r}"
            )

    return errors
