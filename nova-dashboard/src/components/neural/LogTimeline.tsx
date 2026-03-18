
"use client";

import React, { useState, useMemo } from "react";
import { useDashboard } from "../providers/DashboardProvider";
import type { ExecutionEvent } from "../providers/DashboardProvider";
import { cn } from "@/lib/utils";
import { History, Activity, Clock, ChevronRight, Search, PlayCircle, CheckCircle2, AlertCircle } from "lucide-react";

export const LogTimeline = () => {
    const { executions = {}, activeExecutionId, setActiveExecutionId } = useDashboard();
    const [search, setSearch] = useState("");

    const executionList = useMemo(() => {
        return Object.values(executions)
            .sort((a: ExecutionEvent, b: ExecutionEvent) => {
                const timeA = a.started_at ? new Date(a.started_at).getTime() : 0;
                const timeB = b.started_at ? new Date(b.started_at).getTime() : 0;
                return timeB - timeA;
            });
    }, [executions]);

    const filteredExecutions = executionList.filter((ex: ExecutionEvent) =>
        ex.execution_id.toLowerCase().includes(search.toLowerCase()) ||
        ex.identifier?.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="flex-1 min-h-0 flex flex-col bg-transparent overflow-hidden">
            {/* Search Bar */}
            <div className="p-3 border-b border-slate-800/50 bg-[#0f172a]/20">
                <div className="relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" size={14} />
                    <input
                        type="text"
                        placeholder="Filter transactions..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-[#020617] border border-slate-800 rounded-lg py-2 pl-9 pr-4 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-3 space-y-2">
                    {filteredExecutions.map((ex: ExecutionEvent) => (
                        <ExecutionItem
                            key={ex.execution_id}
                            execution={ex}
                            isActive={activeExecutionId === ex.execution_id}
                            onClick={() => setActiveExecutionId(ex.execution_id)}
                        />
                    ))}

                    {filteredExecutions.length === 0 && (
                        <div className="py-20 flex flex-col items-center justify-center text-slate-600 italic gap-2 px-10 text-center">
                            <History size={32} strokeWidth={1} className="opacity-20" />
                            <span className="text-xs">No execution records found matching your filter.</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

interface ExecutionItemProps {
    execution: ExecutionEvent;
    isActive: boolean;
    onClick: () => void;
}

const ExecutionItem = ({ execution, isActive, onClick }: ExecutionItemProps) => {
    const { setModalExecution } = useDashboard();
    const status = execution.status || "RUNNING";
    const nodeCount = Object.keys(execution.nodes || {}).length;

    const StatusIcon = status === "COMPLETED" ? CheckCircle2 : (status === "ERROR" ? AlertCircle : PlayCircle);
    const statusColor = status === "COMPLETED" ? "text-emerald-400" : (status === "ERROR" ? "text-red-400" : "text-indigo-400");

    return (
        <div
            className={cn(
                "group relative overflow-hidden flex flex-col p-3 rounded-lg border cursor-pointer transition-all hover:bg-slate-800/10",
                isActive ? "bg-indigo-500/5 border-indigo-500/30" : "bg-slate-900/20 border-slate-800/50 hover:border-slate-700"
            )}
            onClick={onClick}
        >
            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2 min-w-0">
                    <StatusIcon size={12} className={cn("shrink-0", statusColor)} />
                    <span className="text-[10px] font-mono text-slate-400 truncate">
                        ID: {execution.execution_id.slice(-8)}
                    </span>
                    {isActive && (
                        <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
                    )}
                </div>
                <span className="text-[9px] text-slate-600 tabular-nums">
                    {execution.started_at ? new Date(execution.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
                </span>
            </div>

            <div className="mb-3 px-1">
                <div className="text-xs font-semibold text-slate-200 truncate group-hover:text-indigo-300 transition-colors">
                    {execution.identifier || "System Process"}
                </div>
                <div className="text-[9px] text-slate-500 mt-1 flex items-center gap-3">
                    <span className="flex items-center gap-1"><Activity size={10} /> {nodeCount} nodes</span>
                    <span className="flex items-center gap-1"><Clock size={10} /> {execution.tokens || 0} tok</span>
                </div>
            </div>

            <div className="flex justify-between items-center px-1">
                <div className="flex-1 h-0.5 bg-slate-800 rounded-full overflow-hidden mr-3">
                    <div
                        className={cn("h-full transition-all duration-500", status === "COMPLETED" ? "bg-emerald-500 w-full" : "bg-indigo-500 w-1/3 animate-pulse")}
                    />
                </div>
                <button
                    className="p-1 hover:bg-slate-700 rounded-md text-slate-400 opacity-60 hover:opacity-100 transition-all flex items-center gap-1 group/btn"
                    onClick={(e) => { e.stopPropagation(); setModalExecution(execution); }}
                >
                    <span className="text-[9px] font-bold uppercase tracking-tighter group-hover/btn:text-indigo-300">Details</span>
                    <ChevronRight size={10} />
                </button>
            </div>
        </div>
    );
};
