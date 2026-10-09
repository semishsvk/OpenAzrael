from __future__ import annotations

import json
from pathlib import Path

from .contracts import ToolContract, ToolFamily


DEFAULT_MANIFEST = Path(__file__).with_name("tool_manifest.json")


class ToolRegistry:
    def __init__(self, contracts: list[ToolContract], manifest_path: Path) -> None:
        self._contracts = sorted(contracts, key=lambda item: item.tool_id)
        self.manifest_path = manifest_path

    @classmethod
    def load(cls, manifest_path: Path | None = None) -> "ToolRegistry":
        path = manifest_path or DEFAULT_MANIFEST
        payload = json.loads(path.read_text(encoding="utf-8"))
        contracts = [
            ToolContract.from_dict(item)
            for item in payload.get("tools", [])
        ]
        return cls(contracts, path)

    def all(self) -> tuple[ToolContract, ...]:
        return tuple(self._contracts)

    def by_family(self, family: ToolFamily) -> tuple[ToolContract, ...]:
        return tuple(item for item in self._contracts if item.family == family)

    def get(self, tool_id: str) -> ToolContract:
        for item in self._contracts:
            if item.tool_id == tool_id:
                return item
        raise KeyError(tool_id)

    def validate(self, repo_root: Path) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for item in self._contracts:
            if item.tool_id in seen:
                errors.append(f"duplicate tool_id: {item.tool_id}")
            seen.add(item.tool_id)
            errors.extend(item.validate(repo_root))
        return errors
