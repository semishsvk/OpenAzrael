from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import hashlib
import json
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class GateSpec:
    gate_id: str
    command: tuple[str, ...]
    triggers: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    always_fast: bool = False
    verify: bool = False
    cacheable: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "GateSpec":
        return cls(
            gate_id=str(payload["id"]),
            command=tuple(str(v) for v in payload.get("command", [])),
            triggers=tuple(str(v) for v in payload.get("triggers", [])),
            inputs=tuple(str(v) for v in payload.get("inputs", [])),
            always_fast=bool(payload.get("always_fast", False)),
            verify=bool(payload.get("verify", False)),
            cacheable=bool(payload.get("cacheable", True)),
        )


@dataclass(frozen=True)
class Plan:
    mode: str
    changed_files: tuple[str, ...]
    selected_gate_ids: tuple[str, ...]
    unmatched_critical_files: tuple[str, ...]
    escalated_to_verify: bool
    reason: str


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def merge_changed_files(*groups: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        _norm(path)
        for group in groups
        for path in group
        if str(path).strip()
    }))


def matches_any(path: str, patterns: Sequence[str]) -> bool:
    normalized = _norm(path)
    return any(fnmatch(normalized, pattern) for pattern in patterns)


def select_plan(
    *,
    mode: str,
    changed_files: Iterable[str],
    gates: Sequence[GateSpec],
    critical_patterns: Sequence[str],
    fallback_gate_id: str,
) -> Plan:
    if mode not in {"fast", "verify"}:
        raise ValueError(f"unsupported mode: {mode}")
    changed = merge_changed_files(changed_files)
    by_id = {gate.gate_id: gate for gate in gates}
    if fallback_gate_id not in by_id:
        raise ValueError(f"fallback gate missing: {fallback_gate_id}")

    if mode == "verify":
        selected = tuple(g.gate_id for g in gates if g.verify)
        return Plan(
            mode=mode,
            changed_files=changed,
            selected_gate_ids=selected,
            unmatched_critical_files=(),
            escalated_to_verify=False,
            reason="explicit_verify",
        )

    selected: list[str] = [g.gate_id for g in gates if g.always_fast]
    matched_files: set[str] = set()
    for gate in gates:
        if gate.always_fast or not gate.triggers:
            continue
        hits = [path for path in changed if matches_any(path, gate.triggers)]
        if hits:
            matched_files.update(hits)
            if gate.gate_id not in selected:
                selected.append(gate.gate_id)

    unmatched = tuple(
        path for path in changed
        if matches_any(path, critical_patterns) and path not in matched_files
    )
    escalated = bool(unmatched)
    if escalated and fallback_gate_id not in selected:
        selected.append(fallback_gate_id)
    reason = "unmatched_critical_change" if escalated else "diff_targeted"
    if not changed:
        reason = "no_diff"
    return Plan(
        mode=mode,
        changed_files=changed,
        selected_gate_ids=tuple(selected),
        unmatched_critical_files=unmatched,
        escalated_to_verify=escalated,
        reason=reason,
    )


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def gate_fingerprint(
    gate: GateSpec,
    *,
    input_identity: Mapping[str, Mapping[str, object]],
    profile_sha256: str,
    environment_identity: Mapping[str, object],
) -> str:
    return canonical_sha256({
        "gate_id": gate.gate_id,
        "command": list(gate.command),
        "inputs": {
            path: dict(input_identity[path])
            for path in sorted(input_identity)
        },
        "profile_sha256": profile_sha256,
        "environment": dict(environment_identity),
    })


def can_reuse_pass(
    cached: Mapping[str, object] | None,
    *,
    fingerprint: str,
) -> bool:
    if not cached:
        return False
    return (
        cached.get("status") == "PASS"
        and cached.get("fingerprint") == fingerprint
    )


def classify_readiness(
    *,
    mode: str,
    all_selected_pass: bool,
    clean_worktree: bool,
    exact_head_ci: bool,
) -> str:
    if not all_selected_pass:
        return "BLOCKED_SOURCE_VERIFY"
    if not clean_worktree:
        return "BLOCKED_DIRTY_WORKTREE"
    if mode != "verify":
        return "FAST_PASS_VERIFY_REQUIRED"
    if not exact_head_ci:
        return "LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED"
    return "SOURCE_CHECKPOINT_READY_FOR_ASSET_PREFLIGHT"
