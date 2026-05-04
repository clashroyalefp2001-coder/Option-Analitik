import React, { useEffect, useState } from "react";
import { Database, CheckCircle2, Layers, Table2, RefreshCw, Filter } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { api, type DataProfile } from "../lib/api";

export function Data() {
  const formatOptVal = (val: any) => {
    if (val == null || val === "" || String(val).toLowerCase() === "nan") return "—";
    const num = Number(val);
    if (isNaN(num) || num === 0) return "—";
    if (num % 1 !== 0) return Number(num.toFixed(4));
    return num;
  };

  const [profile, setProfile] = useState<DataProfile | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [instruments, setInstruments] = useState<string[]>([]);
  
  // Читаем последнее выбранное значение из localStorage
  const [selectedInstrument, setSelectedInstrument] = useState<string>(() => {
    return localStorage.getItem("selectedInstrument") || "";
  });

  async function load(instrumentFilter = selectedInstrument) {
    setLoading(true);
    setSuccess(false);
    try {
      const [p, o, instrs] = await Promise.all([
        api.dataProfile(instrumentFilter || undefined), 
        api.options(200, instrumentFilter || undefined),
        api.instruments()
      ]);
      let calculatedProfile: DataProfile = { ...p };
      
      if (o.rows && o.rows.length > 0) {
        const strikes = o.rows.map((r: any) => Number(r.strike)).filter((n: any) => !isNaN(n));
        const calls = o.rows.filter((r: any) => {
          const t = (r.type || r.option_type || "").toLowerCase();
          return t === "call";
        }).length;
        const puts = o.rows.filter((r: any) => {
          const t = (r.type || r.option_type || "").toLowerCase();
          return t === "put";
        }).length;
        
        let daysArray = o.rows.map((r: any) => {
          if (typeof r.days_to_expiry === 'number') return r.days_to_expiry;
          if (r.expiry_date && typeof r.expiry_date === 'string') {
            const match = r.expiry_date.match(/^(\d{4})(\d{2})(\d{2})$/);
            if (match) {
              const [_, year, month, day] = match;
              const date = new Date(Number(year), Number(month) - 1, Number(day));
              const diff = date.getTime() - Date.now();
              return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
            }
          }
          return null;
        }).filter((d: any) => d !== null) as number[];

        // If backend returned dummy values, or 0, we can fill them in
        if (!calculatedProfile.total) calculatedProfile.total = o.rows.length;
        if (!calculatedProfile.calls) calculatedProfile.calls = calls;
        if (!calculatedProfile.puts) calculatedProfile.puts = puts;
        if (!calculatedProfile.strike_min && strikes.length) calculatedProfile.strike_min = Math.min(...strikes);
        if (!calculatedProfile.strike_max && strikes.length) calculatedProfile.strike_max = Math.max(...strikes);
        if (!calculatedProfile.days_min && daysArray.length) calculatedProfile.days_min = Math.min(...daysArray);
        if (!calculatedProfile.days_max && daysArray.length) calculatedProfile.days_max = Math.max(...daysArray);
        if (!calculatedProfile.file || calculatedProfile.file === "—") calculatedProfile.file = "MOEX Live API (option_export.tsv)";
      }

      setProfile(calculatedProfile);
      setRows(o.rows);
      setInstruments(instrs.instruments);
      
      // Если выбранного инструмента нет в списке, сбрасываем фильтр
      if (instrumentFilter && !instrs.instruments.includes(instrumentFilter)) {
          setSelectedInstrument("");
          localStorage.removeItem("selectedInstrument");
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const handleInstrumentChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedInstrument(val);
    localStorage.setItem("selectedInstrument", val); // Запоминаем выбор
    load(val);
  };

  return (
    <>
      <Topbar
        title="Данные"
        status={
          <StatusPill tone="ok">
            Источник: {profile?.file ?? "—"} · {profile?.total ?? 0} контрактов
          </StatusPill>
        }
      >
        <div className="flex items-center gap-3">
          <div className="relative flex items-center bg-bg-2 border border-border rounded-lg px-2 py-1">
            <Filter size={14} className="text-text-3 mr-2" />
            <select 
              className="bg-transparent text-sm text-text-1 focus:outline-none appearance-none pr-4"
              value={selectedInstrument}
              onChange={handleInstrumentChange}
              disabled={loading}
            >
              <option value="">Все инструменты</option>
              {instruments.map(inst => (
                <option key={inst} value={inst}>{inst}</option>
              ))}
            </select>
          </div>
          <button 
            className={`btn ${success ? '!text-success !border-success bg-success/10' : ''}`} 
            onClick={() => load()} 
            disabled={loading}
          >
            {success ? <CheckCircle2 size={16} /> : <RefreshCw size={16} className={loading ? "animate-spin" : ""} />}
            {success ? "Обновлено" : "Перечитать"} <span className="kbd">⌘R</span>
          </button>
        </div>
      </Topbar>

      <main className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <div className="card-title mb-4"><Database size={16} className="text-text-2"/>Источник данных</div>
            <div className="font-mono text-xs text-text-2 break-all">{profile?.file ?? "—"}</div>
            <div className="flex justify-between text-xs text-text-2 mt-4">
              <span>Контрактов</span><span className="num text-text-1">{profile?.total ?? 0}</span>
            </div>
          </Card>
          <Card>
            <div className="card-title mb-4"><CheckCircle2 size={16} className="text-success"/>Валидация</div>
            <div className="text-sm text-text-2">
              {profile?.error ? <span className="text-danger">{profile.error}</span> : "Все колонки распознаны"}
            </div>
            <div className="flex justify-between text-sm mt-2"><span className="text-text-2">Calls/Puts</span><span className="num">{profile?.calls ?? 0} / {profile?.puts ?? 0}</span></div>
          </Card>
          <Card>
            <div className="card-title mb-4"><Layers size={16} className="text-text-2"/>Профиль</div>
            <div className="flex justify-between text-sm mt-2"><span className="text-text-2">Страйки</span><span className="num">{profile?.strike_min ?? 0} – {profile?.strike_max ?? 0}</span></div>
            <div className="flex justify-between text-sm mt-2"><span className="text-text-2">Срок до экспирации</span><span className="num">{profile?.days_min ?? 0} – {profile?.days_max ?? 0} д</span></div>
          </Card>
        </div>

        <Card className="!p-0 overflow-hidden">
          <div className="px-6 pt-6 flex justify-between items-center">
            <CardHead 
              title={selectedInstrument ? `Опционная доска: ${selectedInstrument}` : "Опционная доска"} 
              icon={<Table2 size={16}/>} 
            />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-text-3 border-b border-border">
                  {["Инструмент", "Тип","Страйк","Bid","Ask","Last","Mid","Fair","Δ","Γ","Vega","IV","OI","Vol"].map(h =>
                    <th key={h} className="px-4 py-3 font-medium">{h}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={14} className="px-4 py-12 text-center text-text-2">
                    {loading ? "Загрузка данных..." : "Нет данных для отображения. Убедитесь, что QUIK экспортирует котировки."}
                  </td></tr>
                )}
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-border-soft hover:bg-bg-2">
                    <td className="px-4 py-2.5 font-medium">{r.instrument || r.underlying_symbol || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`badge ${(r.type || r.option_type || "").toLowerCase() === "call" ? "badge-call" : "badge-put"}`}>{r.type || r.option_type || "—"}</span>
                    </td>
                    <td className="px-4 py-2.5 num">{r.strike}</td>
                    <td className="px-4 py-2.5 num">{r.bid}</td>
                    <td className="px-4 py-2.5 num">{r.ask}</td>
                    <td className="px-4 py-2.5 num text-text-500">{r.last || "—"}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.mid)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.fair_value)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.delta)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.gamma)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.vega)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.iv)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.open_interest)}</td>
                    <td className="px-4 py-2.5 num">{formatOptVal(r.volume)}</td>
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
