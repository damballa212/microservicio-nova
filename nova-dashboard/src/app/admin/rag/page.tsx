"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { API_ENDPOINTS } from "@/lib/api-config";
import { Database, FileText, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";
import { useEffect, useState, useRef } from "react";
// import { toast } from "sonner";

interface RagDocument {
    doc_id: string;
    title: string;
    mime: string;
    tags: string;
    created_at: string | null;
}

export default function RagPage() {
    const [documents, setDocuments] = useState<RagDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [empresaId, setEmpresaId] = useState("1"); // Default test ID
    const [tags, setTags] = useState("");
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchDocuments();
    }, [empresaId]); // Refetch when empresaId changes

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_ENDPOINTS.RAG}/documents/${empresaId}`);
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data)) {
                    setDocuments(data);
                } else {
                    setDocuments([]);
                }
            } else {
                setDocuments([]);
            }
        } catch (error) {
            console.error("Failed to fetch documents", error);
            setDocuments([]);
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!fileInputRef.current?.files?.[0]) return;

        setUploading(true);
        const file = fileInputRef.current.files[0];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("empresa_id", empresaId);
        formData.append("empresa_slug", "generic-slug"); // You might want input for this or default
        formData.append("tags", tags);

        try {
            const res = await fetch(`${API_ENDPOINTS.RAG}/ingest/upload`, {
                method: "POST",
                body: formData,
            });

            if (res.ok) {
                // toast.success("Document uploaded successfully");
                alert("Document uploaded successfully");
                if (fileInputRef.current) fileInputRef.current.value = "";
                setTags("");
                fetchDocuments();
            } else {
                // toast.error("Upload failed");
                alert("Upload failed");
                console.error("Upload failed");
            }
        } catch (error) {
            console.error("Upload error", error);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (docId: string) => {
        if (!confirm("Are you sure you want to delete this document?")) return;

        try {
            const res = await fetch(`${API_ENDPOINTS.RAG}/documents/${empresaId}/${docId}`, {
                method: "DELETE",
            });
            if (res.ok) {
                fetchDocuments();
            } else {
                console.error("Delete failed");
            }
        } catch (error) {
            console.error("Delete error", error);
        }
    };

    return (
        <div className="h-full flex flex-col bg-[#020617]">
            {/* Header */}
            <div className="shrink-0 px-8 pt-6 pb-4 border-b border-slate-800/50 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/30">
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                                <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-600 shadow-lg shadow-indigo-500/20">
                                    <Database className="w-5 h-5 text-white" />
                                </div>
                                Knowledge Base
                            </h1>
                            <p className="text-slate-400 mt-1 ml-12">Manage documents and RAG ingestion</p>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchDocuments}
                            className="text-slate-400 hover:text-white"
                        >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Refresh
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto px-8 py-6">
                <div className="max-w-7xl mx-auto space-y-6">

                    {/* Upload Card */}
                    <Card className="bg-slate-900/50 border-slate-800">
                        <CardHeader>
                            <CardTitle className="text-white text-lg flex items-center gap-2">
                                <Upload className="w-5 h-5 text-indigo-400" />
                                Ingest New Document
                            </CardTitle>
                            <CardDescription className="text-slate-400">
                                Upload text files, PDFs, or CSVs to add them to the vector search index.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleUpload} className="grid md:grid-cols-4 gap-4 items-end">
                                <div className="space-y-2">
                                    <Label className="text-slate-300">Tenant/Empresa ID</Label>
                                    <Input
                                        value={empresaId}
                                        onChange={(e) => setEmpresaId(e.target.value)}
                                        className="bg-slate-950 border-slate-700 text-white"
                                        placeholder="e.g. 1"
                                    />
                                </div>
                                <div className="space-y-2 md:col-span-2">
                                    <Label className="text-slate-300">File</Label>
                                    <Input
                                        type="file"
                                        ref={fileInputRef}
                                        className="bg-slate-950 border-slate-700 text-slate-300 file:bg-slate-800 file:text-indigo-400 file:border-0 file:rounded-md cursor-pointer"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-slate-300">Tags (comma separated)</Label>
                                    <Input
                                        value={tags}
                                        onChange={(e) => setTags(e.target.value)}
                                        className="bg-slate-950 border-slate-700 text-white"
                                        placeholder="manual, policies"
                                    />
                                </div>
                                <div className="md:col-span-4">
                                    <Button
                                        type="submit"
                                        className="bg-indigo-600 hover:bg-indigo-700 w-full md:w-auto"
                                        disabled={uploading}
                                    >
                                        {uploading ? (
                                            <>
                                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                Ingesting...
                                            </>
                                        ) : (
                                            <>
                                                <Upload className="w-4 h-4 mr-2" />
                                                Start Ingestion
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Documents List */}
                    <Card className="bg-slate-900/50 border-slate-800">
                        <CardHeader>
                            <CardTitle className="text-white text-lg flex items-center gap-2">
                                <FileText className="w-5 h-5 text-emerald-400" />
                                Parameters & Documents
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <div className="flex justify-center py-8">
                                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                                </div>
                            ) : documents.length === 0 ? (
                                <div className="text-center py-8 text-slate-500 bg-slate-950/30 rounded-lg border border-slate-800/50 border-dashed">
                                    <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
                                    <p>No documents found for User ID {empresaId}.</p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-slate-300 text-sm">
                                        <thead>
                                            <tr className="border-b border-slate-800 text-left">
                                                <th className="py-3 px-4 font-medium text-slate-500">Document ID</th>
                                                <th className="py-3 px-4 font-medium text-slate-500">Title / Name</th>
                                                <th className="py-3 px-4 font-medium text-slate-500">Type</th>
                                                <th className="py-3 px-4 font-medium text-slate-500">Tags</th>
                                                <th className="py-3 px-4 font-medium text-slate-500">Ingested At</th>
                                                <th className="py-3 px-4 font-medium text-slate-500 text-right">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800">
                                            {documents.map((doc) => (
                                                <tr key={doc.doc_id} className="hover:bg-slate-800/50 transition-colors">
                                                    <td className="py-3 px-4 font-mono text-xs text-slate-500 truncate max-w-[120px]" title={doc.doc_id}>
                                                        {doc.doc_id}
                                                    </td>
                                                    <td className="py-3 px-4 font-medium text-white">
                                                        {doc.title || "Untitled Document"}
                                                    </td>
                                                    <td className="py-3 px-4">
                                                        <Badge variant="outline" className="border-slate-700 text-slate-400 text-[10px] uppercase">
                                                            {doc.mime || "text/plain"}
                                                        </Badge>
                                                    </td>
                                                    <td className="py-3 px-4">
                                                        <div className="flex gap-1 flex-wrap">
                                                            {doc.tags?.split(',').filter(Boolean).map((tag, i) => (
                                                                <span key={i} className="bg-indigo-500/10 text-indigo-400 px-1.5 py-0.5 rounded text-[10px]">
                                                                    #{tag.trim()}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </td>
                                                    <td className="py-3 px-4 text-slate-500 text-xs">
                                                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "-"}
                                                    </td>
                                                    <td className="py-3 px-4 text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="text-slate-500 hover:text-red-400 hover:bg-red-950/30"
                                                            onClick={() => handleDelete(doc.doc_id)}
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </Button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
