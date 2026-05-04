export interface MetricsResponse {
  winRate: number;
  totalPnL: number;
  sharpeRatio: number;
  maxDrawdown: number;
  expectedValue: number;
  tradeCount: number;
  uptime: number;
  status: "Active" | "Backtest" | "Offline";
  recentEvents: string[];
  timestamp?: string;
  kpi: {
    sharpe_ratio: number;
    max_drawdown: number;
    hit_rate: number;
    total_return: number;
    cagr: number;
    calmar: number;
  };
  model: {
    backend: string;
    f1_score: number;
    precision: number;
    recall: number;
    roc_auc: number;
    trading_samples: number;
    train_samples: number;
    val_samples: number;
  };
}

export interface Trade {
  id: string;
  date: string;
  instrument: string;
  type: string;
  pnl: number;
  underlying_symbol?: string;
  symbol?: string;
  strike?: string | number;
  side?: string;
}

export interface DataProfile {
  file: string;
  total: number;
  calls?: number;
  puts?: number;
  strike_min?: number;
  strike_max?: number;
  days_min?: number;
  days_max?: number;
  error?: string;
}

const API_URL = "/internal_fastapi";

export const api = {
  async metrics(): Promise<MetricsResponse> {
    try {
      const resp = await fetch(`${API_URL}/metrics/`);
      if (!resp.ok) throw new Error(`Backend metrics error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend metrics not available", e);
      return {
        winRate: 0,
        totalPnL: 0,
        sharpeRatio: 0,
        maxDrawdown: 0,
        expectedValue: 0,
        tradeCount: 0,
        uptime: 0,
        status: "Offline",
        recentEvents: [],
        kpi: { sharpe_ratio: 0, max_drawdown: 0, hit_rate: 0, total_return: 0, cagr: 0, calmar: 0 },
        model: { backend: "—", f1_score: 0, precision: 0, recall: 0, roc_auc: 0, trading_samples: 0, train_samples: 0, val_samples: 0 }
      };
    }
  },
  async trades(): Promise<{ trades: Trade[] }> {
    try {
      const resp = await fetch(`${API_URL}/data/trades`);
      if (!resp.ok) throw new Error(`Backend trades error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend trades not available", e);
      return { trades: [] };
    }
  },
  async runBacktest(useLive: boolean): Promise<void> {
    try {
      const resp = await fetch(`${API_URL}/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useLive }),
      });
      if (!resp.ok) throw new Error(`Backend runBacktest error: ${resp.status}`);
    } catch (e) {
      console.error("Backend runBacktest failed", e);
      throw e;
    }
  },
  async getPipelineStatus(): Promise<any> {
    try {
      const resp = await fetch(`${API_URL}/pipeline/status?_t=${Date.now()}`, {
        cache: "no-store"
      });
      if (!resp.ok) throw new Error(`Backend status error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      return null;
    }
  },
  async dataProfile(instrument?: string): Promise<DataProfile> {
    try {
      const query = instrument ? `?instrument=${instrument}` : '';
      const resp = await fetch(`${API_URL}/data/profile${query}`);
      if (!resp.ok) throw new Error(`Backend dataProfile error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend dataProfile not available", e);
      return { file: "—", total: 0 };
    }
  },
  async options(limit: number, instrument?: string): Promise<{ rows: any[] }> {
    try {
      const query = instrument ? `?instrument=${instrument}&limit=${limit}` : `?limit=${limit}`;
      const resp = await fetch(`${API_URL}/data/options${query}`);
      if (!resp.ok) throw new Error(`Backend options error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend options not available", e);
      return { rows: [] };
    }
  },
  async instruments(): Promise<{ instruments: string[] }> {
    try {
      const resp = await fetch(`${API_URL}/data/instruments`);
      if (!resp.ok) throw new Error(`Backend instruments error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend instruments not available", e);
      return { instruments: [] };
    }
  },
  async getTrainingHistory(): Promise<any[]> {
    try {
      const resp = await fetch(`${API_URL}/pipeline/history`);
      if (!resp.ok) throw new Error(`Backend history error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend training history not available", e);
      return [];
    }
  },
  async getTrainingConfig(): Promise<any> {
    try {
      const resp = await fetch(`${API_URL}/pipeline/config`);
      if (!resp.ok) throw new Error(`Backend config error: ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn("Backend training config not available", e);
      return {};
    }
  },
  async updateTrainingConfig(payload: any): Promise<void> {
    try {
      const resp = await fetch(`${API_URL}/pipeline/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`Backend update config error: ${resp.status}`);
    } catch (e) {
      console.error("Backend update config failed", e);
      throw e;
    }
  }
};
