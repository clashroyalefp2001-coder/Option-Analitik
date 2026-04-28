import { useEffect, useState } from "react";
import { Settings2, Filter, Shield, BrainCircuit, Save, Undo2 } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { api } from "../lib/api";
import { useHotkeys } from "../hooks/useHotkeys";

type Cfg = Record<string, any>;

export function Strategy() {
  const [original, setOriginal] = useState<Cfg>({});
  const [draft, setDraft] = useState<Cfg>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.strategyConfig().then(({ config }) => {
      setOriginal(config);
      setDraft(JSON.parse(JSON.stringify(config)));
    });
  }, []);

  const dirty = JSON.stringify(original) !== JSON.stringify(draft);

  async function save() {
    setSaving(true);
    try {
      await api.saveStrategyConfig(draft);
      setOriginal(JSON.parse(JSON.stringify(draft)));
    } finally {
      setSaving(false);
    }
  }
  function reset() {
    setDraft(JSON.parse(JSON.stringify(original)));
  }

  useHotkeys({
    "mod+s": () => { if (dirty) save(); },
  });

  const risk = (draft.RISK_CONFIG ?? {}) as Cfg;

  function setRisk(key: string, value: any) {
    setDraft({ ...draft, RISK_CONFIG: { ...risk, [key]: value } });
  }
  function setRoot(key: string, value: any) {
    setDraft({ ...draft, [key]: value });
  }

  return (
    <>
      <Topbar
        title="Стратегия"
        status={
          dirty
            ? <StatusPill tone="warn">Несохранённые изменения</StatusPill>
            : <StatusPill tone="ok">Сохранено</StatusPill>
        }
      >
        <button className="btn btn-ghost" onClick={reset} disabled={!dirty}>
          <Undo2 size={16} /> Сбросить
        </button>
        <button className="btn btn-primary" onClick={save} disabled={!dirty || saving}>
          <Save size={16} /> Сохранить <span className="kbd">⌘S</span>
        </button>
      </Topbar>

      <main className="p-8">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
          <Card>
            <CardHead title="Параметры стратегии" icon={<Settings2 size={16}/>} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Бюджет, ₽">
                <input type="number" className="input num"
                  value={draft.budget ?? 1000000}
                  onChange={e => setRoot("budget", Number(e.target.value))}/>
              </Field>
              <Field label="Risk-free rate">
                <input type="number" step="0.001" className="input num"
                  value={draft.r ?? 0.16}
                  onChange={e => setRoot("r", Number(e.target.value))}/>
              </Field>
              <Field label="Default σ">
                <input type="number" step="0.01" className="input num"
                  value={draft.sigma ?? 0.22}
                  onChange={e => setRoot("sigma", Number(e.target.value))}/>
              </Field>
              <Field label="Тип стратегии">
                <select className="input"
                  value={draft.strategy ?? "straddle"}
                  onChange={e => setRoot("strategy", e.target.value)}>
                  <option value="straddle">Straddle</option>
                  <option value="butterfly">Butterfly</option>
                  <option value="iron_condor">Iron Condor</option>
                </select>
              </Field>
            </div>
          </Card>

          <Card>
            <CardHead title="Hard-фильтры" icon={<Filter size={16}/>} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Мин. open interest">
                <input type="number" className="input num"
                  value={risk.min_open_interest ?? 100}
                  onChange={e => setRisk("min_open_interest", Number(e.target.value))}/>
              </Field>
              <Field label="Мин. дневной объём">
                <input type="number" className="input num"
                  value={risk.min_daily_volume ?? 50}
                  onChange={e => setRisk("min_daily_volume", Number(e.target.value))}/>
              </Field>
              <Field label="Макс. bid-ask спред, %">
                <input type="number" step="0.1" className="input num"
                  value={(risk.max_spread_pct ?? 0.05) * 100}
                  onChange={e => setRisk("max_spread_pct", Number(e.target.value) / 100)}/>
              </Field>
              <Field label="Мин. дней до экспирации">
                <input type="number" className="input num"
                  value={risk.min_days_to_expiry ?? 7}
                  onChange={e => setRisk("min_days_to_expiry", Number(e.target.value))}/>
              </Field>
            </div>
          </Card>

          <Card>
            <CardHead title="Sizing (Kelly)" icon={<Shield size={16}/>} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Доля Kelly">
                <input type="number" step="0.05" className="input num"
                  value={risk.kelly_frac ?? 0.25}
                  onChange={e => setRisk("kelly_frac", Number(e.target.value))}/>
              </Field>
              <Field label="Макс. позиция, % от бюджета">
                <input type="number" step="0.01" className="input num"
                  value={(risk.max_position_size_pct ?? 0.05) * 100}
                  onChange={e => setRisk("max_position_size_pct", Number(e.target.value) / 100)}/>
              </Field>
              <Field label="Stop loss, %">
                <input type="number" className="input num"
                  value={(risk.stop_loss_pct ?? 0.20) * 100}
                  onChange={e => setRisk("stop_loss_pct", Number(e.target.value) / 100)}/>
              </Field>
              <Field label="Макс. портфельный γ-риск">
                <input type="number" step="0.0001" className="input num"
                  value={risk.max_portfolio_gamma ?? 0.001}
                  onChange={e => setRisk("max_portfolio_gamma", Number(e.target.value))}/>
              </Field>
            </div>
          </Card>

          <Card>
            <CardHead title="Модель" icon={<BrainCircuit size={16}/>} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Backend">
                <select className="input"
                  value={draft.model_backend ?? "auto"}
                  onChange={e => setRoot("model_backend", e.target.value)}>
                  <option value="auto">Авто (LightGBM → GBR → Dummy)</option>
                  <option value="lightgbm">LightGBM</option>
                  <option value="sklearn_gbr">sklearn GBR</option>
                  <option value="none">Без модели (analytic edge)</option>
                </select>
              </Field>
              <Field label="Доля валидации">
                <input type="number" step="0.05" className="input num"
                  value={draft.val_ratio ?? 0.2}
                  onChange={e => setRoot("val_ratio", Number(e.target.value))}/>
              </Field>
            </div>
            <div className="border-t border-border-soft pt-4 mt-4 text-xs text-text-2">
              Параметры записываются в <span className="num text-text-1">config_live.json</span> —
              читаются пайплайном при следующем прогоне.
            </div>
          </Card>
        </div>
      </main>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-xs text-text-2">{label}</span>
      {children}
    </label>
  );
}
