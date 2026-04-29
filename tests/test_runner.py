import asyncio

from runtime.context import PipelineContext
from runtime.protocol import Source, Sink
from runtime.runner import LinearRunner
from runtime.loader import PipelineDef


class CollectorSink(Sink):
    def __init__(self):
        self.items = []

    def configure(self, params):
        super().configure(params)

    async def run(self, inbox, outbox, ctx):
        while True:
            item = await inbox.get()
            if item is None:
                break
            self.items.append(item)


class EmitNSource(Source):
    def configure(self, params):
        super().configure(params)
        self.count = params.get("count", 3)

    async def run(self, inbox, outbox, ctx):
        for i in range(self.count):
            if ctx.cancelled:
                break
            await outbox.put({"value": i})


def _make_runner(count=3, cancel=False):
    src = EmitNSource()
    src.configure({"_id": "src", "count": count})
    sink = CollectorSink()
    sink.configure({"_id": "sink"})
    ctx = PipelineContext(pipeline_name="test")
    if cancel:
        ctx.cancel.set()
    defn = PipelineDef(name="test", nodes=[], edges=[])
    return LinearRunner(defn, [src, sink], ctx), sink


def test_linear_runner_3_items():
    runner, sink = _make_runner(3)
    asyncio.run(runner.run())
    assert len(sink.items) == 3
    assert sink.items[0]["value"] == 0
    assert sink.items[2]["value"] == 2


def test_linear_runner_cancel():
    runner, sink = _make_runner(3, cancel=True)
    try:
        asyncio.run(runner.run())
    except Exception:
        pass
    assert len(sink.items) == 0
