from __future__ import annotations

import abc
from typing import Any


class Item(dict):
    pass


class Node(abc.ABC):
    node_kind: str = "node"
    name: str = ""
    _params_schema: dict[str, Any] = {}

    def configure(self, params: dict[str, Any]) -> None:
        self.name = params.get("_id", self.__class__.__name__)

    @abc.abstractmethod
    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        ...

    @classmethod
    def schema(cls) -> dict[str, Any]:
        return {"type": cls.node_kind, "params": cls._params_schema}


class Source(Node):
    node_kind: str = "source"

    @abc.abstractmethod
    async def run(self, inbox: None, outbox: Any, ctx: Any) -> None:
        ...


class Processor(Node):
    node_kind: str = "processor"

    @abc.abstractmethod
    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        ...


class Sink(Node):
    node_kind: str = "sink"

    @abc.abstractmethod
    async def run(self, inbox: Any, outbox: None, ctx: Any) -> None:
        ...
