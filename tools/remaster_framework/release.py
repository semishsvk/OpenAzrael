from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


RESULTS_SCHEMA = "remaster.release_gate_results"
RESULTS_VERSION = 1
SUMMARY_SCHEMA = "remaster.release_gate_summary"
SUMMARY_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_json(payload: Any) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _required_gates(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gates = contract.get("gates", [])
    if not isinstance(gates, list):
        raise ValueError("contract gates must be a list")
    out: dict[str, dict[str, Any]] = {}
    for row in gates:
        if not isinstance(row, dict):
            raise ValueError("contract gate must be an object")
        gate_id = str(row.get("id", ""))
        if not gate_id:
            raise ValueError("contract gate id is required")
        if gate_id in out:
            raise ValueError(f"duplicate contract gate: {gate_id}")
        out[gate_id] = row
    return out


def _result_map(results: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    rows = results.get("gates", [])
    if not isinstance(rows, list):
        raise ValueError("results gates must be a list")
    out: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("result gate must be an object")
            continue
        gate_id = str(row.get("id", ""))
        if not gate_id:
            errors.append("result gate id is required")
            continue
        if gate_id in out:
            errors.append(f"duplicate result gate: {gate_id}")
            continue
        out[gate_id] = row
    return out, errors


def _validate_evidence(gate_id: str, row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = row.get("evidence", [])
    if evidence is None:
        return errors
    if not isinstance(evidence, list):
        return [f"{gate_id}: evidence must be a list"]
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"{gate_id}: evidence[{index}] must be an object")
            continue
        digest = item.get("sha256")
        if digest is not None and not SHA256_RE.fullmatch(str(digest)):
            errors.append(f"{gate_id}: evidence[{index}] invalid sha256")
    return errors


def aggregate_release(
    contract: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    if results.get("schema") != RESULTS_SCHEMA:
        raise ValueError("unsupported gate-results schema")
    if results.get("version") != RESULTS_VERSION:
        raise ValueError("unsupported gate-results version")

    required = _required_gates(contract)
    actual, structural_errors = _result_map(results)

    gate_summary: list[dict[str, Any]] = []
    blockers = list(structural_errors)
    warnings: list[str] = []

    for gate_id, gate in required.items():
        required_flag = bool(gate.get("required", False))
        result = actual.get(gate_id)
        if result is None:
            status = "MISSING"
            if required_flag:
                blockers.append(f"{gate_id}: required gate result missing")
            gate_summary.append({
                "id": gate_id,
                "name": gate.get("name"),
                "required": required_flag,
                "status": status,
                "evidence": [],
            })
            continue

        status = str(result.get("status", "UNKNOWN")).upper()
        evidence_errors = _validate_evidence(gate_id, result)
        blockers.extend(evidence_errors)
        if required_flag and status != "PASS":
            blockers.append(
                f"{gate_id}: required gate status is {status}, expected PASS"
            )
        gate_summary.append({
            "id": gate_id,
            "name": gate.get("name"),
            "required": required_flag,
            "status": status,
            "evidence": result.get("evidence", []),
            "note": result.get("note", ""),
        })

    for gate_id in sorted(set(actual) - set(required), key=str.casefold):
        warnings.append(f"result contains gate not in contract: {gate_id}")

    defects = results.get("defects", {})
    if not isinstance(defects, dict):
        defects = {}
        blockers.append("defects must be an object")

    critical = int(defects.get("known_critical_bugs", 0))
    softlocks = int(defects.get("reproducible_softlocks", 0))
    if critical != 0:
        blockers.append(f"known critical bugs: {critical}")
    if softlocks != 0:
        blockers.append(f"reproducible softlocks: {softlocks}")

    candidate = results.get("candidate", {})
    if not isinstance(candidate, dict):
        candidate = {}
        blockers.append("candidate must be an object")
    commit_sha = str(candidate.get("commit_sha", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        blockers.append("candidate commit_sha must be a 40-char lowercase Git SHA")

    holds = results.get("holds", [])
    if not isinstance(holds, list):
        holds = []
        blockers.append("holds must be a list")

    result_digest = sha256_json(results)
    status = "ELIGIBLE_FOR_KNOWN_GOOD" if not blockers else "BLOCKED"

    summary = {
        "schema": SUMMARY_SCHEMA,
        "version": SUMMARY_VERSION,
        "contract_schema": contract.get("schema"),
        "contract_version": contract.get("version"),
        "target_tag": contract.get("target_tag"),
        "candidate": candidate,
        "status": status,
        "defects": {
            "known_critical_bugs": critical,
            "reproducible_softlocks": softlocks,
        },
        "gates": gate_summary,
        "holds": holds,
        "blockers": blockers,
        "warnings": warnings,
        "gate_results_sha256": result_digest,
        "forensic_boundary": contract.get("forensic_boundary", {}),
        "automatic_tag_creation": False,
    }
    summary["summary_sha256"] = sha256_json(summary)
    return summary


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate existing release/Known-Good gates without tagging."
    )
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = aggregate_release(_load(args.contract), _load(args.results))
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if summary["status"] == "ELIGIBLE_FOR_KNOWN_GOOD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
