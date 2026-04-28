import { useEffect } from "react";

/**
 * Глобальные горячие клавиши.
 * - Ctrl/Cmd + R  → run pipeline
 * - Ctrl/Cmd + S  → save strategy config
 * - Ctrl/Cmd + L  → clear logs
 * - 1..6          → переход по экранам
 */
export type HotkeyMap = Record<string, (ev: KeyboardEvent) => void>;

export function useHotkeys(map: HotkeyMap) {
  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      const target = ev.target as HTMLElement | null;
      const editable =
        target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      const meta = ev.metaKey || ev.ctrlKey;
      const key = ev.key.toLowerCase();

      // Cmd/Ctrl + key
      if (meta) {
        const combo = `mod+${key}`;
        if (map[combo]) {
          ev.preventDefault();
          map[combo](ev);
          return;
        }
      }
      // Цифровые клавиши — игнорируем в полях ввода
      if (!editable && /^[1-6]$/.test(ev.key) && map[ev.key]) {
        map[ev.key](ev);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [map]);
}
