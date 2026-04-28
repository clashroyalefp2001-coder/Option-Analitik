import { useEffect, useState } from "react";
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
  ArrowUp,
  ArrowDown,
  Gauge,
  Award,
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
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await api.metrics();
      setM(r);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 5000); // лёгкий live-refresh
    return () => clearInterval(id);
  }, []);

  async function runPipeline() {
    try {
      await api.runBacktest(false);
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <>
      <Topbar
        title="Обзор"
        status={
          <StatusPill tone="ok">
            Модель: {m?.model.backend ?? "—"} · F1={num(m?.model.f1_score ?? 0)}
          </StatusPill>
        }
      >
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Обновить <span className="kbd">⌘R</span>
        </button>
        <button className="btn btn-primary" onClick={runPipeline}>
          <Play size={16} /> Запустить пайплайн
        </button>
      </Topbar>

      <main className="p-8">
        <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
          <div>
            <div className="text-[22px] font-semibold tracking-tight">Состояние стратегии</div>
            <div className="text-sm text-text-2 mt-1">
              {m?.timestamp ? `Последний прогон · ${m.timestamp}` : "Прогонов пока не было"}
              {m?.model.trading_samples ? ` · ${m.model.trading_samples} строк фич` : ""}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          <KpiCard
            label="Sharpe"
            icon={<TrendingUp size={14} />}
            value={num(m?.kpi.sharpe_ratio ?? 0)}
            delta={(m?.kpi.sharpe_ratio ?? 0) > 0 ? "положительный" : "—"}
            deltaTone={(m?.kpi.sharpe_ratio ?? 0) > 0 ? "up" : "neutral"}
          />
          <KpiCard
            label="Max DD"
            icon={<TrendingDown size={14} />}
            value={pct(m?.kpi.max_drawdown ?? 0)}
            deltaTone={(m?.kpi.max_drawdown ?? 0) > -0.1 ? "up" : "down"}
          />
          <KpiCard
            label="Hit-rate"
            icon={<Target size={14} />}
            value={pct(m?.kpi.hit_rate ?? 0)}
          />
          <KpiCard
            label="Total return"
            icon={<Wallet size={14} />}
            value={pct(m?.kpi.total_return ?? 0)}
            delta={(m?.kpi.total_return ?? 0) >= 0 ? "↑ за период" : "↓ за период"}
            deltaTone={(m?.kpi.total_return ?? 0) >= 0 ? "up" : "down"}
          />
          <KpiCard
            label="CAGR"
            icon={<Gauge size={14} />}
            value={pct(m?.kpi.cagr ?? 0)}
          />
          <KpiCard
            label="Calmar"
            icon={<Award size={14} />}
            value={num(m?.kpi.calmar ?? 0)}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="lg:col-span-2">
            <Card>
              <CardHead title="Кривая капитала" icon={<Activity size={16} />} />
              <EquityChartPlaceholder />
            </Card>
          </div>
          <Card>
            <CardHead title="Качество модели" icon={<Cpu size={16} />} />
            <div className="flex flex-col gap-4">
              <ModelMetricRow label="F1-score · направление" value={m?.model.f1_score ?? 0} tone="brand" />
              <ModelMetricRow label="Precision" value={m?.model.precision ?? 0} tone="success" />
              <ModelMetricRow label="Recall" value={m?.model.recall ?? 0} tone="warning" />
              <ModelMetricRow label="ROC-AUC" value={m?.model.roc_auc ?? 0} tone="brand" />
              <div className="border-t border-border-soft pt-4 text-xs text-text-2 flex justify-between">
                <span>Backend · {m?.model.backend ?? "—"}</span>
                <span className="num">
                  {m?.model.trading_samples ?? 0} / {m?.model.train_samples ?? 0} / {m?.model.val_samples ?? 0}
                </span>
              </div>
            </div>
          </Card>
        </div>

        <Card>
          <CardHead title="Последние сигналы" icon={<Zap size={16} />} />
          <SignalsPlaceholder />
        </Card>
      </main>
    </>
  );
}

function ModelMetricRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "brand" | "success" | "warning" | "danger";
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-text-2 mb-1.5">
        <span>{label}</span>
        <span className="num text-text-1">{value.toFixed(2)}</span>
      </div>
      <Progress value={value} tone={tone ?? "brand"} />
    </div>
  );
}

function EquityChartPlaceholder() {
  return (
    <div
      className="h-[280px] rounded-md relative overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg, rgba(59,130,246,0.18) 0%, rgba(59,130,246,0) 100%), " +
          "repeating-linear-gradient(0deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 56px), " +
          "repeating-linear-gradient(90deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 80px)",
      }}
    >
      <svg viewBox="0 0 800 280" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
        <path
          d="M0,210 C60,180 120,150 180,160 C240,170 300,140 360,120 C420,100 480,90 540,75 C600,60 660,80 720,55 C780,30 800,40 800,40"
          fill="none"
          stroke="#3B82F6"
          strokeWidth="2"
        />
      </svg>
    </div>
  );
}

function SignalsPlaceholder() {
  return (
    <div className="text-sm text-text-2 py-12 text-center">
      Сигналы появятся после запуска пайплайна.
    </div>
  );
}
