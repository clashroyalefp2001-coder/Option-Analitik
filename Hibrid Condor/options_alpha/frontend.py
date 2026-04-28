import streamlit as st
import json
import subprocess
import os
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Options Trading Alpha",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 Options Trading Alpha Engine")
st.markdown("Автоматизированная система торговли американскими опционами на MOEX")

# Sidebar - стратегия и параметры
with st.sidebar:
    st.header("⚙️ Настройки стратегии")
    
    # Выбор стратегии
    strategy = st.selectbox(
        "Выберите стратегию:",
        ["straddle", "butterfly"],
        help="Straddle: покупка кола и пута на одном страйке. Butterfly: бабочка."
    )
    
    st.subheader("🎯 Параметры риска")
    
    # Параметры риска
    max_spread_pct = st.slider("Максимальный спред (%)", 0.001, 0.1, 0.01, 0.001)
    min_days_to_expiry = st.slider("Минимальных дней до экспирации", 1, 30, 5)
    max_position_size_pct = st.slider("Максимальный размер позиции (%)", 0.01, 0.2, 0.05, 0.01)
    min_edge = st.slider("Минимальный edge", 0.001, 0.1, 0.005, 0.001)
    
    st.subheader("🔥 Порог уверенности")
    confidence_threshold = st.slider("Порог уверенности", 0.1, 1.0, 0.7, 0.05)
    
    st.subheader("⚡ Быстрые действия")
    
    # Кнопки действий
    if st.button("🚀 Запустить пайплайн", type="primary"):
        run_pipeline()
    
    if st.button("🔄 Перезапустить watcher"):
        restart_watcher()

# Основной интерфейс
def run_pipeline():
    st.info("🔄 Запуск пайплайна...")
    
    # Создаем конфиг
    config = {
        "STRATEGY_TYPE": strategy,
        "RISK_CONFIG": {
            "max_spread_pct": max_spread_pct,
            "min_open_interest": 100,
            "min_daily_volume": 20,
            "min_days_to_expiry": min_days_to_expiry,
            "max_gamma_exposure_pct": 0.02,
            "max_vega_exposure_pct": 0.02,
            "max_delta_exposure_pct": 0.02,
            "max_position_size_pct": max_position_size_pct,
            "max_daily_loss_pct": 0.02,
            "min_edge": min_edge,
            "min_confidence": confidence_threshold
        }
    }
    
    # Сохраняем конфиг
    with open("config_live.json", "w") as f:
        json.dump(config, f, indent=2)
    
    try:
        # Запускаем пайплайн
        result = subprocess.run(
            ["python", "main.py"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            st.success("✅ Пайплайн успешно завершен!")
            st.json(json.loads(result.stdout))
            
            # Показываем результаты
            show_results()
        else:
            st.error(f"❌ Ошибка в пайплайне: {result.stderr}")
            
    except Exception as e:
        st.error(f"❌ Не удалось запустить пайплайн: {str(e)}")

def restart_watcher():
    st.info("🔄 Перезапуск watcher...")
    try:
        subprocess.run(["python", "watcher.py"], capture_output=True, text=True)
        st.success("✅ Watcher запущен")
    except Exception as e:
        st.error(f"❌ Ошибка: {str(e)}")

def show_results():
    st.header("📊 Результаты")
    
    # Показываем отчеты
    cols = st.columns(3)
    
    with cols[0]:
        try:
            if os.path.exists("reports/equity_curve.png"):
                st.image("reports/equity_curve.png", caption="Кривая капитала")
        except:
            st.warning("Картинка кривой капитала не найдена")
    
    with cols[1]:
        try:
            if os.path.exists("reports/drawdown.png"):
                st.image("reports/drawdown.png", caption="Просадки")
        except:
            st.warning("Картинка просадок не найдена")
    
    with cols[2]:
        try:
            if os.path.exists("reports/kpi_summary.png"):
                st.image("reports/kpi_summary.png", caption="KPI")
        except:
            st.warning("KPI не найдены")
    
    # Показываем HTML отчет
    if os.path.exists("reports/report.html"):
        st.markdown("### 📄 Полный отчет")
        st.info("Открытие HTML отчета...")
        st.markdown("Открыть [отчет](reports/report.html)")
    
    # Показываем трейды
    if os.path.exists("data/trades.csv"):
        st.markdown("### 💼 Трейды")
        try:
            trades_df = pd.read_csv("data/trades.csv")
            st.dataframe(trades_df)
        except:
            st.warning("Не удалось загрузить трейды")

# Информация о системе
st.divider()
st.header("ℹ️ О системе")
st.markdown("""
**Options Trading Alpha Engine** - система для автоматизированной торговли опционами.

**Особенности:**
- Автоматическая обработка Excel данных
- Расчет справедливых цен и греческих
- Фильтрация по рискам
- Бэктестинг
- Мониторинг KPI
- Веб интерфейс

**Структура:**
- 📊 Data fetching & cleaning
- 🧠 Feature engineering
- 🎯 Signal generation
- ⚡ Risk filtering
- 📈 Backtesting
- 📊 Monitoring
""")

st.markdown("---")
st.markdown("Система готова к работе! ⚡")