from runtime.registry import register, get, all_types


def test_register_and_get():
    from runtime.protocol import Processor

    @register("test.mock")
    class MockProcessor(Processor):
        async def run(self, inbox, outbox, ctx):
            pass

    assert get("test.mock") is MockProcessor


def test_get_missing_raises():
    try:
        get("nonexistent.node")
        assert False, "should have raised"
    except KeyError:
        pass


def test_all_types():
    types = all_types()
    assert "source.screen" in types
    assert "processor.hash_dedup" in types
    assert "sink.jsonl" in types
