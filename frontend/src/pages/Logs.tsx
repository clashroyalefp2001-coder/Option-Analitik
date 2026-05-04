import { useEffect, useState, useRef } from "react";
import { Topbar } from "../components/Topbar";
import { Terminal, CheckCircle2, RefreshCw, Play } from "lucide-react";
import { api } from "../lib/api";

export const Logs = () => {
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [runPipelineLoading, setRunPipelineLoading] = useState(false);
  const [runPipelineSuccess, setRunPipelineSuccess] = useState(false);

  useEffect(() => {
    const checkPipeline = async () => {
      try {
        const status = await api.getPipelineStatus();
        setPipelineStatus(status);
        if (status?.running) {
          setRunPipelineLoading(true);
        } else if (runPipelineLoading) {
          setRunPipelineLoading(false);
          setRunPipelineSuccess(true);
          setTimeout(() => setRunPipelineSuccess(false), 3000);
        }
      } catch(e) {
        // ignore initially
      }
    };
    checkPipeline();
    const id = setInterval(checkPipeline, 1000);
    return () => clearInterval(id);
  }, [runPipelineLoading]);

  useEffect(() => {
    if (logsEndRef.current) {
        logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [pipelineStatus?.log_tail]);

  async function runPipeline() {
    setRunPipelineLoading(true);
    setRunPipelineSuccess(false);
    try {
      await api.runBacktest(false);
    } catch (e) {
      console.error(e);
      setRunPipelineLoading(false);
    }
  }

  return (
    <>
      <Topbar title="Логи">
        <button 
            className={`btn ${runPipelineSuccess ? '!bg-success !text-white !border-success' : 'btn-primary'}`} 
            onClick={runPipeline}
            disabled={runPipelineLoading}
        >
            {runPipelineSuccess ? <CheckCircle2 size={16} /> : runPipelineLoading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
            {runPipelineSuccess ? "Завершено" : runPipelineLoading ? "В процессе..." : "Запустить пайплайн"}
        </button>
      </Topbar>
      <main className="p-8 h-[calc(100vh-70px)] flex flex-col">
        <div className="bg-[#1e1e1e] border border-gray-800 rounded-xl w-full shadow-2xl flex flex-col flex-1 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-[#252526] border-b border-gray-800">
                <div className="flex items-center gap-2 text-gray-300 text-sm font-medium">
                    <Terminal size={16} />
                    Выполнение пайплайна
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-[13px] leading-relaxed text-green-400 bg-[#1e1e1e]">
               {pipelineStatus?.log_tail?.map((log: string, i: number) => (
                   <div key={i} className="whitespace-pre-wrap">{log}</div>
               ))}
               {!pipelineStatus?.running && (!pipelineStatus?.log_tail || pipelineStatus.log_tail.length === 0) && (
                   <div className="text-gray-500 italic">Логи появятся при запуске...</div>
               )}
               {pipelineStatus?.running && <div className="text-gray-500 animate-pulse mt-2">_</div>}
               <div ref={logsEndRef} />
            </div>
        </div>
      </main>
    </>
  );
}
