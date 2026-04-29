import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Canvas } from "./components/Canvas";
import { RunPanel } from "./components/RunPanel";

export default function App() {
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);

  return (
    <div className="flex h-screen bg-zinc-950">
      <Sidebar
        selected={selectedPipeline}
        onSelect={setSelectedPipeline}
        onRunStarted={setActiveRunId}
        onRunStopped={() => {}}
      />
      <Canvas pipelineId={selectedPipeline} />
      <RunPanel runId={activeRunId} onClose={() => setActiveRunId(null)} />
    </div>
  );
}
