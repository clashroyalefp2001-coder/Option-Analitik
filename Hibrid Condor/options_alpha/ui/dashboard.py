# Main dashboard for Options Trading Alpha Engine
# Modern desktop UI with customtkinter

import customtkinter as ctk
import subprocess
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import threading
import queue

from .theme import Theme
from .components import (
    KPICard,
    ChartPanel,
    ControlPanel,
    LogPanel,
    HeaderPanel,
    SidebarPanel
)
from .charts import ChartGenerator
import json
import matplotlib
matplotlib.use('Agg')  # Не использовать GUI backend
import pandas as pd
from datetime import datetime
import threading
import queue

class TradingDashboard:
    """Главный дашборд торговой системы"""
    
    def __init__(self):
        # Настройка темы
        Theme.apply()
        
        # Основное окно
        self.root = ctk.CTk()
        self.root.title("Options Trading Alpha Engine")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Настройка сетки
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Очередь для сообщений (должна быть до создания компонентов)
        self.log_queue = queue.Queue()
        
        # Инициализация компонентов
        self._create_layout()
        self._create_kpi_cards()
        self._create_charts()
        self._create_controls()
        self._create_logs()
        
        # Запуск обновления логов
        self._process_log_queue()
        
        # Live refresh для метрик (каждые 5 секунд)
        self._start_live_refresh()
    
    def _create_layout(self):
        """Создать основной макет с улучшенной структурой"""
        # Header - улучшенный
        self.header = HeaderPanel(
            self.root,
            title="Options Trading Alpha",
            subtitle="Автоматизированная система торговли опционами",
            width=1200
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=Theme.SPACING_LARGE, pady=(Theme.SPACING_LARGE, Theme.SPACING_LARGE//2))
        
        # Sidebar - улучшенный
        self.sidebar = SidebarPanel(self.root)
        self.sidebar.grid(row=1, column=0, sticky="ns", padx=(Theme.SPACING_STANDARD, 0))
        
        # Main content - улучшенный
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=Theme.get_color("bg_primary"),
            corner_radius=Theme.BORDER_RADIUS
        )
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=(0, Theme.SPACING_LARGE), pady=Theme.SPACING_STANDARD)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
    
    def _create_kpi_cards(self):
        """Создать карточки KPI"""
        # Заголовок секции
        kpi_title = ctk.CTkLabel(
            self.main_frame,
            text="Ключевые показатели",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        kpi_title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Карточки
        self.kpi_cards: Dict[str, KPICard] = {}
        
        cards_config = [
            ("Accuracy", "Loading...", "Precision: --"),
            ("F1-Score", "Loading...", "Recall: --"),
            ("Sharpe Ratio", "Loading...", "Annualized"),
            ("AUC-ROC", "Loading...", "Validation"),
            ("Training Samples", "Loading...", "Current dataset"),
            ("Epochs", "Loading...", "Completed"),
        ]
        
        for i, (title, value, subtitle) in enumerate(cards_config):
            card = KPICard(
                self.main_frame,
                title=title,
                value=value,
                subtitle=subtitle
            )
            card.grid(row=1, column=i % 4, padx=10, pady=10, sticky="nsew")
            self.kpi_cards[title] = card
        
        # Загрузка метрик модели
        self._load_model_metrics()
        
        # Настройка весов
        self.main_frame.grid_rowconfigure(1, weight=1)
        for i in range(4):
            self.main_frame.grid_columnconfigure(i, weight=1)
    
    def _create_charts(self):
        """Создать панели с графиками"""
        # Заголовок секции
        charts_title = ctk.CTkLabel(
            self.main_frame,
            text="Визуализация",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        charts_title.grid(row=2, column=0, padx=20, pady=20, sticky="w")
        
        # Графики в сетке 2x2
        self.charts: Dict[str, ChartPanel] = {}
        self.chart_images: Dict[str, ctk.CTkImage] = {}
        
        chart_configs = [
            ("Training Loss", 0, 2),
            ("Validation Loss", 0, 3),
            ("Feature Importance", 1, 0),
            ("Sharpe Ratio Curve", 1, 1),
        ]
        
        for i, (title, row, col) in enumerate(chart_configs):
            chart = ChartPanel(
                self.main_frame,
                title=title,
                width=300,
                height=200
            )
            chart.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.charts[title] = chart
        
        # Настройка весов
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)
        for i in range(4):
            self.main_frame.grid_columnconfigure(i, weight=1)
    
    def _create_controls(self):
        """Создать панель управления"""
        # Заголовок секции
        controls_title = ctk.CTkLabel(
            self.main_frame,
            text="Управление",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        controls_title.grid(row=3, column=0, columnspan=4, padx=20, pady=20, sticky="w")
        
        # Панель управления
        self.controls = ControlPanel(
            self.main_frame,
            title="Параметры системы"
        )
        self.controls.grid(row=4, column=0, columnspan=4, padx=20, pady=10, sticky="ew")
        
        # Контролы
        self.strategy_var = ctk.StringVar(value="straddle")
        self.controls.add_control(
            "strategy",
            "Стратегия:",
            ctk.CTkComboBox(
                self.controls,
                values=["straddle", "butterfly"],
                variable=self.strategy_var,
                width=200
            ),
            row=1
        )
        
        self.max_spread_var = ctk.DoubleVar(value=0.01)
        self.controls.add_control(
            "max_spread",
            "Макс. спред (%):",
            ctk.CTkSlider(
                self.controls,
                from_=0.001,
                to=0.1,
                variable=self.max_spread_var,
                width=200
            ),
            row=2
        )
        
        self.min_days_var = ctk.IntVar(value=5)
        self.controls.add_control(
            "min_days",
            "Мин. дней до экспирации:",
            ctk.CTkComboBox(
                self.controls,
                values=[str(i) for i in range(1, 31)],
                variable=self.min_days_var,
                width=100
            ),
            row=3
        )
        
        self.min_edge_var = ctk.DoubleVar(value=0.005)
        self.controls.add_control(
            "min_edge",
            "Мин. edge:",
            ctk.CTkSlider(
                self.controls,
                from_=0.001,
                to=0.1,
                variable=self.min_edge_var,
                width=200
            ),
            row=4
        )
        
        self.confidence_var = ctk.DoubleVar(value=0.7)
        self.controls.add_control(
            "confidence",
            "Порог уверенности:",
            ctk.CTkSlider(
                self.controls,
                from_=0.1,
                to=1.0,
                variable=self.confidence_var,
                width=200
            ),
            row=5
        )
        
        # Кнопки действий
        btn_frame = ctk.CTkFrame(self.controls, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, padx=15, pady=15, sticky="w")
        
        ctk.CTkButton(
            btn_frame,
            text="🚀 Запустить пайплайн",
            command=self.run_pipeline,
            height=40,
            width=180
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 Перезапустить watcher",
            command=self.restart_watcher,
            height=40,
            width=180
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="📊 Обновить графики",
            command=self.update_charts,
            height=40,
            width=180
        ).pack(side="left", padx=5)
    
    def _create_logs(self):
        """Создать панель логов"""
        # Заголовок секции
        logs_title = ctk.CTkLabel(
            self.main_frame,
            text="Логи системы",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        logs_title.grid(row=5, column=0, columnspan=4, padx=20, pady=20, sticky="w")
        
        # Панель логов
        self.logs = LogPanel(
            self.main_frame,
            title="Системные логи",
            height=150
        )
        self.logs.grid(row=6, column=0, columnspan=4, padx=20, pady=10, sticky="nsew")
        
        # Настройка веса строки
        self.main_frame.grid_rowconfigure(5, weight=0)
        self.main_frame.grid_rowconfigure(6, weight=1)
    
    def _log(self, message: str, color: str = None):
        """Добавить сообщение в очередь логов"""
        self.log_queue.put((message, color))
    
    def _process_log_queue(self):
        """Обработка очереди логов"""
        try:
            while True:
                message, color = self.log_queue.get_nowait()
                self.logs.append(message, color)
        except queue.Empty:
            pass
        
        # Планируем следующую проверку
        self.root.after(100, self._process_log_queue)
    
    def run_pipeline(self):
        """Запустить пайплайн"""
        self._log("=== Запуск пайплайна ===", "info")
        
        # Сохранить конфиг
        self._save_config()
        
        # Запустить в отдельном потоке
        thread = threading.Thread(target=self._execute_pipeline, daemon=True)
        thread.start()
    
    def _save_config(self):
        """Сохранить конфигурацию"""
        config = {
            "STRATEGY_TYPE": self.strategy_var.get(),
            "RISK_CONFIG": {
                "max_spread_pct": self.max_spread_var.get(),
                "min_open_interest": 0,
                "min_daily_volume": 0,
                "min_days_to_expiry": self.min_days_var.get(),
                "max_gamma_exposure_pct": 0.02,
                "max_vega_exposure_pct": 0.02,
                "max_delta_exposure_pct": 0.02,
                "max_position_size_pct": 0.05,
                "max_daily_loss_pct": 0.02,
                "min_edge": self.min_edge_var.get(),
                "min_confidence": self.confidence_var.get(),
            },
        }
        
        with open("config_live.json", "w", encoding="utf-8") as f:
            import json
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self._log("Конфиг сохранён → config_live.json", "success")
    
    def _execute_pipeline(self):
        """Выполнить пайплайн"""
        try:
            result = subprocess.run(
                [sys.executable, "main_pipeline.py"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Вывод stdout
            for line in result.stdout.splitlines():
                self._log(line)
            
            if result.returncode == 0:
                self._log("✅ Пайплайн завершён успешно", "success")
            else:
                self._log(f"❌ Пайплайн завершён с кодом {result.returncode}", "error")
                
        except Exception as e:
            self._log(f"❌ Ошибка: {str(e)}", "error")
    
    def restart_watcher(self):
        """Перезапустить watcher"""
        self._log("=== Перезапуск watcher ===", "info")
        
        try:
            subprocess.Popen(
                [sys.executable, "watcher.py"],
                cwd=os.getcwd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._log("✅ Watcher запущен в фоне", "success")
        except Exception as e:
            self._log(f"❌ Ошибка watcher: {str(e)}", "error")
    
    def _load_model_metrics(self):
        """Загрузить метрики модели из JSON файла и обновить KPI / графики."""
        metrics_path = "reports/model_metrics.json"
        if not os.path.exists(metrics_path):
            return

        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)

            if "f1_score" in metrics:
                self.kpi_cards["F1-Score"].update(f"{metrics['f1_score']:.2f}", "Validation")
            if "precision" in metrics:
                self.kpi_cards["Accuracy"].update(
                    f"{metrics['precision']:.2f}",
                    f"Recall: {metrics.get('recall', 0):.2f}",
                )
            if "roc_auc" in metrics:
                self.kpi_cards["AUC-ROC"].update(f"{metrics['roc_auc']:.2f}", "Validation")
            if "sharpe_ratio" in metrics:
                self.kpi_cards["Sharpe Ratio"].update(
                    f"{metrics['sharpe_ratio']:.2f}", "Annualized"
                )
            if "trading_samples" in metrics:
                self.kpi_cards["Training Samples"].update(
                    str(metrics["trading_samples"]), "Current dataset"
                )
            if "epochs" in metrics:
                self.kpi_cards["Epochs"].update(str(metrics["epochs"]), "Completed")

            self._update_all_charts(metrics)
        except Exception as e:
            self._log(f"Ошибка загрузки метрик: {e}", "error")


    def _update_all_charts(self, metrics):
        """Обновить все графики с реальными данными"""
        try:
            # Training Loss
            if "training_loss" in metrics and metrics["training_loss"] > 0:
                train_loss = [metrics["training_loss"]]
                val_loss = [metrics["validation_loss"]] if "validation_loss" in metrics else []
                fig = ChartGenerator.create_loss_chart(train_loss, val_loss, "Training Loss")
                img = ChartGenerator.figure_to_ctk_image(fig)
                if img and "Training Loss" in self.charts:
                    self.chart_images["Training Loss"] = img
                    self.charts["Training Loss"].set_image(img)
            
            # Validation Loss
            if "validation_loss" in metrics and metrics["validation_loss"] > 0:
                fig = ChartGenerator.create_loss_chart([], [metrics["validation_loss"]], "Validation Loss")
                img = ChartGenerator.figure_to_ctk_image(fig)
                if img and "Validation Loss" in self.charts:
                    self.chart_images["Validation Loss"] = img
                    self.charts["Validation Loss"].set_image(img)
            
            # Feature Importance
            if "feature_importance" in metrics and metrics["feature_importance"]:
                fig = ChartGenerator.create_feature_importance_chart(
                    metrics["feature_importance"],
                    title="Feature Importance"
                )
                img = ChartGenerator.figure_to_ctk_image(fig)
                if img and "Feature Importance" in self.charts:
                    self.chart_images["Feature Importance"] = img
                    self.charts["Feature Importance"].set_image(img)
            
            # Sharpe Ratio Curve
            if "sharpe_ratio" in metrics:
                sharpe_values = [metrics["sharpe_ratio"]]
                fig = ChartGenerator.create_sharpe_chart(sharpe_values, "Sharpe Ratio Curve")
                img = ChartGenerator.figure_to_ctk_image(fig)
                if img and "Sharpe Ratio Curve" in self.charts:
                    self.chart_images["Sharpe Ratio Curve"] = img
                    self.charts["Sharpe Ratio Curve"].set_image(img)
            
            # KPI Summary
            fig = ChartGenerator.create_kpi_summary_chart(metrics, "KPI Summary")
            img = ChartGenerator.figure_to_ctk_image(fig)
            if img:
                self.chart_images["KPI Summary"] = img
                # Add to charts if exists
                if "KPI Summary" in self.charts:
                    self.charts["KPI Summary"].set_image(img)
            
            self._log("✅ Графики обновлены с реальными данными", "success")
        except Exception as e:
            self._log(f"Ошибка обновления графиков: {str(e)}", "error")
    
    def update_charts(self):
        """Обновить графики"""
        self._log("Обновление графиков...", "info")
        
        # Загрузить метрики
        metrics_path = "reports/model_metrics.json"
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
                
                # Обновить все графики
                self._update_all_charts(metrics)
                
                self._log("✅ Графики обновлены", "success")
            except Exception as e:
                self._log(f"Ошибка обновления графиков: {str(e)}", "error")
        else:
            self._log("Файл метрик не найден", "info")
    
    def export_metrics_to_csv(self):
        """Экспорт метрик в CSV файл"""
        try:
            metrics_path = "reports/model_metrics.json"
            if not os.path.exists(metrics_path):
                self._log("Файл метрик не найден для экспорта", "error")
                return
            
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            
            # Создать DataFrame
            df = pd.DataFrame([metrics])
            
            # Сохранить в CSV
            export_path = f"reports/metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(export_path, index=False, encoding='utf-8-sig')
            
            self._log(f"✅ Метрики экспортированы: {export_path}", "success")
        except Exception as e:
            self._log(f"Ошибка экспорта: {str(e)}", "error")
    
    def export_metrics_to_excel(self):
        """Экспорт метрик в Excel файл"""
        try:
            metrics_path = "reports/model_metrics.json"
            if not os.path.exists(metrics_path):
                self._log("Файл метрик не найден для экспорта", "error")
                return
            
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            
            # Создать DataFrame
            df = pd.DataFrame([metrics])
            
            # Сохранить в Excel
            export_path = f"reports/metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(export_path, index=False, engine='openpyxl')
            
            self._log(f"✅ Метрики экспортированы в Excel: {export_path}", "success")
        except Exception as e:
            self._log(f"Ошибка экспорта в Excel: {str(e)}", "error")
    
    def _start_live_refresh(self):
        """Live refresh метрик каждые 5 секунд (запускается ровно один раз)."""
        # Защита от повторного запуска (раньше функция дублировалась 4 раза
        # и порождала 4 параллельных цикла обновления).
        if getattr(self, "_live_refresh_started", False):
            return
        self._live_refresh_started = True

        self._log("Live refresh запущен (обновление каждые 5 сек)", "info")

        def refresh_loop():
            self._load_model_metrics()
            self.root.after(5000, refresh_loop)

        refresh_loop()


    def run(self):
        """Запустить приложение"""
        self._log("=== Options Trading Alpha Engine ===", "info")
        self._log(f"Запуск: {datetime.now().strftime('%H:%M:%S')}", "info")
        self._log("Интерфейс готов к работе ⚡", "success")
        self.root.mainloop()


def main():
    """Точка входа"""
    dashboard = TradingDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
