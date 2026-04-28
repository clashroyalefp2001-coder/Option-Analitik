# watcher.py
import os
import time
import pathlib
import subprocess
import sys

# --- CONFIG --------------------------------------------------------------
# Путь к нашему каталогу проекта
PROJECT_ROOT = pathlib.Path(r"C:\Project\Option Analitik\Hibrid Condor\options_alpha")
# Путь к файлу‑источнику с котировками
SOURCE_EXCEL = PROJECT_ROOT / "Option Si 06.2026.xlsx"

# Путь к скрипту, который меняет fetcher.py и запускает тесты
AUTO_UPDATE_SCRIPT = PROJECT_ROOT / "auto_update_fetcher.py"

# Интервал проверки (сек.) – 5 секунд для теста (после проверки можно вернуть 60)
INTERVAL = 5
# -----------------------------------------------------------------------


def _run_script(script_path: pathlib.Path) -> None:
    """
    Выполняет python‑скрипт и выводит stdout/stderr в консоль.
    Если скрипт завершился с ошибкой – бросаем исключение.
    """
    print(f"[Watcher] Выполняем: {script_path}")
    result = subprocess.run([sys.executable, str(script_path)],
                            capture_output=True,
                            text=True,
                            cwd=PROJECT_ROOT)
    print("[Watcher] stdout:\n", result.stdout)
    print("[Watcher] stderr:\n", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Скрипт завершился с кодом {result.returncode}")


def watch():
    """
    Главный цикл «наблюдателя». Каждую INTERVAL‑секунду проверяем
    время последнего изменения SOURCE_EXCEL.
    При изменении вызываем AUTO_UPDATE_SCRIPT.
    """
    last_mtime = None
    while True:
        time.sleep(INTERVAL)

        try:
            current_mtime = SOURCE_EXCEL.stat().st_mtime
        except FileNotFoundError:
            print("[Watcher] Файл не найден – пропускаем проверку")
            continue

        if last_mtime != current_mtime:
            print(f"[Watcher] Обнаружено изменение (mtime={current_mtime})")
            try:
                _run_script(AUTO_UPDATE_SCRIPT)   # <‑‑ ВАЖНО — обновление fetcher.py + тестов
                last_mtime = current_mtime         # запоминаем новое время
            except Exception as e:
                print("[Watcher] Ошибка при запуске auto_update_fetcher.py:", e)
        else:
            # Никаких изменений – просто тик‑тик
            pass


if __name__ == "__main__":
    watch()