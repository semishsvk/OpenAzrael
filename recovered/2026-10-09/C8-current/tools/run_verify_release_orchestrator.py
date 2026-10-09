#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.remaster_framework.verify_orchestrator import (
    GateSpec,
    can_reuse_pass,
    classify_readiness,
    gate_fingerprint,
    matches_any,
    merge_changed_files,
    select_plan,
)

PROFILE = ROOT / "data/tests/openazrael_verify_release_profile_v1.json"
DEFAULT_RECEIPT = ROOT / ".tmp/kg001/verify_release_orchestrator.json"
DEFAULT_CACHE = ROOT / ".tmp/kg001/verify_release_cache.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=900,
    )


def git(*args: str) -> str:
    proc = run(["git", *args])
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def git_clean() -> bool:
    proc = run(["git", "status", "--porcelain", "--untracked-files=normal"])
    return proc.returncode == 0 and proc.stdout.strip() == ""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tracked_files() -> list[str]:
    raw = git("ls-files", "-z")
    return [item for item in raw.split("\0") if item]


def resolve_base(explicit: str | None, head: str) -> str | None:
    if explicit:
        git("rev-parse", explicit)
        return explicit
    proc = run(["git", "rev-parse", f"{head}^"])
    if proc.returncode == 0:
        return proc.stdout.strip()
    return None


