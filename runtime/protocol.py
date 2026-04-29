from __future__ import annotations

import abc
from typing import Any


class Item(dict):
    pass


class Node(abc.ABC):
    node_kind: str = "node"
    name: str = ""

    def configure(self, params: dict[str, Any]) -> None:
        self.name = params.get("_id", self.__class__.__name__)

    @abc.abstractmethod
    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        ...

    def schema(self) -> dict[str, Any]:
        return {}


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
