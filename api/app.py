from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.db import Database
from api.dependencies import set_db, get_active_runners
from api.routes import nodes, pipelines, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = getattr(app.state, "db_path", "screen_ocr.db")
    database = Database(db_path)
    database.conn
    set_db(database)
    yield
    for runner in list(get_active_runners().values()):
        runner.stop()
    database.close()


def create_app(db_path: str = "screen_ocr.db") -> FastAPI:
    app = FastAPI(title="Screen OCR Pipeline API", version="0.2.0")
    app.state.db_path = db_path

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
    app.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
    app.include_router(runs.router, prefix="/runs", tags=["runs"])

    return app