def working_tree_changed_files() -> list[str]:
    groups: list[list[str]] = []
    for cmd in (
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        proc = run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(proc.stdout.strip() or f"{' '.join(cmd)} failed")
        groups.append([line.strip() for line in proc.stdout.splitlines() if line.strip()])
    return list(merge_changed_files(*groups))


def changed_files(base: str | None, head: str, worktree: list[str]) -> list[str]:
    if base is None:
        committed = tracked_files()
    else:
        proc = run(["git", "diff", "--name-only", f"{base}...{head}"])
        if proc.returncode != 0:
            raise RuntimeError(proc.stdout.strip() or "git diff failed")
        committed = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return list(merge_changed_files(committed, worktree))


def expand_command(command: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for item in command:
        out.append(sys.executable if item == "<python>" else item)
    return out


def file_identity_for_gate(gate: GateSpec, tracked: list[str]) -> dict[str, dict[str, object]]:
    patterns = gate.inputs or ("**",)
    selected = sorted(path for path in tracked if matches_any(path, patterns))
    identity: dict[str, dict[str, object]] = {}
    for rel in selected:
        path = ROOT / rel
        if not path.is_file():
            identity[rel] = {"missing": True}
            continue
        identity[rel] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    return identity


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def environment_identity() -> dict[str, object]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "packages": {
            name: _package_version(name)
            for name in ("numpy", "Pillow", "trimesh", "soundfile")
        },
    }


def load_cache(path: Path) -> dict:
    if not path.is_file():
        return {"schema": "openazrael.verify_release_cache", "version": 1, "gates": {}}
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {"schema": "openazrael.verify_release_cache", "version": 1, "gates": {}}
    if payload.get("schema") != "openazrael.verify_release_cache" or payload.get("version") != 1:
        return {"schema": "openazrael.verify_release_cache", "version": 1, "gates": {}}
    if not isinstance(payload.get("gates"), dict):
        payload["gates"] = {}
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff-aware OpenAzrael source verification and release-readiness orchestrator.")
    ap.add_argument("--mode", choices=("fast", "verify", "plan"), default="fast")
    ap.add_argument("--base", help="Git base commit/ref. Defaults to HEAD^; if unavailable VERIFY is forced.")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    profile = load_json(PROFILE)
    if profile.get("schema") != "openazrael.verify_release_profile" or profile.get("version") != 1:
        raise SystemExit("invalid verify/release profile")
    gates = [GateSpec.from_dict(item) for item in profile.get("gates", [])]
    gate_by_id = {gate.gate_id: gate for gate in gates}
    if len(gate_by_id) != len(gates):
        raise SystemExit("duplicate gate id in verify/release profile")

    head = git("rev-parse", args.head)
    base = resolve_base(args.base, head)
    worktree = working_tree_changed_files()
    diff = changed_files(base, head, worktree)
    requested_mode = args.mode
    plan_mode = "fast" if requested_mode == "plan" else requested_mode
    if base is None and plan_mode == "fast":
        plan_mode = "verify"

    plan = select_plan(
        mode=plan_mode,
        changed_files=diff,
        gates=gates,
        critical_patterns=tuple(profile.get("critical_patterns", [])),
        fallback_gate_id=str(profile["fallback_gate_id"]),
    )
    selected = [gate_by_id[gate_id] for gate_id in plan.selected_gate_ids]

    profile_sha = sha256(PROFILE)
    tracked = tracked_files()
    fingerprint_files = list(merge_changed_files(tracked, worktree))
    env = environment_identity()
    cache = load_cache(args.cache)
    cache_gates = cache.setdefault("gates", {})
    results: list[dict[str, object]] = []

    if requested_mode != "plan":
        for gate in selected:
            identity = file_identity_for_gate(gate, fingerprint_files)
            fingerprint = gate_fingerprint(
                gate,
                input_identity=identity,
                profile_sha256=profile_sha,
                environment_identity=env,
            )
            cached = cache_gates.get(gate.gate_id)
            if gate.cacheable and not args.no_cache and can_reuse_pass(cached, fingerprint=fingerprint):
                results.append({
                    "gate": gate.gate_id,
                    "status": "PASS",
                    "source": "CACHE_REUSE",
                    "fingerprint": fingerprint,
                    "command": list(gate.command),
                    "output_tail": str(cached.get("output_tail", ""))[-4000:],
                })
                continue

            proc = run(expand_command(gate.command))
            status = "PASS" if proc.returncode == 0 else "FAIL"
            row = {
                "gate": gate.gate_id,
                "status": status,
                "source": "EXECUTED",
                "fingerprint": fingerprint,
                "command": list(gate.command),
                "returncode": proc.returncode,
                "output_tail": proc.stdout[-12000:],
            }
            results.append(row)
            cache_gates[gate.gate_id] = {
                "status": status,
                "fingerprint": fingerprint,
                "command": list(gate.command),
                "output_tail": proc.stdout[-4000:],
            }
            if status != "PASS":
                break

        write_json(args.cache, cache)

    all_pass = requested_mode != "plan" and len(results) == len(selected) and all(
        row.get("status") == "PASS" for row in results
    )
    clean = git_clean()
    github_actions = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    github_sha = os.environ.get("GITHUB_SHA", "")
    ci_expected_sha = os.environ.get("OPENAZRAEL_CI_EXPECTED_SHA", "")
    ci_complete = os.environ.get("OPENAZRAEL_CI_COMPLETE", "").lower() == "true"
    exact_head_ci = bool(
        github_actions
        and ci_complete
        and ci_expected_sha == head
        and requested_mode == "verify"
        and all_pass
    )

    readiness = (
        "PLAN_ONLY"
        if requested_mode == "plan"
        else classify_readiness(
            mode=plan_mode,
            all_selected_pass=all_pass,
            clean_worktree=clean,
            exact_head_ci=exact_head_ci,
        )
    )
    receipt = {
        "schema": "openazrael.verify_release_orchestrator",
        "version": 1,
        "status": "PLAN" if requested_mode == "plan" else ("PASS" if all_pass else "FAIL"),
        "requested_mode": requested_mode,
        "effective_mode": plan_mode,
        "commit_sha": head,
        "source_tree_sha": git("rev-parse", f"{head}^{{tree}}"),
        "base": base,
        "clean_worktree": clean,
        "changed_files": list(plan.changed_files),
        "worktree_changed_files": worktree,
        "selected_gates": list(plan.selected_gate_ids),
        "unmatched_critical_files": list(plan.unmatched_critical_files),
        "escalated_to_verify": plan.escalated_to_verify or (requested_mode == "fast" and plan_mode == "verify"),
        "plan_reason": plan.reason if base is not None else "no_base_full_verify",
        "profile": {
            "path": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": profile_sha,
        },
        "cache_policy": "PASS_ONLY_EXACT_GATE_FINGERPRINT",
        "results": results,
        "execution_context": {
            "github_actions": github_actions,
            "github_sha": github_sha,
            "ci_expected_sha": ci_expected_sha,
            "ci_complete": ci_complete,
            "exact_head_ci": exact_head_ci,
            "environment": env,
        },
        "readiness": readiness,
        "candidate_build_created": False,
        "asset_backed_runtime_executed": False,
        "known_good_claimed": False,
    }
    write_json(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))

    if requested_mode == "plan":
        return 0
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
