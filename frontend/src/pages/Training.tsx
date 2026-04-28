import { useEffect, useState } from "react";
import { GraduationCap, BarChart3, History, Play } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { Progress } from "../components/Progress";
import { api, type TrainingRun, type MetricsResponse } from "../lib/api";

function pct(v: number, d = 1) { return `${(v * 100).toFixed(d)}%`; }
function num(v: number, d = 2) { return Number.isFinite(v) ? v.toFixed(d) : "—"; }

export function Training() {
  const [history, setHistory] = useState<TrainingRun[]>([]);
  const [m, setM] = useState<MetricsResponse | null>(null);
  const [running, setRunning] = useState(false);

  async function load() {
    const [h, mm] = await Promise.all([api.trainingHistory(), api.metrics()]);
    setHistory(h.runs);
    setM(mm);
  }
  useEffect(() => { load(); const id = setInterval(load, 3000); return () => clearInterval(id); }, []);

  async function retrain() {
    setRunning(true);
    try {
      await api.runTraining();
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  }

  // Сортируем feature importance в порядке убывания
  const importance = Object.entries(m?.model.feature_importance ?? {})
    .sort((a, b) => b[1] - a[1]);

  return (
    <>
      <Topbar
        title="Обучение"
        status={
          <StatusPill tone={m?.model.backend === "lightgbm" ? "ok" : "warn"}>
            Активная модель: {m?.model.backend ?? "—"} · F1={num(m?.model.f1_score ?? 0)}
          </StatusPill>
        }
      >
        <button className="btn btn-primary" onClick={retrain} disabled={running}>
          <Play size={16} /> Переобучить
        </button>
      </Topbar>

      <main className="p-8">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6 items-start">
          <Card>
            <CardHead title="Текущие метрики" icon={<GraduationCap size={16}/>} />
            <div className="grid grid-cols-2 gap-4">
              <Stat label="F1-score" value={num(m?.model.f1_score ?? 0)} progress={m?.model.f1_score ?? 0} />
              <Stat label="Precision" value={num(m?.model.precision ?? 0)} progress={m?.model.precision ?? 0} tone="success" />
              <Stat label="Recall" value={num(m?.model.recall ?? 0)} progress={m?.model.recall ?? 0} tone="warning" />
              <Stat label="ROC-AUC" value={num(m?.model.roc_auc ?? 0)} progress={m?.model.roc_auc ?? 0} />
              <Stat label="Train loss" value={num(m?.model.training_loss ?? 0, 4)} />
              <Stat label="Val loss" value={num(m?.model.validation_loss ?? 0, 4)} />
            </div>
            <div className="border-t border-border-soft mt-4 pt-4 text-xs text-text-2 flex justify-between">
              <span>Backend · {m?.model.backend ?? "—"}</span>
              <span className="num">
                samples {m?.model.trading_samples ?? 0} (train {m?.model.train_samples ?? 0} / val {m?.model.val_samples ?? 0})
              </span>
            </div>
          </Card>

          <Card>
            <CardHead title="Важность фич" icon={<BarChart3 size={16}/>} />
            {importance.length === 0 && (
              <div className="text-sm text-text-2 py-12 text-center">
                Запустите обучение, чтобы увидеть важность фич.
              </div>
            )}
            <div className="flex flex-col gap-3">
              {importance.map(([name, v]) => (
                <div key={name}>
                  <div className="flex justify-between text-xs text-text-2 mb-1">
                    <span>{name}</span><span className="num text-text-1">{v.toFixed(3)}</span>
                  </div>
                  <Progress value={v} tone="brand" />
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card className="!p-0 overflow-hidden">
          <div className="px-6 pt-6"><CardHead title="История обучений" icon={<History size={16}/>} /></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-text-3 border-b border-border">
                  {["Время","Backend","Samples","F1","Precision","Recall","ROC-AUC","Train loss","Val loss","Статус"].map(h =>
                    <th key={h} className="px-4 py-3 font-medium">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {history.length === 0 && (
                  <tr><td colSpan={10} className="px-4 py-12 text-center text-text-2">
                    Истории нет. Нажмите «Переобучить», чтобы записать первую модель.
                  </td></tr>
                )}
                {history.map(r => (
                  <tr key={r.id} className="border-b border-border-soft hover:bg-bg-2">
                    <td className="px-4 py-2.5 num">{r.trained_at ?? "—"}</td>
                    <td className="px-4 py-2.5">{r.backend}</td>
                    <td className="px-4 py-2.5 num">{r.samples}</td>
                    <td className="px-4 py-2.5 num">{num(r.f1_score)}</td>
                    <td className="px-4 py-2.5 num">{num(r.precision)}</td>
                    <td className="px-4 py-2.5 num">{num(r.recall)}</td>
                    <td className="px-4 py-2.5 num">{num(r.roc_auc)}</td>
                    <td className="px-4 py-2.5 num">{num(r.training_loss, 4)}</td>
                    <td className="px-4 py-2.5 num">{num(r.validation_loss, 4)}</td>
                    <td className="px-4 py-2.5">
                      {r.is_active
                        ? <span className="badge badge-call">активна</span>
                        : <span className="badge badge-neu">архив</span>}
                    </td>
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

function Stat({
  label, value, progress, tone,
}: {
  label: string; value: string; progress?: number; tone?: "brand" | "success" | "warning" | "danger";
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-text-2 mb-1.5">
        <span>{label}</span><span className="num text-text-1">{value}</span>
      </div>
      {progress !== undefined && <Progress value={progress} tone={tone ?? "brand"} />}
    </div>
  );
}
