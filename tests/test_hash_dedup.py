import asyncio

from runtime.context import PipelineContext
from runtime.loader import PipelineDef
from runtime.registry import get
from runtime.runner import LinearRunner

import nodes.processors.hash_dedup


class FakeSource:
    node_kind = "source"
    name = "fake"

    def configure(self, params):
        pass

    async def run(self, inbox, outbox, ctx):
        await outbox.put({"image_hash": "aaa", "data": 1})
        await outbox.put({"image_hash": "bbb", "data": 2})
        await outbox.put({"image_hash": "aaa", "data": 3})


class FakeSink:
    node_kind = "sink"
    name = "fake_sink"
    items = []

    def configure(self, params):
        pass

    async def run(self, inbox, outbox, ctx):
        while True:
            item = await inbox.get()
            if item is None:
                break
            self.items.append(item)


def test_dedup_skips_duplicates():
    dedup = get("processor.hash_dedup")()
    dedup.configure({"_id": "dedup", "key": "image_hash"})
    sink = FakeSink()
    src = FakeSource()

    ctx = PipelineContext(pipeline_name="test")
    defn = PipelineDef(name="test", nodes=[], edges=[])
    runner = LinearRunner(defn, [src, dedup, sink], ctx)
    asyncio.run(runner.run())

    assert len(sink.items) == 2
    assert sink.items[0]["image_hash"] == "aaa"
    assert sink.items[1]["image_hash"] == "bbb"
