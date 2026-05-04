import { ReactNode } from "react";

export function Topbar({ title, children, status }: { title: string; children?: ReactNode; status?: ReactNode }) {
  return (
    <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-200 px-8 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">{title}</h1>
        {status}
      </div>
      <div className="flex items-center gap-3">
        {children}
      </div>
    </div>
  );
}

export function StatusPill({ children, tone }: { children?: ReactNode; tone?: string }) {
  const map: Record<string, string> = {
    brand: "bg-blue-100 text-blue-800 border-blue-200",
    ok: "bg-emerald-100 text-emerald-800 border-emerald-200",
    warning: "bg-orange-100 text-orange-800 border-orange-200",
    danger: "bg-rose-100 text-rose-800 border-rose-200",
    offline: "bg-gray-100 text-gray-800 border-gray-200"
  };
  
  const state = tone || "offline";
  return (
    <div className={`px-3 py-1.5 rounded-full text-xs font-semibold border flex items-center gap-2 shadow-sm ${map[state] || map.offline}`}>
      <span className="relative flex h-2 w-2">
        {state === 'ok' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${state === 'ok' ? 'bg-emerald-500' : 'bg-current'}`}></span>
      </span>
      {children}
    </div>
  );
}
