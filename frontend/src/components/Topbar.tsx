import { ReactNode } from "react";

export function Topbar({
  title,
  status,
  children,
}: {
  title: string;
  status?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="h-14 px-8 border-b border-border flex items-center gap-4 bg-bg-0 sticky top-0 z-10">
      <span className="font-semibold text-[15px] tracking-tight">{title}</span>
      {status}
      <div className="flex-1" />
      {children}
    </header>
  );
}

export function StatusPill({
  tone = "ok",
  children,
}: {
  tone?: "ok" | "warn" | "err";
  children: ReactNode;
}) {
  const dotColor =
    tone === "warn" ? "bg-warning shadow-[0_0_0_2px_rgba(245,158,11,0.18)]" :
    tone === "err"  ? "bg-danger shadow-[0_0_0_2px_rgba(239,68,68,0.2)]" :
                       "bg-success shadow-[0_0_0_2px_rgba(16,185,129,0.18)]";
  return (
    <span className="inline-flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-full border border-border text-text-2">
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      {children}
    </span>
  );
}
