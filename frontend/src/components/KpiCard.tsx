import { ReactNode } from "react";
import { Card } from "./Card";

export function KpiCard({
  label,
  value,
  icon,
  delta,
  deltaTone,
}: {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  delta?: string;
  deltaTone?: string;
}) {
  return (
    <Card className="p-6 flex flex-col justify-between min-h-[140px]">
      <div className="flex justify-end items-start mb-4">
        {delta ? (
          <div className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider flex items-center gap-1 ${
            deltaTone === "up" || deltaTone === "success" ? "bg-emerald-50 text-emerald-600 border border-emerald-100" :
            deltaTone === "down" || deltaTone === "danger" ? "bg-rose-50 text-rose-600 border border-rose-100" :
            "bg-gray-100/60 text-gray-500 border border-gray-200"
          }`}>
            {delta}
          </div>
        ) : (
          <div className="p-2 rounded-lg bg-gray-50 text-gray-500 flex items-center justify-center border border-gray-100">
            {icon}
          </div>
        )}
      </div>
      <div>
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">{label}</div>
        <div className="text-2xl font-bold tracking-tight text-gray-900 num leading-none">{value}</div>
      </div>
    </Card>
  );
}
