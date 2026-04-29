import { useState, useEffect, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, type Pipeline } from "../lib/api";
import { PipelineNode, yamlToFlow } from "./PipelineNode";

const nodeTypes = { pipelineNode: PipelineNode };

interface Props {
  pipelineId: number | null;
}

export function Canvas({ pipelineId }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);

  const loadPipeline = useCallback(async () => {
    if (!pipelineId) {
      setNodes([]);
      setEdges([]);
      setPipeline(null);
      return;
    }
    try {
      const p = await api.getPipeline(pipelineId);
      setPipeline(p);
      const { nodes: fn, edges: fe } = yamlToFlow(p.definition_yaml);
      setNodes(fn);
      setEdges(fe);
    } catch {
      setNodes([]);
      setEdges([]);
      setPipeline(null);
    }
  }, [pipelineId, setNodes, setEdges]);

  useEffect(() => { loadPipeline(); }, [loadPipeline]);

  if (!pipelineId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zinc-950 text-zinc-500 text-sm">
        Select a pipeline from the sidebar
      </div>
    );
  }

  return (
    <div className="flex-1 bg-zinc-950">
      <div className="px-4 py-2 border-b border-zinc-800 bg-zinc-900 flex items-center gap-3">
        <h2 className="text-white text-sm font-medium">{pipeline?.name}</h2>
        <span className="text-zinc-500 text-xs">#{pipelineId}</span>
      </div>
      <div className="h-[calc(100vh-3rem-2.5rem)]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Controls className="!bg-zinc-800 !border-zinc-700 [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!fill-white" />
          <Background color="#334155" gap={20} />
        </ReactFlow>
      </div>
    </div>
  );
}
