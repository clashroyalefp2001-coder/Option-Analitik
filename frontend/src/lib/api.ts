// frontend/src/lib/api.ts
const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  health: () => get<{ status: string; pipeline_root: string }>("/health"),
  metrics: () => get<MetricsResponse>("/metrics"),
  // ОБНОВЛЕНО: Поддержка инструмента
  options: (limit = 200, instrument?: string) => 
    get<{ rows: any[]; count: number }>(`/options?limit=${limit}${instrument ? `&instrument=${encodeURIComponent(instrument)}` : ''}`),
  dataProfile: (instrument?: string) => 
    get<DataProfile>(`/data/profile${instrument ? `?instrument=${encodeURIComponent(instrument)}` : ''}`),
  instruments: () => 
    get<{ instruments: string[] }>("/data/instruments"),
  // ... (остальные функции оставьте без изменений)
  strategyConfig: () => get<{ config: Record<string, any> }>("/strategy/config"),
  saveStrategyConfig: (cfg: Record<string, any>) =>
    put<{ ok: boolean }>("/strategy/config", { config: cfg }),
  trainingHistory: () => get<{ runs: TrainingRun[] }>("/training/history"),
  runTraining: () => post<{ started: boolean }>("/training/run"),
  runBacktest: (noTrain = false) =>
    post<{ started: boolean; no_train: boolean }>(`/backtest/run?no_train=${noTrain}`),
  equity: () => get<{ points: any[] }>("/backtest/equity"),
  trades: () => get<{ trades: any[] }>("/backtest/trades"),
  state: () => get<RunState>("/backtest/state"),
  logsTail: (n = 200) => get<{ lines: string[]; step: string | null; running: boolean }>(`/logs/tail?n=${n}`),
};

export interface MetricsResponse {
  kpi: {
    sharpe_ratio: number;
    max_drawdown: number;
    total_return: number;
    hit_rate: number;
    cagr: number;
    calmar: number;
  };
  model: {
    backend: string;
    f1_score: number;
    precision: number;
    recall: number;
    roc_auc: number;
    training_loss: number;
    validation_loss: number;
    trading_samples: number;
    train_samples: number;
    val_samples: number;
    training_time: number;
    features: string[];
    feature_importance: Record<string, number>;
  };
  timestamp: string | null;
}

export interface DataProfile {
  total: number;
  calls: number;
  puts: number;
  strike_min: number;
  strike_max: number;
  days_min: number;
  days_max: number;
  file: string;
  error?: string;
}

export interface TrainingRun {
  id: string;
  label: string;
  backend: string;
  trained_at: string | null;
  f1_score: number;
  precision: number;
  recall: number;
  roc_auc: number;
  training_loss: number;
  validation_loss: number;
  samples: number;
  is_active: boolean;
}

export interface RunState {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  step: string | null;
  log_tail: string[];
}