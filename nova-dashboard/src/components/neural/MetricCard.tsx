
"use client";

import React, { useMemo, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Activity, Zap, Server, Database } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useDashboard } from "../providers/DashboardProvider";

interface MetricCardProps {
    title: string;
    value: string;
    unit?: string;
    trend?: string;
    trendUp?: boolean;
    icon: LucideIcon;
    color: "indigo" | "emerald" | "amber" | "rose" | "cyan";
}

export const MetricCard = ({ title, value, unit, trend, trendUp, icon: Icon, color }: MetricCardProps) => {
    const colorStyles = {
        indigo: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
        emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        rose: "text-rose-400 bg-rose-500/10 border-rose-500/20",
        cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    }[color];

    return (
        <div className="relative overflow-hidden rounded-xl border border-slate-800/60 bg-[#0f172a]/40 p-3 backdrop-blur-sm group hover:border-slate-700 transition-all">
            <div className="flex items-start justify-between mb-2">
                <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider text-nowrap">{title}</span>
                <div className={cn("p-1.5 rounded-lg", colorStyles)}>
                    <Icon className="w-3.5 h-3.5" />
                </div>
            </div>

            <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-slate-100 tabular-nums tracking-tight">{value}</span>
                {unit && <span className="text-xs text-slate-500 font-medium">{unit}</span>}
            </div>

            {trend && (
                <div className="mt-2 flex items-center gap-1.5">
                    <div className={cn("w-1.5 h-1.5 rounded-full", trendUp ? "bg-emerald-500" : "bg-slate-600")} />
                    <span className="text-[10px] text-slate-400 font-medium">{trend}</span>
                </div>
            )}
        </div>
    );
};

export const MetricGallery = () => {
    const { executions = {}, recentLogs = [], isConnected } = useDashboard();

    // 1. Calculate Active Threads
    const activeThreads = Object.values(executions).filter(e => e.status === "RUNNING").length;
    const maxThreads = 5; // Hard limit for demo visualization
    const loadPercentage = Math.min(Math.round((activeThreads / maxThreads) * 100), 100);

    // 2. Calculate Latency (deterministic placeholder based on logs length)
    const avgLatency = useMemo(() => {
        if (recentLogs.length === 0) return 0;
        const base = 800;
        const jitter = recentLogs.length % 150;
        return base + jitter;
    }, [recentLogs]);

    // 3. Token Counter (Simulated cumulative)
    const [tokenCount, setTokenCount] = useState(12400);
    useEffect(() => {
        if (activeThreads > 0) {
            const interval = setInterval(() => {
                setTokenCount(prev => prev + Math.floor(Math.random() * 10));
            }, 1000);
            return () => clearInterval(interval);
        }
    }, [activeThreads]);

    return (
        <div className="grid grid-cols-2 gap-3">
            <MetricCard
                title="Latency"
                value={isConnected ? avgLatency.toString() : "0"}
                unit="ms"
                icon={Zap}
                color="indigo"
                trend={isConnected ? "NORMAL" : "OFFLINE"}
                trendUp={false}
            />
            <MetricCard
                title="System Load"
                value={loadPercentage.toString()}
                unit="%"
                icon={Server}
                color="cyan"
                trend={activeThreads > 3 ? "High Traffic" : "Stable"}
                trendUp={activeThreads > 3}
            />
            <MetricCard
                title="Est. Tokens"
                value={(tokenCount / 1000).toFixed(1) + "k"}
                icon={Database}
                color="emerald"
                trend="+12/s"
                trendUp={true}
            />
            <MetricCard
                title="Active Threads"
                value={activeThreads.toString()}
                unit={`/ ${maxThreads}`}
                icon={Activity}
                color={activeThreads > 0 ? "amber" : "indigo"}
                trend={activeThreads === 0 ? "Idle" : "Processing"}
                trendUp={activeThreads > 0}
            />
        </div>
    );
};
