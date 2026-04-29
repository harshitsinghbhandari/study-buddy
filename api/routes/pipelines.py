from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_db, get_active_runners
from runtime.context import PipelineContext
from runtime.loader import PipelineDef, load_pipeline
from runtime.runner import LinearRunner

import nodes.sources.screen
import nodes.sources.camera
import nodes.sources.folder
import nodes.processors.hash_dedup
import nodes.processors.ollama_ocr
import nodes.processors.ollama_summarize
import nodes.sinks.jsonl
import nodes.sinks.discord

router = APIRouter()


class PipelineCreate(BaseModel):
    name: str
    definition_yaml: str


@router.get("")
def list_pipelines():
    return get_db().list_pipelines()


@router.post("", status_code=201)
def create_pipeline(body: PipelineCreate):
    try:
        import yaml
        data = yaml.safe_load(body.definition_yaml)
        defn = PipelineDef(name=data["name"], nodes=data["nodes"], edges=data.get("edges") or [])
        defn.instantiate()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid pipeline: {exc}")
    pid = get_db().create_pipeline(body.name, body.definition_yaml)
    return get_db().get_pipeline(pid)


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int):
    p = get_db().get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="pipeline not found")
    return p


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: int):
    p = get_db().get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="pipeline not found")
    get_db().delete_pipeline(pipeline_id)


@router.post("/{pipeline_id}/start", status_code=200)
def start_pipeline(pipeline_id: int):
    p = get_db().get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="pipeline not found")

    runners = get_active_runners()
    if pipeline_id in runners:
        raise HTTPException(status_code=409, detail="pipeline already running")

    import yaml
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write(p["definition_yaml"])
    tmp.close()
    defn = load_pipeline(Path(tmp.name))
    node_instances = defn.instantiate()

    db = get_db()
    ctx = PipelineContext(pipeline_name=defn.name, db=db)
    runner = LinearRunner(defn, node_instances, ctx)
    runners[pipeline_id] = runner

    async def _run():
        try:
            await runner.run()
        finally:
            runners.pop(pipeline_id, None)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.ensure_future(_run())
    else:
        asyncio.run(_run())

    return {"status": "started", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/stop", status_code=200)
def stop_pipeline(pipeline_id: int):
    runners = get_active_runners()
    runner = runners.get(pipeline_id)
    if not runner:
        raise HTTPException(status_code=404, detail="pipeline not running")
    runner.stop()
    return {"status": "stopping", "pipeline_id": pipeline_id}
