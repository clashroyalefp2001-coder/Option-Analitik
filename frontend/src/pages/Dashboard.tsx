import { useEffect, useState, useMemo, useRef } from "react";
import { AreaChart, Area, Tooltip, ResponsiveContainer, YAxis } from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Wallet,
  Zap,
  Activity,
  Cpu,
  RefreshCw,
  Play,
  Gauge,
  Award,
  CheckCircle2,
} from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { KpiCard } from "../components/KpiCard";
import { Card, CardHead } from "../components/Card";
import { Progress } from "../components/Progress";
import { api, type MetricsResponse } from "../lib/api";

function pct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits)}%`;
}
function num(v: number, digits = 2) {
  return Number.isFinite(v) ? v.toFixed(digits) : "—";
}

export function Dashboard() {
  const [m, setM] = useState<MetricsResponse | null>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshSuccess, setRefreshSuccess] = useState(false);
  const [runPipelineLoading, setRunPipelineLoading] = useState(false);
  const [runPipelineSuccess, setRunPipelineSuccess] = useState(false);
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const isLoadingRef = useRef(runPipelineLoading);
  isLoadingRef.current = runPipelineLoading;

  async function load() {
    setLoading(true);
    setRefreshSuccess(false);
    try {
      // Запрашиваем метрики и трейды для постройки живого графика
      const [r, tRes] = await Promise.all([
        api.metrics(),
        api.trades().catch(() => ({ trades: [] })) // не падаем, если трейдов нет
      ]);
      setM(r);
      setTrades(tRes.trades || []);
      setRefreshSuccess(true);
      setTimeout(() => setRefreshSuccess(false), 2000);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    
    const checkPipeline = async () => {
        const status = await api.getPipelineStatus();
        
        if (status && status.running) {
            if (!isLoadingRef.current) setRunPipelineLoading(true);
        } else if (status && !status.running && isLoadingRef.current) {
            setRunPipelineLoading(false);
            setRunPipelineSuccess(true);
            setTimeout(() => setRunPipelineSuccess(false), 3000);
            load();
        }
    };
    checkPipeline();
    const pId = setInterval(checkPipeline, 1000);
    
    return () => {
      clearInterval(id);
      clearInterval(pId);
    };
  }, []);

  async function runPipeline() {
    setRunPipelineLoading(true);
    setRunPipelineSuccess(false);
    try {
      await api.runBacktest(true);
    } catch (e) {
      console.error(e);
      setRunPipelineLoading(false);
    }
  }

  // Расчёт Cumulative PnL (Кривая капитала)
  const chartData = useMemo(() => {
    if (!trades || trades.length === 0) return [];
    let sum = 1000000; // Базовый бюджет, совпадает с бэктестом по дефолту
    const res = [{ index: 0, equity: sum, label: "Старт" }];
    
    // Сортируем трейды по времени исполнения
    const sorted = [...trades].sort((a,b) => (a.date || a.timestamp || "").localeCompare(b.date || b.timestamp || ""));
    
    sorted.forEach((t, i) => {
      sum += (t.pnl || 0);
      res.push({
        index: i + 1,
        equity: sum,
        label: t.date || t.timestamp || `Trade ${i+1}`
      });
    });
    return res;
  }, [trades]);

  // Последние 5 сделок для виджета
  const recentTrades = useMemo(() => {
    if (!trades || trades.length === 0) return [];
    return [...trades].sort((a,b) => (b.date || b.timestamp || "").localeCompare(a.date || a.timestamp || "")).slice(0, 5);
  }, [trades]);

  return (
    <>
      <Topbar
        title="Обзор"
        status={
          <StatusPill tone="ok">
            Модель: {m?.model?.backend ?? "—"} · F1={num(m?.model?.f1_score ?? 0)}
          </StatusPill>
        }
      >
        <button 
          className={`btn ${refreshSuccess ? '!text-success !border-success bg-success/10' : 'btn-ghost'}`} 
          onClick={load} 
          disabled={loading}
        >
          {refreshSuccess ? <CheckCircle2 size={16} /> : <RefreshCw size={16} className={loading ? "animate-spin" : ""} />}
          {refreshSuccess ? "Обновлено" : "Обновить"} <span className="kbd">⌘R</span>
        </button>
        <div className="flex gap-2">
          <button 
            className={`btn ${runPipelineSuccess ? '!bg-success !text-white !border-success' : 'btn-primary'}`} 
            onClick={runPipeline}
            disabled={runPipelineLoading}
          >
            {runPipelineSuccess ? <CheckCircle2 size={16} /> : runPipelineLoading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
            {runPipelineSuccess ? "Завершено" : runPipelineLoading ? "В процессе..." : "Запустить пайплайн"}
          </button>
        </div>
      </Topbar>

      <main className="p-8">
        <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
          <div>
            <div className="text-[22px] font-semibold tracking-tight">Состояние стратегии</div>
            <div className="text-sm text-text-2 mt-1">
              {m?.timestamp ? `Последний прогон · ${m.timestamp}` : "Прогонов пока не было"}
              {m?.model?.trading_samples ? ` · ${m.model.trading_samples} строк фич` : ""}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          <KpiCard
            label="Sharpe"
            icon={<TrendingUp size={14} />}
            value={num(m?.kpi?.sharpe_ratio ?? 0)}
            delta="—"
            deltaTone="neutral"
          />
          <KpiCard
            label="Max DD"
            icon={<TrendingDown size={14} />}
            value={pct(m?.kpi?.max_drawdown ?? 0)}
          />
          <KpiCard
            label="Hit-rate"
            icon={<Target size={14} />}
            value={pct(m?.kpi?.hit_rate ?? 0)}
          />
          <KpiCard
            label="Total return"
            icon={<Wallet size={14} />}
            value={pct(m?.kpi?.total_return ?? 0)}
            delta={(m?.kpi?.total_return ?? 0) >= 0 ? "↑ за период" : "↓ за период"}
            deltaTone={(m?.kpi?.total_return ?? 0) >= 0 ? "up" : "down"}
          />
          <KpiCard
            label="CAGR"
            icon={<Gauge size={14} />}
            value={pct(m?.kpi?.cagr ?? 0)}
          />
          <KpiCard
            label="Calmar"
            icon={<Award size={14} />}
            value={num(m?.kpi?.calmar ?? 0)}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="lg:col-span-2">
            <Card className="flex flex-col h-[350px]">
              <CardHead title="Кривая капитала" icon={<Activity size={16} />} />
              <div className="flex-1 mt-4 relative w-full h-full pb-4">
                {chartData.length > 1 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="colorEq" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <YAxis domain={['dataMin', 'dataMax']} hide={true} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155", borderRadius: "8px", fontSize: "12px", color: "#f8fafc" }}
                        itemStyle={{ color: "#3B82F6", fontWeight: "bold" }}
                        labelStyle={{ display: "none" }}
                        formatter={(val: any) => [`₽ ${Number(val).toLocaleString('ru-RU', {minimumFractionDigits: 0, maximumFractionDigits: 0})}`, "Баланс"]}
                      />
                      <Area type="monotone" dataKey="equity" stroke="#3B82F6" strokeWidth={2} fillOpacity={1} fill="url(#colorEq)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <EquityChartPlaceholder />
                )}
              </div>
            </Card>
          </div>
          <Card className="h-full">
            <CardHead title="Качество модели" icon={<Award size={16} />} />
            <div className="grid grid-cols-2 gap-y-6 gap-x-4 mt-6">
              <ModelMetric label="F1-score · направление" value={m?.model?.f1_score ?? 0} />
              <ModelMetric label="Precision" value={m?.model?.precision ?? 0} />
              <ModelMetric label="Recall" value={m?.model?.recall ?? 0} />
              <ModelMetric label="ROC-AUC" value={m?.model?.roc_auc ?? 0} />
            </div>
            <div className="border-t border-border pt-6 mt-6">
              <div className="text-[10px] uppercase font-bold text-text-3 tracking-wider mb-1.5 flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-brand-1"></span>
                Backend · {m?.model?.backend ?? "—"}
              </div>
              <div className="text-xl font-bold num text-text-1">
                {m?.model?.trading_samples ?? 0} / {m?.model?.train_samples ?? 0} / {m?.model?.val_samples ?? 0}
              </div>
            </div>
          </Card>
        </div>

        <Card className="!p-0 overflow-hidden">
          <div className="px-6 pt-6 mb-4"><CardHead title="Последние сделки" icon={<Zap size={16} />} /></div>
          {recentTrades.length > 0 ? (
            <div className="overflow-x-auto pb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-text-3 border-b border-border">
                    {["Дата", "Инструмент", "Тип", "Страйк", "Сторона", "PnL"].map(h => <th key={h} className="px-6 py-2 font-medium">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((t, i) => (
                    <tr key={i} className="border-b border-border-soft hover:bg-bg-2">
                      <td className="px-6 py-2.5 num text-text-2">{t.date ?? t.timestamp ?? "—"}</td>
                      <td className="px-6 py-2.5 font-medium">{t.underlying_symbol ?? t.symbol ?? "—"}</td>
                      <td className="px-6 py-2.5">
                        <span className={`badge ${t.type === "call" ? "badge-call" : "badge-put"}`}>{t.type ?? "—"}</span>
                      </td>
                      <td className="px-6 py-2.5 num">{t.strike ?? "—"}</td>
                      <td className="px-6 py-2.5">
                        <span className={`badge ${t.side === "buy" ? "badge-buy" : t.side === "sell" ? "badge-sell" : "badge-neu"}`}>{t.side ?? "—"}</span>
                      </td>
                      <td className={`px-6 py-2.5 num font-medium ${(t.pnl ?? 0) >= 0 ? "text-success" : "text-danger"}`}>
                        {(t.pnl ?? 0) > 0 ? "+" : ""}{num(t.pnl ?? 0, 2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <SignalsPlaceholder />
          )}
        </Card>
      </main>
    </>
  );
}

function ModelMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase font-bold text-text-3 tracking-wider mb-1.5 truncate">
        {label}
      </div>
      <div className="text-2xl font-bold num text-text-1 leading-none">
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function EquityChartPlaceholder() {
  return (
    <div className="flex items-center justify-center w-full h-full text-sm text-text-3 bg-bg-2/30 rounded-md">
      Сделок пока нет. Запустите пайплайн.
    </div>
  );
}

function SignalsPlaceholder() {
  return (
    <div className="text-sm text-text-3 py-12 text-center">
      Сделки появятся после успешного прогона пайплайна.
    </div>
  );
}
