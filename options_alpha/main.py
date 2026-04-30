# Options Trading Alpha Engine — Main Entry Point
# Запускает современный дашборд

import sys
import os

# Добавляем путь к UI модулю
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Запуск дашборда
from ui.dashboard import main as run_dashboard

if __name__ == "__main__":
    run_dashboard()
