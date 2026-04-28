import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Database,
  SlidersHorizontal,
  GraduationCap,
  Play,
  Terminal,
  LineChart,
} from "lucide-react";

const ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Обзор", kbd: "1" },
  { to: "/data", icon: Database, label: "Данные", kbd: "2" },
  { to: "/strategy", icon: SlidersHorizontal, label: "Стратегия", kbd: "3" },
  { to: "/training", icon: GraduationCap, label: "Обучение", kbd: "4" },
  { to: "/backtest", icon: Play, label: "Бэктест", kbd: "5" },
  { to: "/logs", icon: Terminal, label: "Логи", kbd: "6" },
];

export function Sidebar() {
  return (
    <aside className="bg-bg-1 border-r border-border flex flex-col px-3 py-6 sticky top-0 h-screen w-[232px] shrink-0">
      <div className="flex items-center gap-3 px-3 mb-8">
        <div className="w-8 h-8 rounded-md grid place-items-center text-white"
             style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}>
          <LineChart size={18} />
        </div>
        <div>
          <div className="font-semibold text-[15px] tracking-tight">Option-Analitik</div>
          <div className="text-[11px] text-text-3">Si 06.2026</div>
        </div>
      </div>

      <div className="text-[11px] uppercase tracking-wider text-text-3 px-3 pb-2">Навигация</div>
      <nav className="flex flex-col gap-0.5">
        {ITEMS.map(({ to, icon: Icon, label, kbd }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 px-3 py-2.5 rounded-sm text-[13.5px] font-medium transition-colors select-none",
                isActive
                  ? "bg-brand/10 text-brand-2"
                  : "text-text-2 hover:bg-bg-2 hover:text-text-1",
              ].join(" ")
            }
          >
            <Icon size={18} />
            <span>{label}</span>
            <span className="ml-auto font-mono text-[11px] text-text-3 bg-white/[0.04] border border-border rounded px-1.5 py-px">
              {kbd}
            </span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-3 border-t border-border-soft flex items-center gap-3 px-3">
        <div className="w-7 h-7 rounded-full bg-bg-2 grid place-items-center text-xs font-semibold">CR</div>
        <div className="text-xs">
          <div className="text-text-1 font-medium">trader</div>
          <div className="text-text-3">Moscow · MSK</div>
        </div>
      </div>
    </aside>
  );
}
