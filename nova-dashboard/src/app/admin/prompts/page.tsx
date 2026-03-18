"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Edit, FileText, Plus, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

interface PromptTemplate {
    id: number;
    name: string;
    version: number;
    description?: string;
    updated_at?: string;
    is_active: boolean;
}

import { API_ENDPOINTS } from "@/lib/api-config";

export default function PromptsPage() {
    const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
    const [loading, setLoading] = useState(true);

    const [activeTab, setActiveTab] = useState("all");

    useEffect(() => {
        const fetchPrompts = async () => {
            try {
                const res = await fetch(API_ENDPOINTS.PROMPTS);
                if (res.ok) {
                    const data = await res.json();
                    setPrompts(data);
                    // Default to first tab with data or Verticals
                    setActiveTab("verticals");
                }
            } catch (error) {
                console.error("Failed to fetch prompts", error);
            } finally {
                setLoading(false);
            }
        };
        fetchPrompts();
    }, []);

    const filteredPrompts = prompts.filter(prompt => {
        const name = prompt.name.toLowerCase();
        if (activeTab === "verticals") return name.includes("vertical");
        if (activeTab === "core") return name.includes("core");
        if (activeTab === "tenants") return name.includes("tenant");
        if (activeTab === "other") return !name.includes("vertical") && !name.includes("core") && !name.includes("tenant");
        return true;
    });

    if (loading) {
        return (
            <div className="p-8 flex justify-center items-center h-full text-slate-500">
                <Loader2 className="w-8 h-8 animate-spin" />
            </div>
        );
    }

    const tabs = [
        { id: "verticals", label: "Verticals", icon: <FileText className="w-4 h-4 mr-2" /> },
        { id: "core", label: "Core", icon: <FileText className="w-4 h-4 mr-2" /> },
        { id: "tenants", label: "Tenants", icon: <FileText className="w-4 h-4 mr-2" /> },
        { id: "other", label: "Other", icon: <FileText className="w-4 h-4 mr-2" /> },
    ];

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-white">Prompt Templates</h2>
                    <p className="text-slate-400 mt-2">Manage system prompts for Core, Verticals, and Tenants.</p>
                </div>
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                    <Plus className="w-4 h-4 mr-2" />
                    New Template
                </Button>
            </div>

            {/* Tabs */}
            <div className="flex space-x-2 border-b border-slate-800 pb-1">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === tab.id
                            ? "border-blue-500 text-blue-400"
                            : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
                            }`}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filteredPrompts.map((prompt) => (
                    <Card key={prompt.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <Badge variant={prompt.is_active ? "default" : "secondary"} className={prompt.is_active ? "bg-green-900 text-green-300 hover:bg-green-900" : "bg-slate-800 text-slate-400"}>
                                    v{prompt.version}
                                </Badge>
                                <Badge variant="outline" className="border-slate-700 text-slate-400 capitalize">
                                    {activeTab === 'other' ? 'System' : activeTab.slice(0, -1)}
                                </Badge>
                            </div>
                            <CardTitle className="text-xl text-white mt-2 truncate font-mono">
                                {prompt.name}
                            </CardTitle>
                            <CardDescription className="line-clamp-2 min-h-[40px]">
                                {prompt.description || "No description provided."}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between mt-2">
                                <span className="text-xs text-slate-500">
                                    Updated: {prompt.updated_at ? new Date(prompt.updated_at).toLocaleDateString() : 'N/A'}
                                </span>
                                <Link href={`/admin/prompts/${prompt.name}`}>
                                    <Button variant="outline" size="sm" className="border-slate-700 hover:bg-slate-800">
                                        <Edit className="w-3 h-3 mr-2" />
                                        Edit
                                    </Button>
                                </Link>
                            </div>
                        </CardContent>
                    </Card>
                ))}
                {filteredPrompts.length === 0 && (
                    <div className="col-span-full text-center p-12 bg-slate-900/50 border border-dashed border-slate-800 rounded-xl text-slate-500">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No prompt templates found for {activeTab}.</p>
                        <p className="text-sm mt-1">Create one or modify your search.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
