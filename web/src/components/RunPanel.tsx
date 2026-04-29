import { useState, useEffect, useRef } from "react";
import { api, type Event, type Run } from "../lib/api";
import { ScrollText, X } from "lucide-react";

interface Props {
  runId: number | null;
  onClose: () => void;
}

export function RunPanel({ runId, onClose }: Props) {
  const [events, setEvents] = useState<Event[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!runId) return;
    setEvents([]);
    api.getRun(runId).then(setRun).catch(() => {});
    const cancel = api.streamLogs(runId, (e) => {
      setEvents((prev) => [...prev.slice(-500), e]);
    });
    return cancel;
  }, [runId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  if (!runId) return null;

  const kindColor: Record<string, string> = {
    item_emitted: "text-emerald-400",
    item_consumed: "text-blue-400",
    error: "text-red-400",
    log: "text-zinc-400",
  };

  return (
    <div className="h-64 bg-zinc-900 border-t border-zinc-700 flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
        <span className="text-white text-sm font-medium flex items-center gap-2">
          <ScrollText size={14} /> Run #{runId}
          {run && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                run.status === "running"
                  ? "bg-emerald-800 text-emerald-300"
                  : "bg-zinc-700 text-zinc-400"
              }`}
            >
              {run.status}
            </span>
          )}
        </span>
        <button onClick={onClose} className="text-zinc-400 hover:text-white">
          <X size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-auto px-4 py-2 font-mono text-xs space-y-0.5">
        {events.map((e) => (
          <div key={e.id} className="flex gap-3">
            <span className="text-zinc-600 shrink-0">{e.timestamp.slice(11, 19)}</span>
            <span className="text-zinc-500 shrink-0 w-20 truncate">{e.node_id}</span>
            <span className={`shrink-0 w-24 ${kindColor[e.kind] || "text-zinc-400"}`}>
              {e.kind}
            </span>
            <span className="text-zinc-300 truncate">
              {Object.keys(e.payload).length > 0 ? JSON.stringify(e.payload) : ""}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
