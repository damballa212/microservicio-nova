
"use client";

import React from "react";
import { Activity, ChevronDown, History } from "lucide-react";
import { LogTimeline } from "./LogTimeline";
import { MetricGallery } from "./MetricCard";
import { cn } from "@/lib/utils";

export const LogSidebar = () => {
    const [metricsExpanded, setMetricsExpanded] = React.useState(true);
    const [logsExpanded, setLogsExpanded] = React.useState(true);

    return (
        <div className="flex flex-col h-full bg-[#020617]/80 backdrop-blur-xl border-l border-slate-800/50">
            {/* Metrics Section */}
            <div className={cn("flex flex-col border-b border-slate-800/50 transition-all duration-300", metricsExpanded ? "shrink-0" : "h-12")}>
                <div
                    className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/20"
                    onClick={() => setMetricsExpanded(!metricsExpanded)}
                >
                    <div className="flex items-center gap-2 text-slate-400">
                        <Activity className="w-4 h-4 text-indigo-400" />
                        <span className="text-[10px] font-mono uppercase tracking-wider">Live Telemetry</span>
                    </div>
                    <ChevronDown className={cn("w-4 h-4 text-slate-500 transition-transform", !metricsExpanded && "-rotate-90")} />
                </div>
                {metricsExpanded && (
                    <div className="p-4 pt-0">
                        <MetricGallery />
                    </div>
                )}
            </div>

            {/* Logs Section */}
            <div className="flex-1 min-h-0 flex flex-col">
                <div
                    className="h-12 border-b border-slate-800/50 flex items-center justify-between px-4 bg-[#0f172a]/50 cursor-pointer hover:bg-slate-800/20"
                    onClick={() => setLogsExpanded(!logsExpanded)}
                >
                    <div className="flex items-center">
                        <History className="w-4 h-4 text-slate-500 mr-2" />
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-300 font-semibold">Pipeline History</span>
                    </div>
                    <ChevronDown className={cn("w-4 h-4 text-slate-500 transition-transform", !logsExpanded && "-rotate-90")} />
                </div>

                {logsExpanded && (
                    <div className="flex-1 min-h-0 flex flex-col overflow-hidden relative">
                        <LogTimeline />
                    </div>
                )}
            </div>
        </div>
    );
};
