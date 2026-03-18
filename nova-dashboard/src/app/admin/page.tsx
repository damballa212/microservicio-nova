"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Cpu, MessageSquare, Zap } from "lucide-react";

// Mock data - In real app, fetch from /metrics/summary
const stats = [
    {
        title: "Total Executions",
        value: "1,234",
        change: "+12%",
        icon: Activity,
        color: "text-blue-400",
    },
    {
        title: "Active Users",
        value: "56",
        change: "+3%",
        icon: Users,
        color: "text-green-400",
    },
    {
        title: "Avg. Latency",
        value: "230ms",
        change: "-5%",
        icon: Zap,
        color: "text-yellow-400",
    },
    {
        title: "Total Tokens",
        value: "450K",
        change: "+8%",
        icon: Cpu,
        color: "text-purple-400",
    },
];

import { Users } from "lucide-react";

export default function AdminPage() {
    return (
        <div className="p-8 space-y-8">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">Dashboard</h2>
                <p className="text-slate-400 mt-2">Overview of Nova AI performance and usage.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {stats.map((stat) => (
                    <Card key={stat.title} className="bg-slate-900 border-slate-800">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-slate-300">
                                {stat.title}
                            </CardTitle>
                            <stat.icon className={`h-4 w-4 ${stat.color}`} />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-white">{stat.value}</div>
                            <p className="text-xs text-slate-500 mt-1">
                                <span className={stat.change.startsWith("+") ? "text-green-500" : "text-red-500"}>
                                    {stat.change}
                                </span>{" "}
                                from last month
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4 bg-slate-900 border-slate-800">
                    <CardHeader>
                        <CardTitle className="text-white">Recent Activity</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[200px] flex items-center justify-center text-slate-500 text-sm">
                            Chart Placeholder (Recharts)
                        </div>
                    </CardContent>
                </Card>
                <Card className="col-span-3 bg-slate-900 border-slate-800">
                    <CardHeader>
                        <CardTitle className="text-white">System Health</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {["Redis", "Postgres", "LangGraph", "Flowify API"].map(service => (
                                <div key={service} className="flex items-center justify-between">
                                    <span className="text-sm text-slate-300">{service}</span>
                                    <span className="flex items-center text-xs text-green-400 gap-1">
                                        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                                        Operational
                                    </span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
