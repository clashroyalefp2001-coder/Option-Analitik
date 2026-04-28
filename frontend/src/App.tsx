import { Routes, Route, useNavigate } from "react-router-dom";

import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./pages/Dashboard";
import { Data } from "./pages/Data";
import { Strategy } from "./pages/Strategy";
import { Training } from "./pages/Training";
import { Backtest } from "./pages/Backtest";
import { Logs } from "./pages/Logs";
import { useHotkeys } from "./hooks/useHotkeys";
import { api } from "./lib/api";

const NAV: Record<string, string> = {
  "1": "/",
  "2": "/data",
  "3": "/strategy",
  "4": "/training",
  "5": "/backtest",
  "6": "/logs",
};

export default function App() {
  const navigate = useNavigate();

  useHotkeys({
    "1": () => navigate(NAV["1"]),
    "2": () => navigate(NAV["2"]),
    "3": () => navigate(NAV["3"]),
    "4": () => navigate(NAV["4"]),
    "5": () => navigate(NAV["5"]),
    "6": () => navigate(NAV["6"]),
    "mod+r": (ev) => {
      ev.preventDefault();
      // Запускаем пайплайн отовсюду (если уже не запущен)
      api.runBacktest(false).catch(() => {});
    },
  });

  return (
    <div className="grid grid-cols-[232px_1fr] min-h-screen">
      <Sidebar />
      <div className="min-w-0 flex flex-col">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/data" element={<Data />} />
          <Route path="/strategy" element={<Strategy />} />
          <Route path="/training" element={<Training />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/logs" element={<Logs />} />
        </Routes>
      </div>
    </div>
  );
}
