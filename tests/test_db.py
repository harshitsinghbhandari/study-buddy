import tempfile
from pathlib import Path

from core.db import Database


def _db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    db = Database(Path(f.name))
    return db


def test_schema_init():
    db = _db()
    row = db.conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    assert row["value"] == "1"
    db.close()


def test_pipeline_crud():
    db = _db()
    pid = db.create_pipeline("test", "name: test")
    assert pid is not None
    p = db.get_pipeline(pid)
    assert p["name"] == "test"
    p2 = db.get_pipeline_by_name("test")
    assert p2 is not None
    all_p = db.list_pipelines()
    assert len(all_p) == 1
    db.delete_pipeline(pid)
    assert db.get_pipeline(pid) is None
    db.close()


def test_runs():
    db = _db()
    pid = db.create_pipeline("test", "name: test")
    rid = db.create_run(pid)
    r = db.get_run(rid)
    assert r["status"] == "running"
    assert r["stopped_at"] is None
    db.stop_run(rid, "stopped")
    r2 = db.get_run(rid)
    assert r2["status"] == "stopped"
    assert r2["stopped_at"] is not None
    runs = db.list_runs(pid)
    assert len(runs) == 1
    db.close()


def test_events():
    db = _db()
    pid = db.create_pipeline("test", "name: test")
    rid = db.create_run(pid)
    db.append_event(rid, "screen", "item_emitted", {"hash": "abc"})
    db.append_event(rid, "ollama", "item_consumed", {"status": "ok"})
    events = db.get_events(rid)
    assert len(events) == 2
    assert events[0]["node_id"] == "ollama"
    db.close()


def test_state():
    db = _db()
    assert db.get_state("test_key") == {}
    db.set_state("test_key", {"count": 5})
    assert db.get_state("test_key") == {"count": 5}
    db.set_state("test_key", {"count": 10})
    assert db.get_state("test_key") == {"count": 10}
    db.close()


def test_checkpoints():
    db = _db()
    pid = db.create_pipeline("test", "name: test")
    rid = db.create_run(pid)
    assert db.get_checkpoint(rid, "screen") == {}
    db.set_checkpoint(rid, "screen", {"last_hash": "abc"})
    assert db.get_checkpoint(rid, "screen") == {"last_hash": "abc"}
    db.set_checkpoint(rid, "screen", {"last_hash": "def"})
    assert db.get_checkpoint(rid, "screen") == {"last_hash": "def"}
    db.close()
