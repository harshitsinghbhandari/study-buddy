import tempfile
from pathlib import Path

from runtime.loader import load_pipeline

import nodes.sources.screen
import nodes.sources.camera
import nodes.processors.hash_dedup
import nodes.processors.ollama_ocr
import nodes.sinks.jsonl


def _yaml(text):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(text)
    f.close()
    return Path(f.name)


def test_load_screen_ocr():
    p = _yaml("""
name: test-pipeline
nodes:
  - id: src
    type: source.screen
    params:
      interval: 5
  - id: dedup
    type: processor.hash_dedup
  - id: sink
    type: sink.jsonl
edges:
  - [src, dedup]
  - [dedup, sink]
""")
    defn = load_pipeline(p)
    assert defn.name == "test-pipeline"
    assert len(defn.nodes) == 3
    assert len(defn.edges) == 2
    nodes = defn.instantiate()
    assert len(nodes) == 3
    assert nodes[0].name == "src"
    assert nodes[0].node_kind == "source"
    assert nodes[1].name == "dedup"
    assert nodes[2].name == "sink"


def test_linear_topo_sort():
    p = _yaml("""
name: linear
nodes:
  - id: a
    type: source.screen
  - id: b
    type: processor.hash_dedup
  - id: c
    type: sink.jsonl
edges:
  - [a, b]
  - [b, c]
""")
    defn = load_pipeline(p)
    nodes = defn.instantiate()
    names = [n.name for n in nodes]
    assert names.index("a") < names.index("b") < names.index("c")
