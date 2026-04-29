from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_db

router = APIRouter()


@router.get("")
def list_runs(pipeline_id: int | None = None, limit: int = 50):
    return get_db().list_runs(pipeline_id)[:limit]


@router.get("/{run_id}")
def get_run(run_id: int):
    r = get_db().get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")
    return r


@router.get("/{run_id}/logs")
def stream_logs(run_id: int, limit: int = 100):
    r = get_db().get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")

    def event_stream():
        seen = 0
        while True:
            r_now = get_db().get_run(run_id)
            events = get_db().get_events(run_id, limit=50, offset=seen)
            for ev in events:
                yield f"data: {json.dumps(ev, default=str)}\n\n"
            seen += len(events)
            if r_now and r_now["status"] != "running":
                break
            time.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
