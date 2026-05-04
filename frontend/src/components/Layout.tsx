import React from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Database, Search, GraduationCap, Terminal } from "lucide-react";

export function Sidebar() {
  const location = useLocation();

  const links = [
    { to: "/", icon: LayoutDashboard, label: "Панель управления" },
    { to: "/data", icon: Database, label: "Данные" },
    { to: "/trades", icon: Search, label: "Поиск сделок" },
    { to: "/training", icon: GraduationCap, label: "Обучение" },
    { to: "/logs", icon: Terminal, label: "Логи" },
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 text-2xl font-bold tracking-tight">Option Analitik</div>
      <nav className="flex-1 px-4 space-y-2">
        {links.map((link) => {
          const active = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                active ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <link.icon className="w-5 h-5" />
              <span>{link.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900 font-sans">
      <Sidebar />
      <main className="flex-1 overflow-auto h-screen relative">
        {children}
      </main>
    </div>
  );
}
