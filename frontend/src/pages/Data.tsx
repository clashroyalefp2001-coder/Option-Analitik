import { useEffect, useState } from "react";
import { FileSpreadsheet, CheckCircle2, Layers, Table2, RefreshCw } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { api, type DataProfile } from "../lib/api";

export function Data() {
  const [profile, setProfile] = useState<DataProfile | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [p, o] = await Promise.all([api.dataProfile(), api.options(50)]);
      setProfile(p);
      setRows(o.rows);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <>
      <Topbar
        title="Данные"
        status={
          <StatusPill tone="ok">
            Файл: {profile?.file ?? "—"} · {profile?.total ?? 0} контрактов
          </StatusPill>
        }
      >
        <button className="btn" onClick={load} disabled={loading}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Перечитать <span className="kbd">⌘R</span>
        </button>
      </Topbar>

      <main className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <div className="card-title mb-4"><FileSpreadsheet size={16} className="text-text-2"/>Excel-файл</div>
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
          <div className="px-6 pt-6"><CardHead title="Опционная доска" icon={<Table2 size={16}/>} /></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-text-3 border-b border-border">
                  {["Тип","Страйк","Bid","Ask","Mid","Fair","Δ","Γ","Vega","IV","OI","Vol"].map(h =>
                    <th key={h} className="px-4 py-3 font-medium">{h}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={12} className="px-4 py-12 text-center text-text-2">
                    Загрузите файл `Option Si 06.2026.xlsx` в корень пайплайна и нажмите «Перечитать».
                  </td></tr>
                )}
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-border-soft hover:bg-bg-2">
                    <td className="px-4 py-2.5">
                      <span className={`badge ${r.type === "call" ? "badge-call" : "badge-put"}`}>{r.type}</span>
                    </td>
                    <td className="px-4 py-2.5 num">{r.strike}</td>
                    <td className="px-4 py-2.5 num">{r.bid}</td>
                    <td className="px-4 py-2.5 num">{r.ask}</td>
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
