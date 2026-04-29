from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from runtime.protocol import Node
from runtime.registry import get


class PipelineDef:
    def __init__(self, name: str, nodes: list[dict[str, Any]], edges: list[list[str]]) -> None:
        self.name = name
        self.nodes = nodes
        self.edges = edges

    def instantiate(self) -> list[Node]:
        node_map: dict[str, Node] = {}
        for nd in self.nodes:
            node_id = nd["id"]
            cls = get(nd["type"])
            instance = cls()
            params = dict(nd.get("params") or {})
            params["_id"] = node_id
            instance.configure(params)
            node_map[node_id] = instance

        ordered = self._topo_sort(node_map)
        return ordered

    def _topo_sort(self, node_map: dict[str, Node]) -> list[Node]:
        if not self.edges:
            return list(node_map.values())

        in_degree: dict[str, int] = {nid: 0 for nid in node_map}
        adj: dict[str, list[str]] = {nid: [] for nid in node_map}
        for src, dst in self.edges:
            adj[src].append(dst)
            in_degree[dst] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result: list[Node] = []
        while queue:
            nid = queue.pop(0)
            result.append(node_map[nid])
            for child in adj[nid]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(node_map):
            orphan_ids = set(node_map) - {n.name for n in result}
            result.extend(node_map[nid] for nid in orphan_ids)
        return result


def load_pipeline(path: Path) -> PipelineDef:
    text = path.read_text()
    data = yaml.safe_load(text)
    return PipelineDef(
        name=data["name"],
        nodes=data["nodes"],
        edges=data.get("edges") or [],
    )
