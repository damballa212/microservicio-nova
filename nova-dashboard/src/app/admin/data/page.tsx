export default function DataPage() {
    return (
        <div className="p-8 flex flex-col justify-center items-center h-full text-center space-y-4">
            <div className="p-4 rounded-full bg-slate-900 border border-slate-800">
                <svg
                    className="w-8 h-8 text-slate-500"
                    fill="none"
                    height="24"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                    width="24"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <ellipse cx="12" cy="5" rx="9" ry="3" />
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
            </div>
            <div>
                <h2 className="text-xl font-semibold text-white">Data Management</h2>
                <p className="text-slate-400 mt-2">Manage knowledge base and vector stores.</p>
            </div>
            <div className="px-3 py-1 bg-yellow-900/30 border border-yellow-800 rounded-full text-yellow-500 text-xs font-medium">
                Work in Progress
            </div>
        </div>
    );
}
