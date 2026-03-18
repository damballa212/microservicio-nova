"use client";

import { ChatSidebar } from "@/components/neural/ChatSidebar";
import { LogSidebar } from "@/components/neural/LogSidebar";
import { ExecutionDetailModal } from "@/components/neural/ExecutionDetailModal";
import { NeuralGraph } from "@/components/neural/NeuralGraph";
import { useDashboard } from "@/components/providers/DashboardProvider";
import { DashboardProvider } from "@/components/providers/DashboardProvider";

export default function DashboardPage() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
}

function DashboardContent() {
  const { modalExecution, setModalExecution } = useDashboard();

  return (
    <div className="flex h-screen w-screen bg-[#020617] text-slate-200 overflow-hidden font-sans">

      {/* LEFT: Communication (Chat) */}
      <aside className="w-[320px] h-full border-r border-slate-800 shrink-0 z-20 shadow-xl">
        <ChatSidebar />
      </aside>

      {/* CENTER: Visualization (Graph) */}
      <main className="flex-1 min-w-0 h-full relative z-10 bg-[radial-gradient(circle_at_center,#0f172a_0%,#020617_100%)]">
        <NeuralGraph />
      </main>

      {/* RIGHT: Telemetry (Logs & Metrics) */}
      <aside className="w-[380px] h-full border-l border-slate-800 shrink-0 z-20 shadow-xl">
        <LogSidebar />
      </aside>

      {/* Global Modal */}
      <ExecutionDetailModal
        execution={modalExecution}
        isOpen={!!modalExecution}
        onClose={() => setModalExecution(null)}
      />
    </div>
  );
}
