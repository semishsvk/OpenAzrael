from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, Callable, Generic, Hashable, Sequence, TypeVar


StateT = TypeVar("StateT", bound=Hashable)
EffectT = TypeVar("EffectT")


@dataclass(frozen=True)
class StateFuzzConfig:
    seed_base: int = 0xA2A3E1
    seed_count: int = 64
    steps_per_seed: int = 200
    repeat_previous_probability: float = 0.20
    restart_probability: float = 0.04

    def validate(self) -> None:
        if self.seed_count <= 0:
            raise ValueError("seed_count must be positive")
        if self.steps_per_seed <= 0:
            raise ValueError("steps_per_seed must be positive")
        for name, value in (
            ("repeat_previous_probability", self.repeat_previous_probability),
            ("restart_probability", self.restart_probability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class StateFuzzFailure:
    property_name: str
    seed: int
    step: int
    action: str
    trace: tuple[str, ...]
    state_before: str
    state_after: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "property": self.property_name,
            "seed": self.seed,
            "step": self.step,
            "action": self.action,
            "trace": list(self.trace),
            "state_before": self.state_before,
            "state_after": self.state_after,
            "details": self.details,
        }


def _stable_effect(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except TypeError:
        return repr(value)


def run_state_fuzz(
    *,
    initial_state: StateT,
    actions: Sequence[str],
    transition: Callable[[StateT, str], tuple[StateT, EffectT]],
    state_key: Callable[[StateT], str],
    invariant_errors: Callable[[StateT], list[str]],
    transition_errors: Callable[
        [StateT, str, StateT, EffectT], list[str]
    ] | None = None,
    reachable_state_keys: set[str] | None = None,
    recoverable_state_keys: set[str] | None = None,
    is_success: Callable[[StateT], bool] | None = None,
    success_must_be_monotonic: bool = False,
    no_op_effects_must_be_empty: bool = True,
    config: StateFuzzConfig | None = None,
) -> dict[str, Any]:
    cfg = config or StateFuzzConfig()
    cfg.validate()
    if not actions:
        raise ValueError("actions must not be empty")

    failures: list[StateFuzzFailure] = []
    total_attempts = 0
    changed_transitions = 0
    noops = 0
    success_hits = 0
    visited_keys: set[str] = {state_key(initial_state)}

    def add_failure(
        property_name: str,
        *,
        seed: int,
        step: int,
        action: str,
        trace: list[str],
        before: StateT,
        after: StateT,
        details: dict[str, Any],
    ) -> None:
        failures.append(
            StateFuzzFailure(
                property_name=property_name,
                seed=seed,
                step=step,
                action=action,
                trace=tuple(trace),
                state_before=state_key(before),
                state_after=state_key(after),
                details=details,
            )
        )

    initial_errors = invariant_errors(initial_state)
    if initial_errors:
        add_failure(
            "state_invariant",
            seed=cfg.seed_base,
            step=-1,
            action="<initial>",
            trace=[],
            before=initial_state,
            after=initial_state,
            details={"errors": initial_errors},
        )

    for offset in range(cfg.seed_count):
        seed = cfg.seed_base + offset
        rng = random.Random(seed)
        state = initial_state
        trace: list[str] = []
        previous_action: str | None = None
        success_seen = bool(is_success and is_success(state))

        for step in range(cfg.steps_per_seed):
            if step > 0 and rng.random() < cfg.restart_probability:
                state = initial_state
                trace = []
                previous_action = None
                success_seen = bool(is_success and is_success(state))

            if (
                previous_action is not None
                and rng.random() < cfg.repeat_previous_probability
            ):
                action = previous_action
            else:
                action = actions[rng.randrange(len(actions))]

            total_attempts += 1
            before = state
            next_a, effect_a = transition(before, action)
            next_b, effect_b = transition(before, action)
            trace.append(action)

            if (
                state_key(next_a) != state_key(next_b)
                or _stable_effect(effect_a) != _stable_effect(effect_b)
            ):
                add_failure(
                    "transition_determinism",
                    seed=seed,
                    step=step,
                    action=action,
                    trace=trace,
                    before=before,
                    after=next_a,
                    details={
                        "first_state": state_key(next_a),
                        "second_state": state_key(next_b),
                        "first_effect": _stable_effect(effect_a),
                        "second_effect": _stable_effect(effect_b),
                    },
                )

            before_key = state_key(before)
            after_key = state_key(next_a)
            changed = before_key != after_key
            if changed:
                changed_transitions += 1
            else:
                noops += 1
                if (
                    no_op_effects_must_be_empty
                    and _stable_effect(effect_a)
                    not in ("null", "[]", "{}", "\"\"", "()", "null")
                ):
                    add_failure(
                        "noop_side_effect",
                        seed=seed,
                        step=step,
                        action=action,
                        trace=trace,
                        before=before,
                        after=next_a,
                        details={"effect": _stable_effect(effect_a)},
                    )

            errors = invariant_errors(next_a)
            if errors:
                add_failure(
                    "state_invariant",
                    seed=seed,
                    step=step,
                    action=action,
                    trace=trace,
                    before=before,
                    after=next_a,
                    details={"errors": errors},
                )

            if transition_errors is not None:
                errors = transition_errors(
                    before,
                    action,
                    next_a,
                    effect_a,
                )
                if errors:
                    add_failure(
                        "transition_invariant",
                        seed=seed,
                        step=step,
                        action=action,
                        trace=trace,
                        before=before,
                        after=next_a,
                        details={"errors": errors},
                    )

            if (
                reachable_state_keys is not None
                and after_key not in reachable_state_keys
            ):
                add_failure(
                    "unreachable_state_escape",
                    seed=seed,
                    step=step,
                    action=action,
                    trace=trace,
                    before=before,
                    after=next_a,
                    details={},
                )

            if (
                recoverable_state_keys is not None
                and after_key not in recoverable_state_keys
            ):
                add_failure(
                    "liveness_softlock",
                    seed=seed,
                    step=step,
                    action=action,
                    trace=trace,
                    before=before,
                    after=next_a,
                    details={
                        "reason": (
                            "fuzzed state has no known path to success"
                        )
                    },
                )

            if is_success is not None:
                now_success = bool(is_success(next_a))
                if now_success:
                    success_hits += 1
                if (
                    success_must_be_monotonic
                    and success_seen
                    and not now_success
                ):
                    add_failure(
                        "success_regression",
                        seed=seed,
                        step=step,
                        action=action,
                        trace=trace,
                        before=before,
                        after=next_a,
                        details={},
                    )
                success_seen = success_seen or now_success

            visited_keys.add(after_key)
            state = next_a
            previous_action = action

    unique_failures: dict[tuple[Any, ...], StateFuzzFailure] = {}
    for failure in failures:
        key = (
            failure.property_name,
            failure.action,
            failure.state_before,
            failure.state_after,
            _stable_effect(failure.details),
        )
        unique_failures.setdefault(key, failure)

    ordered_failures = sorted(
        unique_failures.values(),
        key=lambda item: (
            item.seed,
            item.step,
            item.property_name,
            item.action,
        ),
    )

    return {
        "schema": "remaster.state_fuzz",
        "version": 1,
        "status": "PASS" if not ordered_failures else "FAIL",
        "configuration": {
            "seed_base": cfg.seed_base,
            "seed_count": cfg.seed_count,
            "steps_per_seed": cfg.steps_per_seed,
            "repeat_previous_probability": (
                cfg.repeat_previous_probability
            ),
            "restart_probability": cfg.restart_probability,
            "success_must_be_monotonic": success_must_be_monotonic,
        },
        "action_count": len(actions),
        "attempts": total_attempts,
        "changed_transitions": changed_transitions,
        "noops": noops,
        "success_hits": success_hits,
        "unique_states_visited": len(visited_keys),
        "failure_count": len(ordered_failures),
        "failures": [item.to_dict() for item in ordered_failures],
    }
