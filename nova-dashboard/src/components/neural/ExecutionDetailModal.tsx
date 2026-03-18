
"use client";

import React from "react";
import { X, Activity, Cpu, Hash, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

import type { ExecutionEvent, NodeEvent, LogEntry } from "../providers/DashboardProvider";

interface ExecutionDetailModalProps {
    execution: ExecutionEvent | null;
    isOpen: boolean;
    onClose: () => void;
}

export const ExecutionDetailModal = ({ execution, isOpen, onClose }: ExecutionDetailModalProps) => {
    // Lock body scroll when modal is open
    React.useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "unset";
        }
        return () => { document.body.style.overflow = "unset"; };
    }, [isOpen]);

    if (!isOpen || !execution) return null;

    const nodeArray = Object.values(execution.nodes || {}) as NodeEvent[];
    const logs = execution.logs || [] as LogEntry[];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-[#020617] border border-slate-800 w-full max-w-4xl max-h-[90vh] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-[#0f172a]/20">
                    <div className="flex items-center gap-4">
                        <div className={cn(
                            "p-2 rounded-lg bg-opacity-20",
                            execution.status === "COMPLETED" ? "bg-emerald-500 text-emerald-400" :
                                execution.status === "ERROR" ? "bg-red-500 text-red-400" : "bg-indigo-500 text-indigo-400"
                        )}>
                            <Activity size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                                Execution {execution.execution_id.slice(-8)}
                                <span className={cn(
                                    "text-[10px] px-2 py-0.5 rounded-full border",
                                    execution.status === "COMPLETED" ? "border-emerald-500/50 text-emerald-400 bg-emerald-500/10" :
                                        execution.status === "ERROR" ? "border-red-500/50 text-red-400 bg-red-500/10" : "border-indigo-500/50 text-indigo-400 bg-indigo-500/10"
                                )}>
                                    {execution.status}
                                </span>
                            </h2>
                            <p className="text-slate-400 text-sm font-mono mt-1">
                                {execution.identifier} • {execution.started_at ? new Date(execution.started_at).toLocaleString() : ""}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Left: Metadata & Trace */}
                    <div className="w-1/3 border-r border-slate-800 p-6 flex flex-col gap-6 overflow-y-auto custom-scrollbar bg-slate-900/10">
                        <section>
                            <h3 className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-4 px-1">Node Trace</h3>
                            <div className="space-y-3">
                                {nodeArray.map((node: NodeEvent, i) => (
                                    <div key={node.node_name} className="flex gap-3 relative">
                                        {i !== nodeArray.length - 1 && (
                                            <div className="absolute left-2.5 top-6 bottom-[-12px] w-px bg-slate-800" />
                                        )}
                                        <div className={cn(
                                            "w-5 h-5 rounded-full flex items-center justify-center z-10 text-[10px] font-bold border",
                                            node.status === "COMPLETED" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                                                node.status === "ERROR" ? "bg-red-500/20 text-red-400 border-red-500/30" : "bg-slate-800 text-slate-500 border-slate-700"
                                        )}>
                                            {i + 1}
                                        </div>
                                        <div className="flex-1">
                                            <div className="text-xs font-semibold text-slate-200">{node.node_name}</div>
                                            <div className="text-[10px] text-slate-500 font-mono">
                                                {node.duration_ms ? `${node.duration_ms}ms` : "pending..."}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section className="mt-auto pt-6 border-t border-slate-800/50 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 rounded-lg bg-slate-800/20 border border-slate-700/30">
                                    <div className="text-slate-500 text-[9px] uppercase font-mono mb-1 flex items-center gap-1">
                                        <Cpu size={10} /> Cost
                                    </div>
                                    <div className="text-slate-200 text-sm font-bold">{execution.cost || "0.0000"}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-800/20 border border-slate-700/30">
                                    <div className="text-slate-500 text-[9px] uppercase font-mono mb-1 flex items-center gap-1">
                                        <Hash size={10} /> Tokens
                                    </div>
                                    <div className="text-slate-200 text-sm font-bold">{execution.tokens || "0"}</div>
                                </div>
                            </div>
                        </section>
                    </div>

                    {/* Right: Detailed Logs */}
                    <div className="flex-1 flex flex-col bg-[#010409]">
                        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
                            <Terminal size={14} className="text-indigo-400" />
                            <h3 className="text-[10px] font-mono uppercase tracking-widest text-slate-300">Detailed Execution Stream</h3>
                        </div>
                        <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                            <div className="space-y-4 font-mono text-xs">
                                {logs.length > 0 ? logs.map((log: LogEntry, i: number) => (
                                    <div key={i} className="flex gap-3">
                                        <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                                        <div className="flex-1 min-w-0">
                                            <span className={cn(
                                                "px-1.5 py-0.5 rounded mr-2 text-[10px]",
                                                log.level === "error" ? "bg-red-500/20 text-red-400" : "bg-slate-800 text-slate-400"
                                            )}>
                                                {log.node_name || "core"}
                                            </span>
                                            <span className="text-slate-300 wrap-break-word">{log.message}</span>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="text-slate-600 italic">No detailed logs found for this execution.</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
