import { ReactNode } from "react";

export function KpiCard({
  label,
  value,
  delta,
  deltaTone,
  icon,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaTone?: "up" | "down" | "neutral";
  icon?: ReactNode;
}) {
  const deltaCls =
    deltaTone === "up" ? "text-success" :
    deltaTone === "down" ? "text-danger" :
    "text-text-2";
  return (
    <div className="card !p-5">
      <div className="text-xs text-text-2 flex items-center gap-2">
        {icon}
        <span>{label}</span>
      </div>
      <div className="num text-[26px] font-semibold mt-3 tracking-tight">{value}</div>
      {delta !== undefined && <div className={`text-xs mt-2 ${deltaCls}`}>{delta}</div>}
    </div>
  );
}
