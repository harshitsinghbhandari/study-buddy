const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface NodeDef {
  type: string;
  kind: "source" | "processor" | "sink";
  description: string;
  params_schema: Record<string, ParamField>;
}

export interface ParamField {
  type: "string" | "integer" | "float" | "boolean";
  required?: boolean;
  default?: unknown;
  description?: string;
}

export interface Pipeline {
  id: number;
  name: string;
  definition_yaml: string;
  created_at: string;
}

export interface Run {
  id: number;
  pipeline_id: number;
  status: string;
  started_at: string;
  stopped_at: string | null;
}

export interface Event {
  id: number;
  run_id: number;
  node_id: string;
  timestamp: string;
  kind: string;
  payload: Record<string, unknown>;
}

export const api = {
  listNodes: () => request<NodeDef[]>("/nodes"),

  listPipelines: () => request<Pipeline[]>("/pipelines"),
  getPipeline: (id: number) => request<Pipeline>(`/pipelines/${id}`),
  createPipeline: (name: string, definition_yaml: string) =>
    request<Pipeline>("/pipelines", {
      method: "POST",
      body: JSON.stringify({ name, definition_yaml }),
    }),
  deletePipeline: (id: number) =>
    request<void>(`/pipelines/${id}`, { method: "DELETE" }),

  startPipeline: (id: number) =>
    request<{ run_id: number }>(`/pipelines/${id}/start`, { method: "POST" }),
  stopPipeline: (id: number) =>
    request<void>(`/pipelines/${id}/stop`, { method: "POST" }),

  listRuns: (pipelineId?: number) => {
    const q = pipelineId ? `?pipeline_id=${pipelineId}` : "";
    return request<Run[]>(`/runs${q}`);
  },
  getRun: (id: number) => request<Run>(`/runs/${id}`),

  streamLogs: (runId: number, onEvent: (e: Event) => void) => {
    const ctrl = new AbortController();
    fetch(`${BASE}/runs/${runId}/logs`, { signal: ctrl.signal })
      .then((res) => {
        if (!res.ok || !res.body) throw new Error("SSE failed");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        function read() {
          reader
            .read()
            .then(({ done, value }) => {
              if (done) return;
              buf += decoder.decode(value, { stream: true });
              const lines = buf.split("\n");
              buf = lines.pop()!;
              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  try {
                    onEvent(JSON.parse(line.slice(6)));
                  } catch {}
                }
              }
              read();
            })
            .catch(() => {});
        }
        read();
      })
      .catch(() => {});
    return () => ctrl.abort();
  },
};
