import { useState, useEffect } from "react";
import { Search, Filter, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";
import { Topbar } from "../components/Topbar";
import { Card } from "../components/Card";
import { api, type Trade } from "../lib/api";

export function TradesSearch() {
  const [query, setQuery] = useState("");
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const res = await api.trades();
      setTrades(res.trades);
    } finally {
      setLoading(false);
    }
  }

  const filtered = trades.filter(t => 
    (t.instrument || "").toLowerCase().includes(query.toLowerCase()) ||
    (t.type || "").toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Topbar title="Поиск сделок" />
      
      <Card className="p-6">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input 
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition-shadow"
              placeholder="Поиск по инструменту (например Si-3.24) или типу..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg flex items-center gap-2 font-medium transition-colors">
            <Filter className="w-5 h-5" />
            Фильтры
          </button>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 text-gray-900 border-b border-gray-100">
            <tr>
              <th className="p-4 font-medium">Дата и время</th>
              <th className="p-4 font-medium">Инструмент</th>
              <th className="p-4 font-medium">Тип</th>
              <th className="p-4 font-medium text-right">PnL (₽)</th>
              <th className="p-4 font-medium">Входы</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-500">Загрузка сделок...</td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-500">Сделки не найдены</td>
              </tr>
            ) : (
              filtered.map(t => (
                <tr key={t.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="p-4">
                    {t.date && !isNaN(new Date(t.date).getTime()) 
                      ? new Date(t.date).toLocaleString('ru-RU') 
                      : "—"}
                  </td>
                  <td className="p-4 font-medium text-gray-900">{t.instrument || t.symbol || "—"}</td>
                  <td className="p-4">
                    <span className="px-2.5 py-1 bg-gray-100 rounded-md text-xs font-medium">
                      {t.type}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <div className={`font-semibold flex items-center justify-end gap-1 ${t.pnl >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {t.pnl >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      {t.pnl > 0 ? "+" : ""}{t.pnl}
                    </div>
                  </td>
                  <td className="p-4">
                    <button 
                      onClick={() => setSelectedTrade(t)}
                      className="text-blue-600 hover:text-blue-800 p-1.5 hover:bg-blue-50 rounded-lg transition-colors inline-flex items-center gap-1"
                    >
                      Детали <ArrowRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>

      {selectedTrade && (
        <Card className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Детали сделки: {selectedTrade.id}</h3>
            <button onClick={() => setSelectedTrade(null)} className="text-gray-500 hover:text-gray-700">Закрыть</button>
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {(() => {
              const tradeLabels: Record<string, string> = {
                id: "ID сделки",
                instrument: "Инструмент",
                symbol: "Символ",
                type: "Тип",
                pnl: "PnL (₽)",
                date: "Дата и время",
                side: "Сторона",
                quantity: "Количество",
                entry_price: "Цена входа",
                exit_price: "Цена выхода",
                expected_exit_price: "Ожидаемая цена выхода",
                return: "Доходность",
                days_held: "Дней удержания",
                exit_reason: "Причина выхода",
                win_rate_sim: "Win Rate (симуляция)",
                n_simulations: "Кол-во симуляций",
                entry_date: "Дата входа",
                exit_date: "Дата выхода",
                s0: "S0",
                k: "K"
              };

              return Object.entries(selectedTrade).map(([key, value]) => {
                const label = tradeLabels[key] || key.replace(/_/g, ' ');
                return (
                  <div key={key}>
                    <dt className="font-medium text-gray-500 capitalize">{label}</dt>
                    <dd className="font-semibold">{String(value)}</dd>
                  </div>
                );
              });
            })()}
          </dl>
        </Card>
      )}
    </div>
  );
}
