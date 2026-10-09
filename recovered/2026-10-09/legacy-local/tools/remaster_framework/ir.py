from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class IRKind(str, Enum):
    WORLD = "world"
    ROOM = "room"
    GAMEPLAY_GRAPH = "gameplay_graph"
    TRIGGER_GRAPH = "trigger_graph"
    AUDIO = "audio"
    TEXTURE = "texture"
    LOCALIZATION = "localization"
    AUDIT = "audit"
    TEST_CONTRACT = "test_contract"
    PROJECT_CONTEXT = "project_context"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IRDescriptor:
    schema_id: str
    schema_version: int | str | None
    kind: IRKind
    adapter_id: str
    legacy: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


def _legacy_schema_id(path: Path, payload: dict[str, Any]) -> tuple[str, IRKind, str]:
    name = path.name.lower()

    if "graphs" in payload and isinstance(payload.get("graphs"), dict):
        return (
            "openazrael.gameplay_event_graph",
            IRKind.GAMEPLAY_GRAPH,
            "legacy_gameplay_graph",
        )

    if (
        isinstance(payload.get("rooms"), dict)
        and isinstance(payload.get("demo_transitions"), list)
    ):
        return (
            "openazrael.xaf_trigger_evidence",
            IRKind.TRIGGER_GRAPH,
            "legacy_xaf_trigger_evidence",
        )

    if "acceptance" in name or "contract" in name:
        return (
            f"openazrael.legacy.{path.stem}",
            IRKind.TEST_CONTRACT,
            "legacy_filename_contract",
        )

    if "project_context" in name:
        return (
            "openazrael.project_context",
            IRKind.PROJECT_CONTEXT,
            "legacy_project_context",
        )

    if "sound" in name or "audio" in name:
        return (
            f"openazrael.legacy.{path.stem}",
            IRKind.AUDIO,
            "legacy_audio_filename",
        )

    if "audit" in name or "lifecycle" in name:
        return (
            f"openazrael.legacy.{path.stem}",
            IRKind.AUDIT,
            "legacy_audit_filename",
        )

    return (
        f"openazrael.legacy.{path.stem}",
        IRKind.UNKNOWN,
        "legacy_fallback",
    )


def _kind_from_schema(schema_id: str) -> IRKind:
    lowered = schema_id.lower()
    if "room" in lowered:
        return IRKind.ROOM
    if "world" in lowered and "sound" not in lowered and "audio" not in lowered:
        return IRKind.WORLD
    if "sound" in lowered or "audio" in lowered:
        return IRKind.AUDIO
    if "texture" in lowered:
        return IRKind.TEXTURE
    if "localization" in lowered or "language" in lowered:
        return IRKind.LOCALIZATION
    if "trigger" in lowered:
        return IRKind.TRIGGER_GRAPH
    if "event_graph" in lowered or "gameplay" in lowered:
        return IRKind.GAMEPLAY_GRAPH
    if "context" in lowered:
        return IRKind.PROJECT_CONTEXT
    if "contract" in lowered:
        return IRKind.TEST_CONTRACT
    if "audit" in lowered or "lifecycle" in lowered:
        return IRKind.AUDIT
    return IRKind.UNKNOWN


def describe_json_ir(path: Path, payload: dict[str, Any]) -> IRDescriptor:
    declared_schema = payload.get("schema")
    declared_version = payload.get("version")

    if isinstance(declared_schema, str) and declared_schema.strip():
        return IRDescriptor(
            schema_id=declared_schema.strip(),
            schema_version=declared_version,
            kind=_kind_from_schema(declared_schema),
            adapter_id="declared_schema",
            legacy=False,
        )

    schema_id, kind, adapter_id = _legacy_schema_id(path, payload)
    numeric_schema = declared_schema if isinstance(declared_schema, int) else None
    version = declared_version if declared_version is not None else numeric_schema

    return IRDescriptor(
        schema_id=schema_id,
        schema_version=version,
        kind=kind,
        adapter_id=adapter_id,
        legacy=True,
    )
