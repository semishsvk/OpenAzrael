from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ToolFamily(str, Enum):
    DATA_LAB = "data_lab"
    TEXTURE_LAB = "texture_lab"
    AUDIO_LAB = "audio_lab"
    LOCALIZATION_LAB = "localization_lab"
    VALIDATION_LAB = "validation_lab"
    PROJECT_RELEASE = "project_release"


class ToolMaturity(str, Enum):
    EXPERIMENTAL = "experimental"
    POC = "poc"
    STABLE = "stable"
    LEGACY = "legacy"


@dataclass(frozen=True)
class ToolContract:
    tool_id: str
    family: ToolFamily
    description: str
    entrypoint: str
    inputs: tuple[str, ...] = field(default_factory=tuple)
    outputs: tuple[str, ...] = field(default_factory=tuple)
    source_safe: bool = True
    deterministic: bool = True
    mutates_runtime: bool = False
    maturity: ToolMaturity = ToolMaturity.EXPERIMENTAL

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ToolContract":
        return cls(
            tool_id=str(payload["tool_id"]),
            family=ToolFamily(payload["family"]),
            description=str(payload.get("description", "")),
            entrypoint=str(payload["entrypoint"]),
            inputs=tuple(str(v) for v in payload.get("inputs", [])),
            outputs=tuple(str(v) for v in payload.get("outputs", [])),
            source_safe=bool(payload.get("source_safe", True)),
            deterministic=bool(payload.get("deterministic", True)),
            mutates_runtime=bool(payload.get("mutates_runtime", False)),
            maturity=ToolMaturity(payload.get("maturity", "experimental")),
        )

    def validate(self, repo_root: Path) -> list[str]:
        errors: list[str] = []
        if not self.tool_id.strip():
            errors.append("tool_id must not be empty")
        if not self.description.strip():
            errors.append(f"{self.tool_id}: description must not be empty")

        path = repo_root / self.entrypoint
        if not path.is_file():
            errors.append(f"{self.tool_id}: entrypoint does not exist: {self.entrypoint}")

        # source_safe describes the immutable source corpus, while
        # mutates_runtime describes ephemeral execution state. A physical
        # validation driver may legitimately be both source-safe and
        # runtime-mutating.
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["family"] = self.family.value
        payload["maturity"] = self.maturity.value
        payload["inputs"] = list(self.inputs)
        payload["outputs"] = list(self.outputs)
        return payload
