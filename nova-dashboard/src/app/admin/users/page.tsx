export default function UsersPage() {
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
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
            </div>
            <div>
                <h2 className="text-xl font-semibold text-white">User Management</h2>
                <p className="text-slate-400 mt-2">Manage admin users and permissions.</p>
            </div>
            <div className="px-3 py-1 bg-yellow-900/30 border border-yellow-800 rounded-full text-yellow-500 text-xs font-medium">
                Work in Progress
            </div>
        </div>
    );
}
