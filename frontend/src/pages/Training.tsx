import { useState, useEffect, useRef } from "react";
import { Play, Settings2, Cpu, CheckCircle2, ChevronRight, Activity, Terminal, Database, Server, Gauge } from "lucide-react";
import { Topbar } from "../components/Topbar";
import { Card, CardHead } from "../components/Card";
import { api } from "../lib/api";
import { motion, AnimatePresence } from "motion/react";

export function Training() {
  const [pipelineState, setPipelineState] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [config, setConfig] = useState<any>({});
  const [isEditingConfig, setIsEditingConfig] = useState(false);
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let id: any;
    async function load() {
      const [status, hist, cfg] = await Promise.all([
        api.getPipelineStatus(),
        api.getTrainingHistory(),
        api.getTrainingConfig()
      ]);
      
      if (status) setPipelineState(status);
      if (hist) setHistory(hist);
      if (cfg && !isEditingConfig) setConfig(cfg);

      if (logsRef.current && status?.running) {
        logsRef.current.scrollTop = logsRef.current.scrollHeight;
      }
    }
    load();
    id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [isEditingConfig]);

  async function startTraining() {
    await api.runBacktest(true); // run actual training
  }

  async function saveConfig() {
    await api.updateTrainingConfig(config);
    setIsEditingConfig(false);
  }

  const isRunning = pipelineState?.running;
  const logs = pipelineState?.log_tail || [];
  const step = pipelineState?.step;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Topbar title="Обучение Моделей" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHead title="Управление Пайплайном Обучения" icon={<Play className="w-4 h-4" />} />
            <div className="p-6">
              <div className="bg-gray-50 border border-gray-100 p-6 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-6">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <h4 className="text-xl font-bold text-gray-900">RL Агент (PPO)</h4>
                    <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">Reinforcement Learning</span>
                  </div>
                  <p className="text-sm text-gray-500 max-w-md leading-relaxed">
                    Алгоритм Proximal Policy Optimization обучается на исторических данных МОЕХ Si, находя оптимальные точки входа и динамический сайзинг для максимизации доходности при заданном риске.
                  </p>
                </div>
                {!isRunning ? (
                  <button 
                    onClick={startTraining}
                    className="w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-blue-200 active:scale-95 group"
                  >
                    <Play className="w-5 h-5 fill-current group-hover:scale-110 transition-transform" />
                    Запустить Обучение
                  </button>
                ) : (
                  <button disabled className="w-full sm:w-auto px-8 py-4 bg-white border-2 border-blue-600 text-blue-600 rounded-xl font-bold flex items-center justify-center gap-3 transition-all cursor-not-allowed">
                    <div className="relative">
                      <Activity className="w-5 h-5 animate-pulse" />
                      <div className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-ping" />
                    </div>
                    {step === "starting" ? "Инициализация..." : step ? `Этап: ${step.toUpperCase()}` : "Выполняется..."}
                  </button>
                )}
              </div>
            </div>
          </Card>

          <Card>
            <CardHead title="Последние Эксперименты" icon={<Database className="w-4 h-4" />} />
            <div className="px-6 py-2 overflow-hidden">
              <div className="divide-y divide-gray-50">
                {history.length > 0 ? history.map((exp) => (
                  <div key={exp.id} className="flex items-center justify-between py-4 group hover:bg-gray-50/50 -mx-6 px-6 transition-colors cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border-2 ${exp.is_active ? 'bg-green-50 border-green-100 text-green-600' : 'bg-gray-50 border-gray-100 text-gray-400'}`}>
                        {exp.is_active ? <CheckCircle2 className="w-6 h-6" /> : <Activity className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-3 mb-0.5">
                          <span className="font-bold text-gray-900 group-hover:text-blue-600 transition-colors uppercase tracking-tight">{exp.id}</span>
                          {exp.is_active && <span className="bg-green-100 text-green-700 text-[9px] font-black px-1.5 py-0.5 rounded uppercase">Active</span>}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span className="font-medium text-gray-600">{exp.label}</span>
                          <span className="w-1 h-1 rounded-full bg-gray-300" />
                          <span>{exp.backend || "Sb3"}</span>
                          <span className="w-1 h-1 rounded-full bg-gray-300" />
                          <span>{exp.trained_at ? new Date(exp.trained_at).toLocaleDateString() : "—"}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-8">
                      <div className="text-right hidden sm:block">
                        <p className="text-[10px] uppercase font-bold text-gray-400 tracking-widest mb-1">Win Rate</p>
                        <p className={`text-lg font-black ${exp.win_rate !== '—' ? 'text-gray-900' : 'text-gray-300'}`}>{exp.win_rate}</p>
                      </div>
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-gray-300 group-hover:text-blue-500 group-hover:bg-blue-50 transition-all">
                        <ChevronRight className="w-5 h-5" />
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="py-12 text-center text-gray-400">
                    <Database className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p className="text-sm font-medium">История экспериментов пуста</p>
                  </div>
                )}
              </div>
            </div>
          </Card>

          <Card>
            <CardHead title="Логи Пайплайна" icon={<Terminal size={14} />} />
            <div className="p-4 bg-gray-900 text-green-400 font-mono text-[11px] h-[300px] overflow-y-auto w-full rounded-b-xl scroll-smooth" ref={logsRef}>
              {logs.length === 0 ? (
                <div className="text-gray-600 italic">Ожидание запуска процесса...</div>
              ) : (
                logs.map((log: string, i: number) => (
                  <div key={i} className="py-0.5 border-b border-white/5 last:border-0">{log}</div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHead title="Параметры Обучения" icon={<Settings2 className="w-4 h-4" />} />
            <div className="p-6 space-y-4">
              {[
                { label: "Learning Rate", key: "learning_rate", default: "0.0003" },
                { label: "Batch Size", key: "batch_size", default: "2048" },
                { label: "Gamma (Discount)", key: "gamma", default: "0.99" },
                { label: "GAE Lambda", key: "gae_lambda", default: "0.95" },
                { label: "Clip Range", key: "clip_range", default: "0.2" },
              ].map((param) => (
                <div key={param.key} className="flex justify-between items-center group">
                  <label className="text-sm text-gray-500 font-medium">{param.label}</label>
                  {isEditingConfig ? (
                    <input 
                      type="text" 
                      value={config[param.key] || param.default} 
                      onChange={(e) => setConfig({...config, [param.key]: e.target.value})}
                      className="w-20 bg-gray-50 border border-gray-200 rounded px-2 py-1 text-xs font-mono text-right outline-none focus:border-blue-500 transition-colors"
                    />
                  ) : (
                    <span className="text-xs font-mono font-bold text-gray-900 bg-gray-50 px-3 py-1 rounded">{config[param.key] || param.default}</span>
                  )}
                </div>
              ))}

              <div className="pt-4">
                {isEditingConfig ? (
                  <div className="flex gap-2">
                    <button onClick={saveConfig} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold shadow-sm">Сохранить</button>
                    <button onClick={() => setIsEditingConfig(false)} className="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg text-sm font-bold">Отмена</button>
                  </div>
                ) : (
                  <button 
                    onClick={() => setIsEditingConfig(true)}
                    className="w-full py-2.5 border-2 border-gray-100 hover:border-blue-100 hover:bg-blue-50 text-blue-600 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2"
                  >
                    Изменить Параметры
                  </button>
                )}
              </div>
            </div>
          </Card>

          <Card>
             <CardHead title="Инфо" icon={<Server className="w-4 h-4" />} />
             <div className="p-6 space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">Node Status</span>
                  <div className="flex items-center gap-1.5 font-bold text-green-600">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    Online
                  </div>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">Pipeline Step</span>
                  <span className="font-mono font-bold text-gray-900">{step || "Idle"}</span>
                </div>
             </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
