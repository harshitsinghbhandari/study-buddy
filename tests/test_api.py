import json

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import create_app
from api.dependencies import set_db
from core.db import Database


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def app(db_path):
    a = create_app(db_path=db_path)
    db = Database(db_path)
    db.conn
    set_db(db)
    return a


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_list_nodes(client):
    resp = await client.get("/nodes")
    assert resp.status_code == 200
    data = resp.json()
    types = [n["type"] for n in data]
    assert "source.screen" in types
    assert "processor.hash_dedup" in types
    assert "sink.jsonl" in types
    for node in data:
        assert "schema" in node
        assert "params" in node["schema"]


SCREEN_OCR_YAML = """\
name: screen-ocr
nodes:
  - id: screen
    type: source.screen
    params:
      run: 1
  - id: dedup
    type: processor.hash_dedup
  - id: jsonl
    type: sink.jsonl
edges:
  - [screen, dedup]
  - [dedup, jsonl]
"""


@pytest.mark.anyio
async def test_pipeline_crud(client):
    resp = await client.post("/pipelines", json={"name": "screen-ocr", "definition_yaml": SCREEN_OCR_YAML})
    assert resp.status_code == 201
    pid = resp.json()["id"]

    resp = await client.get("/pipelines")
    assert len(resp.json()) >= 1

    resp = await client.get(f"/pipelines/{pid}")
    assert resp.json()["name"] == "screen-ocr"

    resp = await client.delete(f"/pipelines/{pid}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_list_runs(client):
    resp = await client.get("/runs")
    assert resp.status_code == 200
    assert resp.json() == []
