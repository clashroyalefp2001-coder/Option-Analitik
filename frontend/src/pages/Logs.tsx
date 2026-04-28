import { useEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";

import { Topbar, StatusPill } from "../components/Topbar";
import { Card } from "../components/Card";
import { api } from "../lib/api";
import { useHotkeys } from "../hooks/useHotkeys";

type Level = "all" | "info" | "warn" | "err";

function classifyLine(line: string): "info" | "warn" | "err" | "ok" {
  const s = line.toUpperCase();
  if (s.includes("[ERROR]") || s.includes("ERR")) return "err";
  if (s.includes("[WARN]") || s.includes("WARNING")) return "warn";
  if (s.includes("[OK]") || s.includes("ЗАВЕРШЁН")) return "ok";
  return "info";
}

export function Logs() {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState("");
  const [level, setLevel] = useState<Level>("all");
  const tailRef = useRef<HTMLDivElement>(null);

  async function load() {
    const r = await api.logsTail(500);
    setLines(r.lines);
    setRunning(r.running);
  }
  useEffect(() => {
    load();
    const id = setInterval(load, 800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    tailRef.current?.scrollTo({ top: tailRef.current.scrollHeight });
  }, [lines]);

  function clear() { setLines([]); }
  useHotkeys({ "mod+l": () => clear() });

  const filtered = lines.filter(l => {
    if (filter && !l.toLowerCase().includes(filter.toLowerCase())) return false;
    if (level === "all") return true;
    const k = classifyLine(l);
    return level === "info" ? k === "info" || k === "ok" :
           level === "warn" ? k === "warn" :
           k === "err";
  });

  return (
    <>
      <Topbar
        title="Логи"
        status={
          <StatusPill tone={running ? "warn" : "ok"}>
            {running ? "Streaming · в работе" : `Простой · ${lines.length} строк`}
          </StatusPill>
        }
      >
        <input
          className="input"
          placeholder="Поиск…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{ width: 220 }}
        />
        <Toggle value={level} onChange={setLevel} options={[
          { value: "all", label: "Все" },
          { value: "info", label: "Info" },
          { value: "warn", label: "Warn" },
          { value: "err", label: "Error" },
        ]} />
        <button className="btn btn-ghost" onClick={clear}>
          <Trash2 size={16} /> Очистить <span className="kbd">⌘L</span>
        </button>
      </Topbar>

      <main className="p-8">
        <Card className="!p-0 overflow-hidden">
          <div
            ref={tailRef}
            className="font-mono text-[12.5px] leading-7 px-4 py-4 h-[640px] overflow-auto"
            style={{ background: "#0A0E14" }}
          >
            {filtered.length === 0 && (
              <div className="text-text-3">Лог пуст. Запустите пайплайн на экране «Бэктест».</div>
            )}
            {filtered.map((l, i) => {
              const k = classifyLine(l);
              const cls =
                k === "err" ? "text-danger" :
                k === "warn" ? "text-warning" :
                k === "ok"  ? "text-success" :
                                "text-brand-2";
              return (
                <div key={i}>
                  <span className={cls}>{l}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </main>
    </>
  );
}

function Toggle<T extends string>({
  value, onChange, options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex bg-bg-2 border border-border rounded-sm p-0.5">
      {options.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`px-4 py-1.5 rounded text-[13px] ${value === o.value ? "bg-bg-0 text-text-1 shadow" : "text-text-2"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
