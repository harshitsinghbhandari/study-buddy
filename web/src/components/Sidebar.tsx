import { useState, useEffect } from "react";
import { api, type Pipeline } from "../lib/api";
import { Plus, Trash2, Play, Square, Workflow } from "lucide-react";

interface Props {
  selected: number | null;
  onSelect: (id: number) => void;
  onRunStarted: (runId: number) => void;
  onRunStopped: () => void;
}

export function Sidebar({ selected, onSelect, onRunStarted, onRunStopped }: Props) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [yaml, setYaml] = useState("");

  const load = () => api.listPipelines().then(setPipelines).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!name || !yaml) return;
    await api.createPipeline(name, yaml);
    setName("");
    setYaml("");
    setCreating(false);
    load();
  };

  const handleDelete = async (id: number) => {
    await api.deletePipeline(id);
    load();
  };

  const handleStart = async (id: number) => {
    const { run_id } = await api.startPipeline(id);
    onRunStarted(run_id);
  };

  const handleStop = async (id: number) => {
    await api.stopPipeline(id);
    onRunStopped();
  };

  const defaultYaml = `name: new-pipeline
nodes:
  - id: grab
    type: source.screen
    params:
      crop_box: [350, 250, 1350, 850]
      interval: 10
  - id: dedup
    type: processor.hash_dedup
  - id: ocr
    type: processor.ollama_ocr
    params:
      model: deepseek-ocr
  - id: out
    type: sink.jsonl
    params:
      path: data/ocr-output/responses.jsonl
edges:
  - [grab, dedup]
  - [dedup, ocr]
  - [ocr, out]`;

  return (
    <div className="w-72 bg-zinc-900 border-r border-zinc-700 flex flex-col h-full">
      <div className="p-4 border-b border-zinc-700 flex items-center justify-between">
        <h1 className="text-white font-semibold flex items-center gap-2">
          <Workflow size={18} /> Pipelines
        </h1>
        <button
          onClick={() => { setCreating(true); setYaml(defaultYaml); }}
          className="text-zinc-400 hover:text-white"
        >
          <Plus size={18} />
        </button>
      </div>

      {creating && (
        <div className="p-3 border-b border-zinc-700 space-y-2">
          <input
            className="w-full bg-zinc-800 text-white text-sm px-2 py-1 rounded border border-zinc-600"
            placeholder="Pipeline name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <textarea
            className="w-full bg-zinc-800 text-white text-xs px-2 py-1 rounded border border-zinc-600 font-mono h-48"
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-sm py-1 rounded"
            >
              Create
            </button>
            <button
              onClick={() => setCreating(false)}
              className="flex-1 bg-zinc-700 hover:bg-zinc-600 text-white text-sm py-1 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {pipelines.map((p) => (
          <div
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`p-3 border-b border-zinc-800 cursor-pointer flex items-center justify-between group ${
              selected === p.id ? "bg-zinc-800" : "hover:bg-zinc-800/50"
            }`}
          >
            <span className="text-white text-sm truncate flex-1">{p.name}</span>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => { e.stopPropagation(); handleStart(p.id); }}
                className="text-emerald-400 hover:text-emerald-300"
                title="Start"
              >
                <Play size={14} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleStop(p.id); }}
                className="text-orange-400 hover:text-orange-300"
                title="Stop"
              >
                <Square size={14} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                className="text-red-400 hover:text-red-300"
                title="Delete"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
        {pipelines.length === 0 && (
          <p className="text-zinc-500 text-sm p-4">No pipelines yet.</p>
        )}
      </div>
    </div>
  );
}
