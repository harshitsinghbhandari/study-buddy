from __future__ import annotations

from fastapi import APIRouter

import nodes.sources.screen
import nodes.sources.camera
import nodes.sources.folder
import nodes.processors.hash_dedup
import nodes.processors.ollama_ocr
import nodes.processors.ollama_summarize
import nodes.sinks.jsonl
import nodes.sinks.discord
from runtime.registry import all_types

router = APIRouter()


@router.get("")
def list_nodes():
    result = []
    for name, cls in sorted(all_types().items()):
        result.append({"type": name, "kind": cls.node_kind, "class": cls.__name__, "schema": cls.schema()})
    return result
