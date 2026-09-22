from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


RESULTS_SCHEMA = "remaster.release_gate_results"
RESULTS_VERSION = 1

EVIDENCE_CANDIDATES = {
    "source": ("kg001_source_validation_v112.json",),
    "state_space": ("kg001_state_space_v108.json",),
    "state_fuzz": ("kg001_state_fuzz_v119.json",),
    "collision_v120": ("kg001_collision_geometry_v120.json",),
    "v109": (
        "kg001_v109_runtime.json",
        "kg001_headless_runtime_v109.json",
    ),
    "v110": (
        "kg001_v110_runtime.json",
        "kg001_room_trigger_runtime_v110.json",
    ),
    "v111": (
        "kg001_v111_runtime.json",
        "kg001_full_demo_runtime_v111.json",
    ),
    "v117": (
        "kg001_v117_runtime.json",
        "kg001_physical_traversal_runtime_v117.json",
    ),
    "v118": (
        "kg001_v118_runtime.json",
        "kg001_well_tongs_animation_runtime_v118.json",
    ),
    "well_pppv": (
        "kg001_well_tongs_pppv.json",
    ),
    "pppv_suite": (
        "kg001_pppv_scenario_suite.json",
    ),
    "pppv_suite_integrity": (
        "pppv_scenario_suite_integrity.json",
    ),
    "pppv_playthrough": (
        "kg001_pppv_playthrough_evaluation.json",
    ),
    "pppv_determinism": (
        "kg001_pppv_determinism.json",
    ),
    "pppv_determinism_integrity": (
        "pppv_determinism_integrity.json",
    ),
    "fresh": ("kg001_fresh_checkout.json",),
    "manual": (
        "kg001_manual_sanity.json",
        "kg001_manual_sanity_template.json",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _find_first(root: Path, names: Iterable[str]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _status(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "MISSING"
    value = payload.get("status")
    if value is None:
        value = payload.get("overall_status")
    return str(value or "UNKNOWN").upper()


def _combined_status(*payloads: dict[str, Any] | None) -> str:
    statuses = [_status(payload) for payload in payloads]
    if statuses and all(status == "PASS" for status in statuses):
        return "PASS"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    return "PENDING"


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _state_space_status(payload: dict[str, Any] | None) -> str:
    status = _status(payload)
    if status == "FAIL":
        return "FAIL"
    if status != "PASS" or payload is None:
        return "PENDING"

    checks = payload.get("exploration_checks")
    if (
        payload.get("schema") != "openazrael.kg001.state_space"
        or payload.get("version") != 108
        or int(payload.get("softlock_states", -1)) != 0
        or int(payload.get("non_success_dead_end_states", -1)) != 0
        or not _valid_sha256(
            payload.get("shortest_success_persistent_state_sha256")
        )
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        return "FAIL"
    return "PASS"


def _state_fuzz_status(payload: dict[str, Any] | None) -> str:
    status = _status(payload)
    if status == "FAIL":
        return "FAIL"
    if status != "PASS" or payload is None:
        return "PENDING"

    fuzz = payload.get("fuzz")
    properties = payload.get("properties")
    if (
        payload.get("schema") != "openazrael.kg001.state_fuzz"
        or payload.get("version") != 119
        or not isinstance(fuzz, dict)
        or fuzz.get("status") != "PASS"
        or int(fuzz.get("failure_count", -1)) != 0
        or int(fuzz.get("attempts", 0)) <= 0
        or not isinstance(properties, dict)
        or not properties
        or not all(value is True for value in properties.values())
    ):
        return "FAIL"
    return "PASS"


def _collision_v120_status(payload: dict[str, Any] | None) -> str:
    status = _status(payload)
    if status == "FAIL":
        return "FAIL"
    if status != "PASS" or payload is None:
        return "PENDING"

    checks = payload.get("checks")
    roles = payload.get("roles")
    errors = payload.get("errors")
    if (
        payload.get("schema")
        != "openazrael.kg001.collision_geometry_validation"
        or payload.get("version") != 120
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
        or not isinstance(roles, list)
        or not roles
        or not all(
            isinstance(row, dict) and row.get("status") == "PASS"
            for row in roles
        )
        or not isinstance(errors, list)
        or errors
    ):
        return "FAIL"
    return "PASS"


def _fresh_checkout_status(payload: dict[str, Any] | None) -> str:
    status = _status(payload)
    if status == "FAIL":
        return "FAIL"
    if status != "PASS" or payload is None:
        return "PENDING"

    runtime = payload.get("runtime_status")
    if not isinstance(runtime, dict):
        return "PENDING"
    required = (
        "v109",
        "v110",
        "v111",
        "v117",
        "v118",
        "pppv_scenario_suite",
        "pppv_playthrough",
    )
    if all(str(runtime.get(key, "")).upper() == "PASS" for key in required):
        return "PASS"
    return "PENDING"


def _evidence(path: Path | None, repo_root: Path) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    resolved = path.resolve()
    try:
        display = resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        display = str(resolved)
    return [{
        "path": display,
        "sha256": sha256_file(resolved),
    }]


def _merge_evidence(
    repo_root: Path,
    *paths: Path | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        for row in _evidence(path, repo_root):
            key = str(row["path"])
            if key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def derive_gate_rows(
    repo_root: Path,
    *,
    source_path: Path | None,
    state_space_path: Path | None,
    state_fuzz_path: Path | None,
    collision_v120_path: Path | None,
    v109_path: Path | None,
    v110_path: Path | None,
    v111_path: Path | None,
    pppv_suite_path: Path | None,
    pppv_suite_integrity_path: Path | None,
    pppv_playthrough_path: Path | None,
    pppv_determinism_path: Path | None,
    pppv_determinism_integrity_path: Path | None,
    fresh_path: Path | None,
    manual_path: Path | None,
) -> list[dict[str, Any]]:
    payloads = {
        "source": _load(source_path) if source_path else None,
        "state": _load(state_space_path) if state_space_path else None,
        "state_fuzz": _load(state_fuzz_path) if state_fuzz_path else None,
        "collision_v120": (
            _load(collision_v120_path) if collision_v120_path else None
        ),
        "v109": _load(v109_path) if v109_path else None,
        "v110": _load(v110_path) if v110_path else None,
        "v111": _load(v111_path) if v111_path else None,
        "pppv_suite": _load(pppv_suite_path) if pppv_suite_path else None,
        "pppv_suite_integrity": (
            _load(pppv_suite_integrity_path)
            if pppv_suite_integrity_path
            else None
        ),
        "pppv_playthrough": (
            _load(pppv_playthrough_path)
            if pppv_playthrough_path
            else None
        ),
        "pppv_determinism": (
            _load(pppv_determinism_path)
            if pppv_determinism_path
            else None
        ),
        "pppv_determinism_integrity": (
            _load(pppv_determinism_integrity_path)
            if pppv_determinism_integrity_path
            else None
        ),
        "fresh": _load(fresh_path) if fresh_path else None,
        "manual": _load(manual_path) if manual_path else None,
    }

    state_space_status = _state_space_status(payloads["state"])
    state_fuzz_status = _state_fuzz_status(payloads["state_fuzz"])
    state_status = (
        "PASS"
        if state_space_status == "PASS" and state_fuzz_status == "PASS"
        else (
            "FAIL"
            if "FAIL" in (state_space_status, state_fuzz_status)
            else "PENDING"
        )
    )

    collision_v120_status = _collision_v120_status(
        payloads["collision_v120"]
    )

    rows = [
        {
            "id": "G00",
            "status": _combined_status(payloads["source"]),
            "evidence": _merge_evidence(repo_root, source_path),
        },
        {
            "id": "G01",
            "status": _combined_status(payloads["source"]),
            "evidence": _merge_evidence(repo_root, source_path),
        },
        {
            "id": "G02",
            "status": _combined_status(payloads["source"], payloads["v109"]),
            "evidence": _merge_evidence(repo_root, source_path, v109_path),
        },
        {
            "id": "G03",
            "status": (
                "PASS"
                if _combined_status(payloads["source"]) == "PASS"
                and state_status == "PASS"
                else (
                    "FAIL"
                    if _combined_status(payloads["source"]) == "FAIL"
                    or state_status == "FAIL"
                    else "PENDING"
                )
            ),
            "evidence": _merge_evidence(
                repo_root,
                source_path,
                state_space_path,
                state_fuzz_path,
            ),
        },
        {
            "id": "G04",
            "status": _combined_status(
                payloads["v110"],
                payloads["pppv_suite"],
                payloads["pppv_suite_integrity"],
                {"status": collision_v120_status},
            ),
            "evidence": _merge_evidence(
                repo_root,
                v110_path,
                pppv_suite_path,
                pppv_suite_integrity_path,
                collision_v120_path,
            ),
        },
        {
            "id": "G05",
            "status": _combined_status(
                payloads["v110"],
                payloads["pppv_suite"],
                payloads["pppv_suite_integrity"],
            ),
            "evidence": _merge_evidence(
                repo_root,
                v110_path,
                pppv_suite_path,
                pppv_suite_integrity_path,
            ),
        },
        {
            "id": "G06",
            "status": _combined_status(payloads["v109"], payloads["v111"]),
            "evidence": _merge_evidence(repo_root, v109_path, v111_path),
        },
        {
            "id": "G07",
            "status": _combined_status(payloads["v109"]),
            "evidence": _merge_evidence(repo_root, v109_path),
        },
        {
            "id": "G08",
            "status": _combined_status(
                payloads["v111"],
                payloads["pppv_playthrough"],
                payloads["pppv_determinism"],
                payloads["pppv_determinism_integrity"],
            ),
            "evidence": _merge_evidence(
                repo_root,
                v111_path,
                pppv_playthrough_path,
                pppv_determinism_path,
                pppv_determinism_integrity_path,
            ),
        },
        {
            "id": "G09",
            "status": _combined_status(
                {"status": _fresh_checkout_status(payloads["fresh"])},
                payloads["pppv_suite_integrity"],
                payloads["pppv_determinism"],
                payloads["pppv_determinism_integrity"],
            ),
            "evidence": _merge_evidence(
                repo_root,
                fresh_path,
                pppv_suite_integrity_path,
                pppv_determinism_path,
                pppv_determinism_integrity_path,
            ),
        },
        {
            "id": "G10",
            "status": _combined_status(payloads["manual"]),
            "evidence": _merge_evidence(repo_root, manual_path),
        },
    ]
    return rows


def _defects(manual: dict[str, Any] | None) -> dict[str, Any]:
    if manual is None:
        return {
            "inventory_complete": False,
            "known_critical_bugs": 0,
            "reproducible_softlocks": 0,
        }

    critical = manual.get("critical_bugs")
    softlocks = manual.get("reproducible_softlocks")
    complete = (
        _status(manual) in {"PASS", "FAIL"}
        and isinstance(critical, list)
        and isinstance(softlocks, list)
    )
    return {
        "inventory_complete": complete,
        "known_critical_bugs": len(critical) if isinstance(critical, list) else 0,
        "reproducible_softlocks": (
            len(softlocks) if isinstance(softlocks, list) else 0
        ),
    }


def build_gate_results(
    repo_root: Path,
    evidence_root: Path,
    *,
    commit_sha: str | None = None,
    build_id: str = "KG-001 Candidate 1",
    manual_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    evidence_root = evidence_root.resolve()

    paths = {
        key: _find_first(evidence_root, names)
        for key, names in EVIDENCE_CANDIDATES.items()
    }
    if manual_path is not None:
        paths["manual"] = manual_path.resolve()

    state_path = paths["state_space"]

    fresh = _load(paths["fresh"]) if paths["fresh"] else None
    manual = _load(paths["manual"]) if paths["manual"] else None

    resolved_commit = str(commit_sha or "")
    if not resolved_commit and fresh is not None:
        resolved_commit = str(fresh.get("commit_sha", ""))

    gates = derive_gate_rows(
        repo_root,
        source_path=paths["source"],
        state_space_path=state_path,
        state_fuzz_path=paths["state_fuzz"],
        collision_v120_path=paths["collision_v120"],
        v109_path=paths["v109"],
        v110_path=paths["v110"],
        v111_path=paths["v111"],
        pppv_suite_path=paths["pppv_suite"],
        pppv_suite_integrity_path=paths["pppv_suite_integrity"],
        pppv_playthrough_path=paths["pppv_playthrough"],
        pppv_determinism_path=paths["pppv_determinism"],
        pppv_determinism_integrity_path=paths[
            "pppv_determinism_integrity"
        ],
        fresh_path=paths["fresh"],
        manual_path=paths["manual"],
    )

    supplemental_checks = [
        {
            "id": "V117_PHYSICAL_TRAVERSAL",
            "status": _combined_status(
                _load(paths["v117"]) if paths["v117"] else None
            ),
            "evidence": _merge_evidence(repo_root, paths["v117"]),
        },
        {
            "id": "V118_WELL_TONGS",
            "status": _combined_status(
                _load(paths["v118"]) if paths["v118"] else None
            ),
            "evidence": _merge_evidence(repo_root, paths["v118"]),
        },
        {
            "id": "PPPV_WELL_REAL_INPUT",
            "status": _combined_status(
                _load(paths["well_pppv"]) if paths["well_pppv"] else None
            ),
            "evidence": _merge_evidence(repo_root, paths["well_pppv"]),
            "required_for_g09": False,
        },
    ]

    return {
        "schema": RESULTS_SCHEMA,
        "version": RESULTS_VERSION,
        "candidate": {
            "commit_sha": resolved_commit,
            "build_id": build_id,
        },
        "defects": _defects(manual),
        "gates": gates,
        "supplemental_checks": supplemental_checks,
        "holds": [],
        "source": {
            "evidence_root": str(evidence_root),
            "adapter": "openazrael.kg001_release_evidence",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert existing KG-001 evidence into generic release gates."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        required=True,
        help="Usually .tmp/kg001 or data/tests.",
    )
    parser.add_argument("--commit-sha")
    parser.add_argument("--build-id", default="KG-001 Candidate 1")
    parser.add_argument("--manual", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_gate_results(
        args.repo_root,
        args.evidence_root,
        commit_sha=args.commit_sha,
        build_id=args.build_id,
        manual_path=args.manual,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "KG-001 release evidence: "
        + ", ".join(f"{row['id']}={row['status']}" for row in payload["gates"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
