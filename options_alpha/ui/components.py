# Reusable UI components for the dashboard

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Optional, Dict, Any
import pandas as pd
from .theme import Theme

class KPICard(ctk.CTkFrame):
    """Профессиональная карточка ключевой метрики"""
    
    def __init__(
        self,
        master,
        title: str,
        value: str = "0.00",
        subtitle: str = "",
        color: str = "accent",
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.value = value
        self.subtitle = subtitle
        
        # Стилизация - улучшенная
        self.configure(
            fg_color=Theme.get_color("bg_card"),
            corner_radius=Theme.BORDER_RADIUS,
            border_width=0
        )
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Заголовок - улучшенный
        self.title_label = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold"),
            text_color=Theme.get_color("text_secondary"),
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, padx=15, pady=(12, 6), sticky="w")
        
        # Значение - улучшенное
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=self._get_value_color(),
            anchor="w"
        )
        self.value_label.grid(row=1, column=0, padx=15, pady=6, sticky="w")
        
        # Подзаголовок - улучшенный
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
                text_color=Theme.get_color("text_secondary"),
                anchor="w"
            )
            self.subtitle_label.grid(row=2, column=0, padx=15, pady=(4, 12), sticky="w")
    
    def _get_value_color(self) -> str:
        """Цвет значения в зависимости от типа"""
        if self.title.lower() in ["max drawdown", "loss", "error"]:
            return Theme.get_color("error")
        elif self.title.lower() in ["accuracy", "precision", "recall", "f1", "sharpe"]:
            return Theme.get_color("success")
        return Theme.get_color("text_primary")
    
    def update(self, value: str, subtitle: str = ""):
        """Обновить значение и подзаголовок"""
        self.value_label.configure(text=value)
        if subtitle:
            self.subtitle = subtitle
            if self.subtitle_label.cget("text") != subtitle:
                self.subtitle_label.configure(text=subtitle)


class ChartPanel(ctk.CTkFrame):
    """Панель с matplotlib-графиком или изображением"""
    
    def __init__(
        self,
        master,
        title: str,
        width: int = 400,
        height: int = 250,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.width = width
        self.height = height
        self.figure: Optional[plt.Figure] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.image_label: Optional[ctk.CTkLabel] = None
        
        # Стилизация
        self.configure(
            fg_color=Theme.get_color("bg_card"),
            corner_radius=10,
            border_width=0
        )
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        self.title_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        # Контейнер для графика/изображения
        self.chart_container = ctk.CTkFrame(
            self,
            fg_color=Theme.get_color("bg_panel"),
            corner_radius=8
        )
        self.chart_container.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)
    
    def create_figure(self) -> plt.Figure:
        """Создать фигуру matplotlib"""
        if self.figure is None:
            self.figure = plt.Figure(figsize=(5, 3), dpi=80)
            self.figure.patch.set_facecolor(Theme.get_color("bg_panel"))
        return self.figure
    
    def plot(self, func):
        """Построить график через callback"""
        self.figure = self.create_figure()
        func(self.figure)
        
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def set_image(self, image: ctk.CTkImage):
        """Установить изображение вместо графика"""
        if self.image_label:
            self.image_label.destroy()
        
        self.image_label = ctk.CTkLabel(
            self.chart_container,
            image=image,
            text=""
        )
        self.image_label.pack(fill="both", expand=True)
    
    def clear(self):
        """Очистить график"""
        if self.figure:
            plt.close(self.figure)
            self.figure = None
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None


class ControlPanel(ctk.CTkFrame):
    """Панель управления с параметрами"""
    
    def __init__(self, master, title: str, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.controls: Dict[str, ctk.CTkBaseWidget] = {}
        
        # Стилизация
        self.configure(
            fg_color=Theme.get_color("bg_card"),
            corner_radius=10,
            border_width=0
        )
        
        self.grid_columnconfigure(1, weight=1)
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
    
    def add_control(self, name: str, label: str, control: ctk.CTkBaseWidget, row: int):
        """Добавить контрол"""
        label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            text_color=Theme.get_color("text_secondary")
        )
        label_widget.grid(row=row, column=0, padx=15, pady=5, sticky="w")
        
        control.grid(row=row, column=1, padx=15, pady=5, sticky="ew")
        self.controls[name] = control
    
    def get_value(self, name: str) -> Any:
        """Получить значение контрола"""
        control = self.controls.get(name)
        if control is None:
            return None
        if hasattr(control, "get"):
            return control.get()
        return None


class LogPanel(ctk.CTkFrame):
    """Панель логов"""
    
    def __init__(self, master, title: str, height: int = 150, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.height = height
        
        # Стилизация
        self.configure(
            fg_color=Theme.get_color("bg_card"),
            corner_radius=10,
            border_width=0
        )
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        self.title_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        # Текстовое поле
        self.log_text = ctk.CTkTextbox(
            self,
            fg_color=Theme.get_color("bg_panel"),
            text_color=Theme.get_color("text_primary"),
            corner_radius=8,
            wrap="word"
        )
        self.log_text.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        
        # Автоматический скролл
        self.log_text.configure(state="disabled")
    
    def append(self, message: str, color: str = None):
        """Добавить сообщение в лог"""
        self.log_text.configure(state="normal")
        
        # Добавляем сообщение без раскраски (CTkTextbox не поддерживает тэги)
        if color and ("error" in color.lower() or "ошибка" in color.lower()):
            self.log_text.insert("end", f"[ERROR] {message}\n")
        elif color and ("success" in color.lower() or "успешно" in color.lower()):
            self.log_text.insert("end", f"[OK] {message}\n")
        else:
            self.log_text.insert("end", f"{message}\n")
        
        self.log_text.configure(state="disabled")
        self.log_text.see("end")
    
    def clear(self):
        """Очистить логи"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


class HeaderPanel(ctk.CTkFrame):
    """Верхняя панель с заголовком"""
    
    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.subtitle = subtitle
        
        # Стилизация
        self.configure(
            fg_color=Theme.get_color("bg_secondary"),
            corner_radius=0,
            border_width=0
        )
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold"),
            text_color=Theme.get_color("text_primary")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Подзаголовок
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
                text_color=Theme.get_color("text_secondary")
            )
            self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")


class SidebarPanel(ctk.CTkFrame):
    """Боковая панель навигации"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Стилизация
        self.configure(
            fg_color=Theme.get_color("bg_secondary"),
            corner_radius=0,
            width=220
        )
        
        self.grid_rowconfigure(1, weight=1)
        
        # Логотип/название
        self.logo_label = ctk.CTkLabel(
            self,
            text="OPTIONS ALPHA",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold"),
            text_color=Theme.get_color("accent_primary")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Пункты меню
        self.menu_items: Dict[str, ctk.CTkButton] = {}
        
        self._add_menu_item("dashboard", "📊 Дашборд", self._on_dashboard_click)
        self._add_menu_item("model", "🤖 Модель", self._on_model_click)
        self._add_menu_item("settings", "⚙️ Настройки", self._on_settings_click)
    
    def _add_menu_item(self, name: str, text: str, callback):
        """Добавить пункт меню"""
        btn = ctk.CTkButton(
            self,
            text=text,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
            fg_color="transparent",
            hover_color=Theme.get_color("bg_card"),
            anchor="w",
            command=callback
        )
        btn.grid(row=len(self.menu_items), column=0, padx=10, pady=5, sticky="ew")
        self.menu_items[name] = btn
    
    def _on_dashboard_click(self):
        pass
    
    def _on_model_click(self):
        pass
    
    def _on_settings_click(self):
        pass
