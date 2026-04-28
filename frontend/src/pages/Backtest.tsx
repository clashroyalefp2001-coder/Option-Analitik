import { useEffect, useState } from "react";
import { Play, Square, LineChart, Receipt, Check } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { Progress } from "../components/Progress";
import { api, type RunState } from "../lib/api";

const STEPS = [
  { id: "data",       label: "Данные" },
  { id: "features",   label: "Фичи" },
  { id: "training",   label: "Обучение" },
  { id: "inference",  label: "Инференс" },
  { id: "filters",    label: "Фильтры" },
  { id: "sizing",     label: "Sizing" },
  { id: "backtest",   label: "Бэктест" },
];

export function Backtest() {
  const [state, setState] = useState<RunState | null>(null);
  const [trades, setTrades] = useState<any[]>([]);

  async function load() {
    const [s, t] = await Promise.all([api.state(), api.trades()]);
    setState(s);
    setTrades(t.trades);
  }
  useEffect(() => { load(); const id = setInterval(load, 2000); return () => clearInterval(id); }, []);

  const stepIdx = STEPS.findIndex(s => s.id === state?.step);
  const progress = state?.running
    ? Math.max(0, stepIdx + 1) / STEPS.length
    : (state?.exit_code === 0 ? 1 : 0);

  async function run(noTrain: boolean) {
    try { await api.runBacktest(noTrain); } catch (e) { console.error(e); }
  }

  return (
    <>
      <Topbar
        title="Бэктест"
        status={
          state?.running
            ? <StatusPill tone="warn">Запущен · {state.step ?? ""}</StatusPill>
            : state?.exit_code === 0
              ? <StatusPill tone="ok">Завершён успешно</StatusPill>
              : <StatusPill tone="ok">Готов к запуску</StatusPill>
        }
      >
        <button className="btn btn-ghost" disabled={state?.running} onClick={() => run(true)}>
          <Square size={16} /> Без обучения
        </button>
        <button className="btn btn-primary" disabled={state?.running} onClick={() => run(false)}>
          <Play size={16} /> Запустить <span className="kbd">⌘⏎</span>
        </button>
      </Topbar>

      <main className="p-8">
        <Card className="mb-6">
          <CardHead
            title="Прогресс"
            icon={<LineChart size={16}/>}
            right={
              <span className="num text-xs text-text-2">
                шаг {Math.max(0, stepIdx + 1)} из {STEPS.length}
              </span>
            }
          />
          <Progress value={progress} tone={state?.exit_code === 0 ? "success" : "brand"} className="!h-2" />
          <div className="grid grid-cols-7 gap-2 mt-4 text-[11px] text-text-2">
            {STEPS.map((s, i) => (
              <div key={s.id} className="flex items-center gap-1.5">
                <Check
                  size={14}
                  className={i <= stepIdx ? "text-success" : "text-text-3"}
                />
                {s.label}
              </div>
            ))}
          </div>
        </Card>

        <Card className="!p-0 overflow-hidden">
          <div className="px-6 pt-6"><CardHead title="Сделки" icon={<Receipt size={16}/>} /></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-text-3 border-b border-border">
                  {["Дата","Тип","Страйк","Сторона","Размер","Цена входа","Цена выхода","PnL"].map(h =>
                    <th key={h} className="px-4 py-3 font-medium">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {trades.length === 0 && (
                  <tr><td colSpan={8} className="px-4 py-12 text-center text-text-2">
                    Сделок пока нет. Запустите бэктест.
                  </td></tr>
                )}
                {trades.map((t, i) => (
                  <tr key={i} className="border-b border-border-soft hover:bg-bg-2">
                    <td className="px-4 py-2.5 num">{t.date ?? t.timestamp ?? "—"}</td>
                    <td className="px-4 py-2.5"><span className={`badge ${t.type === "call" ? "badge-call" : "badge-put"}`}>{t.type ?? "—"}</span></td>
                    <td className="px-4 py-2.5 num">{t.strike ?? "—"}</td>
                    <td className="px-4 py-2.5"><span className={`badge ${t.side === "buy" ? "badge-buy" : t.side === "sell" ? "badge-sell" : "badge-neu"}`}>{t.side ?? "—"}</span></td>
                    <td className="px-4 py-2.5 num">{t.size ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{t.entry_price ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{t.exit_price ?? "—"}</td>
                    <td className={`px-4 py-2.5 num ${(t.pnl ?? 0) >= 0 ? "text-success" : "text-danger"}`}>{t.pnl ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </>
  );
}
