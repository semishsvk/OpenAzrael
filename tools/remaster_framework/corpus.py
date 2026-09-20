from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PROFILES = Path(__file__).with_name("corpus_profiles.json")


@dataclass(frozen=True)
class CorpusEntry:
    relative_path: str
    name: str
    size: int


def scan_corpus(root: Path) -> tuple[CorpusEntry, ...]:
    root = root.resolve()
    entries = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        entries.append(
            CorpusEntry(
                relative_path=path.relative_to(root).as_posix(),
                name=path.name,
                size=path.stat().st_size,
            )
        )
    return tuple(sorted(entries, key=lambda item: item.relative_path.casefold()))


def load_profiles(path: Path | None = None) -> dict[str, Any]:
    profile_path = path or DEFAULT_PROFILES
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "remaster.corpus_profiles":
        raise ValueError("unsupported corpus profile schema")
    if payload.get("version") != 1:
        raise ValueError("unsupported corpus profile version")
    return payload


def _count(entries: tuple[CorpusEntry, ...], pattern: str) -> int:
    folded = pattern.casefold()
    return sum(
        1
        for entry in entries
        if fnmatch.fnmatch(entry.name.casefold(), folded)
        or fnmatch.fnmatch(entry.relative_path.casefold(), folded)
    )


def _has_exact(entries: tuple[CorpusEntry, ...], expected: str) -> bool:
    folded = expected.casefold()
    return any(
        entry.name.casefold() == folded
        or entry.relative_path.casefold() == folded
        for entry in entries
    )


def evaluate_profile(
    entries: tuple[CorpusEntry, ...],
    profile: dict[str, Any],
) -> dict[str, Any]:
    missing_exact = [
        name
        for name in profile.get("required_exact", [])
        if not _has_exact(entries, str(name))
    ]

    pattern_results = []
    pattern_failures = []
    for rule in profile.get("required_patterns", []):
        pattern = str(rule["pattern"])
        minimum = int(rule.get("min_count", 1))
        actual = _count(entries, pattern)
        result = {
            "pattern": pattern,
            "min_count": minimum,
            "actual_count": actual,
            "pass": actual >= minimum,
        }
        pattern_results.append(result)
        if not result["pass"]:
            pattern_failures.append(pattern)

    count_results = []
    count_failures = []
    for rule in profile.get("expected_counts", []):
        pattern = str(rule["pattern"])
        expected = int(rule["count"])
        actual = _count(entries, pattern)
        result = {
            "pattern": pattern,
            "expected_count": expected,
            "actual_count": actual,
            "pass": actual == expected,
        }
        count_results.append(result)
        if not result["pass"]:
            count_failures.append(pattern)

    hard_failures = len(missing_exact) + len(pattern_failures)
    if hard_failures == 0 and not count_failures:
        status = "match"
    elif hard_failures == 0:
        status = "partial"
    else:
        status = "no_match"

    return {
        "profile_id": profile["profile_id"],
        "game_id": profile.get("game_id"),
        "edition": profile.get("edition"),
        "status": status,
        "missing_exact": missing_exact,
        "required_patterns": pattern_results,
        "expected_counts": count_results,
        "evidence": list(profile.get("evidence", [])),
    }


def discover_corpus(
    root: Path,
    profiles_path: Path | None = None,
) -> dict[str, Any]:
    entries = scan_corpus(root)
    profile_set = load_profiles(profiles_path)
    matches = [
        evaluate_profile(entries, profile)
        for profile in profile_set.get("profiles", [])
    ]
    order = {"match": 0, "partial": 1, "no_match": 2}
    matches.sort(
        key=lambda item: (
            order.get(str(item["status"]), 9),
            str(item["profile_id"]).casefold(),
        )
    )

    return {
        "schema": "remaster.corpus_discovery",
        "version": 1,
        "file_count": len(entries),
        "total_size": sum(entry.size for entry in entries),
        "profiles": matches,
        "hold": list(profile_set.get("hold", [])),
    }
