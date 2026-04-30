import { useEffect, useState } from "react";
import { Database, CheckCircle2, Layers, Table2, RefreshCw, Filter } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { api, type DataProfile } from "../lib/api";

export function Data() {
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
      setProfile(p);
      setRows(o.rows);
      setInstruments(instrs.instruments);
      
      // Если выбранного инструмента нет в списке, сбрасываем фильтр
      if (instrumentFilter && !instrs.instruments.includes(instrumentFilter)) {
          setSelectedInstrument("");
          localStorage.removeItem("selectedInstrument");
      }
      // Включаем зеленую индикацию успешной загрузки
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

  const dataSourceName = "MOEX ISS API (Live)";

  return (
    <>
      <Topbar
        title="Данные"
        status={
          <StatusPill tone="ok">
            Источник: {dataSourceName} · {profile?.total ?? 0} контрактов
          </StatusPill>
        }
      >
        <div className="flex items-center gap-3">
          <div className="relative flex items-center bg-bg-2 border border-border rounded-lg px-2 py-1">
            <Filter size={14} className="text-text-3 mr-2" />
            <select 
              className="bg-transparent text-sm text-text-1 focus:outline-none appearance-none pr-4 cursor-pointer"
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
            className={`btn ${success ? '!text-success !border-success bg-success/10' : 'btn-ghost'}`} 
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
            <div className="font-mono text-sm text-text-1 break-all flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
              </span>
              {dataSourceName}
            </div>
            <div className="flex justify-between text-xs text-text-2 mt-4">
              <span>Контрактов</span><span className="num text-text-1">{profile?.total ?? 0}</span>
            </div>
          </Card>
          <Card>
            <div className="card-title mb-4"><CheckCircle2 size={16} className="text-success"/>Валидация</div>
            <div className="text-sm text-text-2">
              {profile?.error ? <span className="text-danger">{profile.error}</span> : "Все данные получены корректно"}
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
          <div className="px-6 pt-6 pb-4 flex justify-between items-center">
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
                    {loading ? "Загрузка данных..." : "Нет данных для отображения. Подключение к MOEX могло быть прервано."}
                  </td></tr>
                )}
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-border-soft hover:bg-bg-2">
                    <td className="px-4 py-2.5 font-medium">{r.underlying_symbol ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`badge ${r.type === "call" ? "badge-call" : "badge-put"}`}>{r.type}</span>
                    </td>
                    <td className="px-4 py-2.5 num">{r.strike}</td>
                    <td className="px-4 py-2.5 num">{r.bid}</td>
                    <td className="px-4 py-2.5 num">{r.ask}</td>
                    <td className="px-4 py-2.5 num text-text-1 font-medium">{r.last ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.mid ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.fair_value ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.delta ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.gamma ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.vega ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.iv ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.open_interest ?? "—"}</td>
                    <td className="px-4 py-2.5 num">{r.volume ?? "—"}</td>
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