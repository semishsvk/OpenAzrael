from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


GRAPH_SCHEMA = "remaster.reference_graph"
GRAPH_VERSION = 1


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_edge_id(
    source: str,
    relation: str,
    target: str,
    qualifier: str = "",
) -> str:
    raw = "\0".join((source, relation, target, qualifier)).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"edge:{digest}"


class ReferenceGraph:
    def __init__(self, *, project: str) -> None:
        self.project = project
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

    def add_node(
        self,
        node_id: str,
        kind: str,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        candidate = GraphNode(node_id, kind, label, metadata or {})
        previous = self._nodes.get(node_id)
        if previous is not None and previous != candidate:
            raise ValueError(f"conflicting node definition: {node_id}")
        self._nodes[node_id] = candidate

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def add_edge(
        self,
        source: str,
        relation: str,
        target: str,
        *,
        metadata: dict[str, Any] | None = None,
        qualifier: str = "",
    ) -> None:
        edge_id = stable_edge_id(source, relation, target, qualifier)
        candidate = GraphEdge(
            edge_id=edge_id,
            source=source,
            target=target,
            relation=relation,
            metadata=metadata or {},
        )
        previous = self._edges.get(edge_id)
        if previous is not None and previous != candidate:
            raise ValueError(f"conflicting edge definition: {edge_id}")
        self._edges[edge_id] = candidate

    def validate(self) -> list[str]:
        errors: list[str] = []
        for edge in self._edges.values():
            if edge.source not in self._nodes:
                errors.append(
                    f"{edge.edge_id}: missing source node {edge.source}"
                )
            if edge.target not in self._nodes:
                errors.append(
                    f"{edge.edge_id}: missing target node {edge.target}"
                )
        return sorted(errors)

    def to_dict(self) -> dict[str, Any]:
        nodes = sorted(self._nodes.values(), key=lambda item: item.node_id)
        edges = sorted(
            self._edges.values(),
            key=lambda item: (
                item.source,
                item.relation,
                item.target,
                item.edge_id,
            ),
        )
        return {
            "schema": GRAPH_SCHEMA,
            "version": GRAPH_VERSION,
            "project": self.project,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": [item.to_dict() for item in nodes],
            "edges": [item.to_dict() for item in edges],
        }
