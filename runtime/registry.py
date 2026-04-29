from __future__ import annotations

from typing import Any, TypeVar

from runtime.protocol import Node

_registry: dict[str, type[Node]] = {}

N = TypeVar("N", bound=type[Node])


def register(node_type: str | None = None, *, cls: type[Node] | None = None) -> Any:
    if cls is not None:
        _registry[node_type or cls.__name__] = cls
        return cls

    def decorator(c: type[Node]) -> type[Node]:
        key = node_type or c.__name__
        _registry[key] = c
        return c
    return decorator


def get(node_type: str) -> type[Node]:
    if node_type not in _registry:
        raise KeyError(f"unknown node type: {node_type}")
    return _registry[node_type]


def all_types() -> dict[str, type[Node]]:
    return dict(_registry)
