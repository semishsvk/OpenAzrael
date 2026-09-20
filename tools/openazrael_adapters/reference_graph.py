from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.remaster_framework.graph import ReferenceGraph


def _asset_kind(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".wav", ".xmi", ".mid", ".midi"}:
        return "audio_asset"
    if suffix in {".gif", ".png", ".jpg", ".jpeg", ".bmp", ".azf"}:
        return "texture_asset"
    return "asset"


def _add_asset(graph: ReferenceGraph, name: str) -> str:
    node_id = f"asset:{name}"
    graph.add_node(
        node_id,
        _asset_kind(name),
        name,
        {"filename": name},
    )
    return node_id


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def build_openazrael_reference_graph(
    xaf_path: Path,
    gameplay_path: Path,
) -> ReferenceGraph:
    xaf = _load_object(xaf_path)
    gameplay = _load_object(gameplay_path)
    graph = ReferenceGraph(project="OpenAzrael")

    rooms = xaf.get("rooms", {})
    for room_id, room in sorted(rooms.items()):
        room_node = f"room:{room_id}"
        graph.add_node(room_node, "room", room_id)

        for trigger in room.get("triggers", []):
            name = str(trigger.get("name", ""))
            trigger_node = f"trigger:{room_id}:{name}"
            graph.add_node(
                trigger_node,
                "trigger",
                name,
                {
                    "room": room_id,
                    "material": trigger.get("material"),
                    "centroid": trigger.get("centroid"),
                },
            )
            graph.add_edge(room_node, "contains", trigger_node)

            texture = trigger.get("texture")
            if isinstance(texture, str) and texture:
                asset_node = _add_asset(graph, texture)
                graph.add_edge(trigger_node, "references_texture", asset_node)

        for portal in room.get("portal_views", []):
            name = str(portal.get("name", ""))
            portal_node = f"portal:{room_id}:{name}"
            graph.add_node(
                portal_node,
                "portal",
                name,
                {
                    "room": room_id,
                    "material": portal.get("material"),
                    "centroid": portal.get("centroid"),
                    "normal": portal.get("normal"),
                },
            )
            graph.add_edge(room_node, "contains", portal_node)

            texture = portal.get("texture")
            if isinstance(texture, str) and texture:
                asset_node = _add_asset(graph, texture)
                graph.add_edge(portal_node, "references_texture", asset_node)

    for index, transition in enumerate(xaf.get("demo_transitions", [])):
        source_room = str(transition.get("source_room", ""))
        destination_room = str(transition.get("destination_room", ""))
        trigger = str(transition.get("trigger", ""))
        source_node = f"room:{source_room}"
        target_node = f"room:{destination_room}"
        trigger_node = f"trigger:{source_room}:{trigger}"

        metadata = {
            "trigger": trigger,
            "source_view": transition.get("source_view"),
            "destination_view": transition.get("destination_view"),
            "confidence": transition.get("confidence"),
        }
        graph.add_edge(
            source_node,
            "room_transition",
            target_node,
            metadata=metadata,
            qualifier=f"{index}:{trigger}",
        )
        if trigger_node in {node["node_id"] for node in graph.to_dict()["nodes"]}:
            graph.add_edge(
                trigger_node,
                "activates_transition",
                target_node,
                metadata=metadata,
                qualifier=f"{index}:{trigger}",
            )

    graphs = gameplay.get("graphs", {})
    for graph_id, payload in sorted(graphs.items()):
        gameplay_node = f"gameplay:{graph_id}"
        graph.add_node(
            gameplay_node,
            "gameplay_graph",
            graph_id,
        )

        room_prefix = graph_id.split("_", 1)[0]
        room_node = f"room:{room_prefix}"
        if room_node in {node["node_id"] for node in graph.to_dict()["nodes"]}:
            graph.add_edge(room_node, "owns_gameplay", gameplay_node)

        for source in payload.get("source", []):
            source_name = str(source)
            source_node = f"source:{source_name}"
            graph.add_node(
                source_node,
                "evidence_source",
                source_name,
            )
            graph.add_edge(gameplay_node, "evidence_source", source_node)

        for index, action in enumerate(payload.get("actions", [])):
            op = str(action.get("op", ""))
            confidence = action.get("confidence")
            asset = action.get("asset")
            key = action.get("key")

            if isinstance(asset, str) and asset:
                asset_node = _add_asset(graph, asset)
                relation = "plays_audio" if op == "play_sound" else "references_asset"
                graph.add_edge(
                    gameplay_node,
                    relation,
                    asset_node,
                    metadata={
                        "op": op,
                        "confidence": confidence,
                        "semantic": action.get("semantic"),
                    },
                    qualifier=str(index),
                )

            if isinstance(key, str) and key:
                state_kind = "inventory_state" if "inventory" in op else "state"
                state_node = f"state:{key}"
                graph.add_node(
                    state_node,
                    state_kind,
                    key,
                )
                graph.add_edge(
                    gameplay_node,
                    "mutates_state",
                    state_node,
                    metadata={
                        "op": op,
                        "value": action.get("value"),
                        "confidence": confidence,
                    },
                    qualifier=str(index),
                )

    errors = graph.validate()
    if errors:
        raise ValueError("reference graph invalid: " + "; ".join(errors))
    return graph


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic OpenAzrael room/puzzle/trigger/asset graph."
    )
    parser.add_argument("--xaf", type=Path, required=True)
    parser.add_argument("--gameplay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph = build_openazrael_reference_graph(args.xaf, args.gameplay)
    payload = graph.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"reference graph OK: {payload['node_count']} nodes, "
        f"{payload['edge_count']} edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
