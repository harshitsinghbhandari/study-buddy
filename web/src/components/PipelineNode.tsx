import type { NodeProps } from "@xyflow/react";
import { Handle, Position } from "@xyflow/react";
import {
  Monitor,
  Camera,
  FolderOpen,
  Filter,
  ScanText,
  Sparkles,
  FileText,
  MessageSquare,
} from "lucide-react";
import type { NodeDef } from "../lib/api";

const iconMap: Record<string, React.ReactNode> = {
  "source.screen": <Monitor size={16} />,
  "source.camera": <Camera size={16} />,
  "source.folder": <FolderOpen size={16} />,
  "processor.hash_dedup": <Filter size={16} />,
  "processor.ollama_ocr": <ScanText size={16} />,
  "processor.ollama_summarize": <Sparkles size={16} />,
  "sink.jsonl": <FileText size={16} />,
  "sink.discord": <MessageSquare size={16} />,
};

const kindColors: Record<string, string> = {
  source: "bg-emerald-900/60 border-emerald-500",
  processor: "bg-blue-900/60 border-blue-500",
  sink: "bg-purple-900/60 border-purple-500",
};

export function PipelineNode({ data }: NodeProps) {
  const nodeType = data.nodeType as string;
  const kind = nodeType?.split(".")[0] || "processor";
  const label = data.label as string;
  const icon = iconMap[nodeType] || <Filter size={16} />;
  const borderColor = kindColors[kind] || kindColors.processor;

  return (
    <div
      className={`px-3 py-2 rounded-lg border-2 ${borderColor} min-w-[140px]`}
    >
      {kind !== "source" && (
        <Handle type="target" position={Position.Left} className="!bg-white" />
      )}
      <div className="flex items-center gap-2 text-white text-sm font-medium">
        {icon}
        <span>{label}</span>
      </div>
      {kind !== "sink" && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-white"
        />
      )}
    </div>
  );
}

export function nodeTypeToLabel(t: string) {
  return t.split(".").pop()?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || t;
}

export function yamlToFlow(yaml: string) {
  const lines = yaml.split("\n");
  const nodes: Array<{ id: string; type: string; params: Record<string, unknown> }> = [];
  const edges: Array<[string, string]> = [];
  let inEdges = false;
  let currentNode: typeof nodes[0] | null = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "edges:") { inEdges = true; continue; }
    if (trimmed.startsWith("- id:") && !inEdges) {
      currentNode = { id: trimmed.split(":")[1].trim(), type: "", params: {} };
      nodes.push(currentNode);
    }
    if (trimmed.startsWith("type:") && currentNode && !inEdges) {
      currentNode.type = trimmed.split(":")[1].trim();
    }
    if (trimmed.startsWith("param") && currentNode && !inEdges) {
      const [k, ...rest] = trimmed.split(":");
      const key = k.trim();
      if (key === "params") continue;
      let val: unknown = rest.join(":").trim();
      try { val = JSON.parse(val as string); } catch {}
      currentNode.params[key] = val;
    }
    if (inEdges && trimmed.startsWith("- [")) {
      const match = trimmed.match(/\[(\S+),\s*(\S+)\]/);
      if (match) edges.push([match[1], match[2]]);
    }
  }

  const spacing = 220;
  const flowNodes = nodes.map((n, i) => ({
    id: n.id,
    type: "pipelineNode",
    position: { x: i * spacing + 50, y: 200 },
    data: { label: nodeTypeToLabel(n.type), nodeType: n.type, params: n.params },
  }));

  const flowEdges = edges.map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    animated: true,
    style: { stroke: "#64748b" },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

export { type NodeDef };
