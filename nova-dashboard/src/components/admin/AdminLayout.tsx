"use client";

import { LayoutDashboard, Settings, FileText, Database, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const NAV_ITEMS = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Settings", href: "/admin/settings", icon: Settings },
    { label: "Prompts", href: "/admin/prompts", icon: FileText },
    { label: "Knowledge", href: "/admin/rag", icon: Database },
    { label: "Data", href: "/admin/data", icon: FileText },
    { label: "Users", href: "/admin/users", icon: Users },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
    const pathname = usePathname();

    return (
        <div className="flex h-screen bg-[#020617] text-slate-200 font-sans overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 border-r border-slate-800 bg-[#020617] flex flex-col">
                <div className="p-6">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                        NOVA Admin
                    </h1>
                    <p className="text-xs text-slate-500 mt-1">v2.1 Control Center</p>
                </div>

                <nav className="flex-1 px-4 py-2 space-y-1">
                    {NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive
                                    ? "bg-slate-800 text-blue-400"
                                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                                    }`}
                            >
                                <item.icon className="w-4 h-4" />
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
                            <span className="text-xs font-bold">AD</span>
                        </div>
                        <div className="text-xs">
                            <p className="font-medium text-slate-200">Admin User</p>
                            <p className="text-slate-500">super@nova.ai</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
                {children}
            </main>
        </div>
    );
}
