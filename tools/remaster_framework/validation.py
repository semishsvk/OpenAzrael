from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


VALIDATION_SCHEMA = "remaster.validation_scenario"
VALIDATION_VERSION = 1
EVALUATION_SCHEMA = "remaster.validation_evaluation"
EVALUATION_VERSION = 1


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlayerAction":
        return cls(
            action_id=str(payload["action_id"]),
            kind=ActionKind(payload["kind"]),
            execution_mode=ExecutionMode(payload["execution_mode"]),
            input_action=payload.get("input_action"),
            target=payload.get("target"),
            frames=payload.get("frames"),
            parameters=dict(payload.get("parameters", {})),
        )


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    kind: str
    match: dict[str, Any] = field(default_factory=dict)
    min_count: int = 1
    max_count: int | None = None
    after_requirement: str | None = None
    action_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value not in (None, {}, [])
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRequirement":
        return cls(
            requirement_id=str(payload["requirement_id"]),
            kind=str(payload["kind"]),
            match=dict(payload.get("match", {})),
            min_count=int(payload.get("min_count", 1)),
            max_count=(
                int(payload["max_count"])
                if payload.get("max_count") is not None
                else None
            ),
            after_requirement=payload.get("after_requirement"),
            action_id=payload.get("action_id"),
        )


@dataclass(frozen=True)
class EvidenceSequence:
    sequence_id: str
    kind: str
    field: str
    expected: tuple[Any, ...]
    match: dict[str, Any] = field(default_factory=dict)
    exact: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expected"] = list(self.expected)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceSequence":
        return cls(
            sequence_id=str(payload["sequence_id"]),
            kind=str(payload["kind"]),
            field=str(payload["field"]),
            expected=tuple(payload.get("expected", [])),
            match=dict(payload.get("match", {})),
            exact=bool(payload.get("exact", True)),
        )


@dataclass(frozen=True)
class StateExpectation:
    path: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StateExpectation":
        return cls(
            path=str(payload["path"]),
            before=payload.get("before"),
            after=payload.get("after"),
        )


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeEvidence":
        return cls(
            event_id=str(payload["event_id"]),
            frame=int(payload["frame"]),
            kind=str(payload["kind"]),
            payload=dict(payload.get("payload", {})),
            room=payload.get("room"),
        )


