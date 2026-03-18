"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Save, Loader2, History } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { API_ENDPOINTS } from "@/lib/api-config";

interface PromptTemplate {
    id: number;
    name: string;
    content: string;
    version: number;
    description?: string;
    updated_at?: string;
    updated_by?: string;
}

export default function EditPromptPage() {
    const params = useParams();
    const router = useRouter();
    const name = params.name as string;

    const [prompt, setPrompt] = useState<PromptTemplate | null>(null);
    const [content, setContent] = useState("");
    const [description, setDescription] = useState("");

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);



    useEffect(() => {
        const fetchPrompt = async () => {
            try {
                // Decode name in case of special chars, though usually prompts are safe slugs
                const decodedName = decodeURIComponent(name);
                const res = await fetch(`${API_ENDPOINTS.PROMPTS}/${decodedName}`);
                if (res.ok) {
                    const data = await res.json();
                    setPrompt(data);
                    setContent(data.content);
                    setDescription(data.description || "");
                } else {
                    // Handle 404
                }
            } catch (error) {
                console.error("Failed to fetch prompt", error);
            } finally {
                setLoading(false);
            }
        };
        fetchPrompt();
    }, [name]);

    const handleSave = async () => {
        if (!prompt) return;
        setSaving(true);
        try {
            const res = await fetch(API_ENDPOINTS.PROMPTS, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: prompt.name,
                    content: content,
                    description: description,
                    // user info would come from auth context
                }),
            });

            if (res.ok) {
                // Refresh data to get new version number
                const refreshReq = await fetch(`${API_ENDPOINTS.PROMPTS}/${prompt.name}`);
                const savedData = await refreshReq.json();
                setPrompt(savedData);
                // Maybe show toast success
            }
        } catch (error) {
            console.error("Failed to save", error);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="p-8 flex justify-center items-center h-full text-slate-500">
                <Loader2 className="w-8 h-8 animate-spin" />
            </div>
        );
    }

    if (!prompt) {
        return (
            <div className="p-8 text-center text-slate-500">
                <p>Prompt not found.</p>
                <Link href="/admin/prompts" className="text-blue-400 hover:underline mt-4 inline-block">
                    Go back
                </Link>
            </div>
        )
    }

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-6 h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-4">
                    <Link href="/admin/prompts">
                        <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white hover:bg-slate-800">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                    </Link>
                    <div>
                        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                            {prompt.name}
                            <Badge variant="secondary" className="bg-slate-800 text-blue-300">
                                v{prompt.version}
                            </Badge>
                        </h2>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 mr-2">
                        Last updated by {prompt.updated_by || 'system'}
                    </span>
                    <Button
                        onClick={handleSave}
                        disabled={saving || (content === prompt.content && description === (prompt.description || ""))}
                        className="bg-blue-600 hover:bg-blue-700 min-w-[100px]"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                            <>
                                <Save className="w-4 h-4 mr-2" />
                                Save
                            </>
                        )}
                    </Button>
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-3 flex-1 min-h-0">
                {/* Metadata Column */}
                <div className="space-y-6">
                    <Card className="bg-slate-900 border-slate-800">
                        <CardHeader>
                            <CardTitle className="text-white text-base">Metadata</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-slate-400">Description</Label>
                                <Textarea
                                    rows={3}
                                    className="bg-slate-950 border-slate-700 text-slate-300 resize-none focus-visible:ring-blue-900"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-slate-400">Variables</Label>
                                <div className="bg-slate-950 rounded-md p-3 text-xs font-mono text-slate-500 border border-slate-800">
                                    Detecting variables... <br />
                                    {/* Simple regex to find {{vars}} could go here */}
                                    No variables detected.
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-900 border-slate-800 opacity-50">
                        <CardHeader>
                            <CardTitle className="text-white text-base flex items-center gap-2">
                                <History className="w-4 h-4" /> History
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-xs text-slate-500">Version history not implemented yet.</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Editor Column */}
                <div className="lg:col-span-2 h-full flex flex-col">
                    <Card className="bg-slate-900 border-slate-800 flex-1 flex flex-col min-h-[500px]">
                        <CardHeader className="bg-slate-950/50 border-b border-slate-800 py-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-mono text-slate-500">PROMPT CONTENT</span>
                                <div className="flex gap-2">
                                    {/* Toolbar buttons could go here */}
                                </div>
                            </div>
                        </CardHeader>
                        <div className="flex-1 relative">
                            <Textarea
                                className="absolute inset-0 w-full h-full resize-none bg-slate-950 text-slate-300 font-mono text-sm leading-relaxed p-6 border-0 focus-visible:ring-0 rounded-none rounded-b-lg"
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                spellCheck={false}
                            />
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