@dataclass(frozen=True)
class ValidationScenario:
    scenario_id: str
    room: str
    setup: dict[str, Any]
    actions: tuple[PlayerAction, ...]
    requirements: tuple[EvidenceRequirement, ...]
    forbidden: tuple[EvidenceRequirement, ...] = field(default_factory=tuple)
    sequences: tuple[EvidenceSequence, ...] = field(default_factory=tuple)
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

        for requirement in (*self.requirements, *self.forbidden):
            if (
                requirement.action_id is not None
                and requirement.action_id not in action_ids
            ):
                errors.append(
                    f"{requirement.requirement_id}: unknown action_id "
                    f"{requirement.action_id}"
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

        sequence_ids: set[str] = set()
        for sequence in self.sequences:
            if not sequence.sequence_id:
                errors.append(
                    f"{self.scenario_id}: sequence_id must not be empty"
                )
            if sequence.sequence_id in sequence_ids:
                errors.append(
                    f"{self.scenario_id}: duplicate sequence_id "
                    f"{sequence.sequence_id}"
                )
            sequence_ids.add(sequence.sequence_id)
            if not sequence.field:
                errors.append(
                    f"{sequence.sequence_id}: sequence field must not be empty"
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
            "sequences": [item.to_dict() for item in self.sequences],
            "state_expectations": [
                item.to_dict() for item in self.state_expectations
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ValidationScenario":
        if payload.get("schema") != VALIDATION_SCHEMA:
            raise ValueError("unsupported validation scenario schema")
        if payload.get("version") != VALIDATION_VERSION:
            raise ValueError("unsupported validation scenario version")
        return cls(
            scenario_id=str(payload["scenario_id"]),
            room=str(payload["room"]),
            setup=dict(payload.get("setup", {})),
            actions=tuple(
                PlayerAction.from_dict(item)
                for item in payload.get("actions", [])
            ),
            requirements=tuple(
                EvidenceRequirement.from_dict(item)
                for item in payload.get("requirements", [])
            ),
            forbidden=tuple(
                EvidenceRequirement.from_dict(item)
                for item in payload.get("forbidden", [])
            ),
            sequences=tuple(
                EvidenceSequence.from_dict(item)
                for item in payload.get("sequences", [])
            ),
            state_expectations=tuple(
                StateExpectation.from_dict(item)
                for item in payload.get("state_expectations", [])
            ),
            metadata=dict(payload.get("metadata", {})),
        )


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


def _is_subsequence(actual: list[Any], expected: list[Any]) -> bool:
    if not expected:
        return True
    index = 0
    for value in actual:
        if value == expected[index]:
            index += 1
            if index == len(expected):
                return True
    return False


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

    indexed = list(enumerate(ordered))
    action_evidence = [
        (index, item)
        for index, item in indexed
        if item.kind == "player_action"
    ]
    expected_action_sequence = [
        (action.action_id, action.execution_mode.value)
        for action in scenario.actions
    ]
    actual_action_sequence = [
        (
            str(item.payload.get("action_id", "")),
            str(item.payload.get("execution_mode", "")),
        )
        for _, item in action_evidence
    ]
    if actual_action_sequence != expected_action_sequence:
        errors.append(
            f"{scenario.scenario_id}: player_action sequence mismatch: "
            f"{actual_action_sequence!r} != {expected_action_sequence!r}"
        )

    action_windows: dict[str, tuple[int, int]] = {}
    for action_index, action in enumerate(scenario.actions):
        if action_index >= len(action_evidence):
            continue
        event_index, event = action_evidence[action_index]
        if str(event.payload.get("action_id", "")) != action.action_id:
            continue
        end_index = (
            action_evidence[action_index + 1][0]
            if action_index + 1 < len(action_evidence)
            else len(ordered)
        )
        action_windows[action.action_id] = (event_index, end_index)

    def requirement_matches(
        requirement: EvidenceRequirement,
    ) -> list[tuple[int, RuntimeEvidence]]:
        rows = [
            (index, item)
            for index, item in indexed
            if item.kind == requirement.kind
            and _subset_match(item.payload, requirement.match)
        ]
        if requirement.action_id is None:
            return rows
        window = action_windows.get(requirement.action_id)
        if window is None:
            return []
        start_index, end_index = window
        return [
            (index, item)
            for index, item in rows
            if start_index <= index < end_index
        ]

    matches_by_requirement: dict[
        str,
        list[tuple[int, RuntimeEvidence]],
    ] = {}
    for requirement in scenario.requirements:
        matches = requirement_matches(requirement)
        matches_by_requirement[requirement.requirement_id] = matches
        count = len(matches)
        if count < requirement.min_count:
            suffix = (
                f" within action {requirement.action_id}"
                if requirement.action_id
                else ""
            )
            errors.append(
                f"{requirement.requirement_id}: expected >= "
                f"{requirement.min_count}, got {count}{suffix}"
            )
        if requirement.max_count is not None and count > requirement.max_count:
            errors.append(
                f"{requirement.requirement_id}: expected <= "
                f"{requirement.max_count}, got {count}"
            )

    for requirement in scenario.requirements:
        if requirement.after_requirement is None:
            continue
        matches = matches_by_requirement.get(requirement.requirement_id, [])
        prior_matches = matches_by_requirement.get(
            requirement.after_requirement, []
        )
        if not matches or not prior_matches:
            continue
        if matches[0][0] < prior_matches[0][0]:
            errors.append(
                f"{requirement.requirement_id}: occurred before "
                f"{requirement.after_requirement}"
            )

    for forbidden in scenario.forbidden:
        matches = requirement_matches(forbidden)
        if len(matches) >= max(1, forbidden.min_count):
            scope = (
                f" during action {forbidden.action_id}"
                if forbidden.action_id
                else ""
            )
            errors.append(
                f"{forbidden.requirement_id}: forbidden evidence observed "
                f"{len(matches)} time(s){scope}"
            )

    for sequence in scenario.sequences:
        matching_events = [
            item
            for item in ordered
            if item.kind == sequence.kind
            and _subset_match(item.payload, sequence.match)
        ]
        actual = [
            item.payload.get(sequence.field)
            for item in matching_events
            if sequence.field in item.payload
        ]
        expected = list(sequence.expected)
        ok = actual == expected if sequence.exact else _is_subsequence(actual, expected)
        if not ok:
            mode = "exact" if sequence.exact else "subsequence"
            errors.append(
                f"{sequence.sequence_id}: {mode} sequence mismatch: "
                f"{actual!r} != {expected!r}"
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


def build_evaluation_report(
    scenario: ValidationScenario,
    evidence: list[RuntimeEvidence],
    before_state: dict[str, Any],
    after_state: dict[str, Any],
) -> dict[str, Any]:
    errors = evaluate_scenario(
        scenario,
        evidence,
        before_state,
        after_state,
    )
    return {
        "schema": EVALUATION_SCHEMA,
        "version": EVALUATION_VERSION,
        "scenario_id": scenario.scenario_id,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "evidence_count": len(evidence),
        "before_state_sha256": canonical_state_hash(before_state),
        "after_state_sha256": canonical_state_hash(after_state),
    }
