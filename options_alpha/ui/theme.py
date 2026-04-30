# Theme configuration for the dashboard
# Professional dark theme with modern color palette

import customtkinter as ctk
from typing import Tuple

class Theme:
    """Профессиональная тема оформления дашборда"""
    
    # Основные цвета - современная палитра
    COLOR_BG_PRIMARY = "#0f172a"  # Глубокий синий
    COLOR_BG_SECONDARY = "#1e293b"  # Светлее
    COLOR_BG_CARD = "#334155"  # Карточки
    COLOR_BG_PANEL = "#1e293b"  # Панели
    
    # Акцентные цвета - профессиональные
    COLOR_ACCENT_PRIMARY = "#3b82f6"  # Яркий синий
    COLOR_ACCENT_SECONDARY = "#60a5fa"  # Светлый синий
    
    # Статусные цвета - сбалансированные
    COLOR_SUCCESS = "#10b981"  # Изумрудный
    COLOR_WARNING = "#f59e0b"  # Янтарный
    COLOR_ERROR = "#ef4444"  # Красный
    COLOR_INFO = "#3b82f6"  # Синий
    
    # Текст - высокая контрастность
    COLOR_TEXT_PRIMARY = "#f8fafc"  # Почти белый
    COLOR_TEXT_SECONDARY = "#94a3b8"  # Серый
    COLOR_TEXT_DISABLED = "#64748b"  # Темный серый
    
    # Шрифты - современные
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_TITLE = 24  # Увеличен
    FONT_SIZE_HEADING = 18  # Увеличен
    FONT_SIZE_BODY = 13  # Увеличен
    FONT_SIZE_SMALL = 11  # Увеличен
    
    # Дополнительные стили
    BORDER_RADIUS = 12  # Скругление
    SPACING_STANDARD = 15  # Стандартный отступ
    SPACING_LARGE = 20  # Большой отступ
    
    @classmethod
    def apply(cls) -> None:
        """Применить тему ко всему приложению"""
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
    @classmethod
    def get_color(cls, name: str) -> str:
        """Получить цвет по имени"""
        colors = {
            "bg_primary": cls.COLOR_BG_PRIMARY,
            "bg_secondary": cls.COLOR_BG_SECONDARY,
            "bg_card": cls.COLOR_BG_CARD,
            "bg_panel": cls.COLOR_BG_PANEL,
            "accent_primary": cls.COLOR_ACCENT_PRIMARY,
            "accent_secondary": cls.COLOR_ACCENT_SECONDARY,
            "success": cls.COLOR_SUCCESS,
            "warning": cls.COLOR_WARNING,
            "error": cls.COLOR_ERROR,
            "info": cls.COLOR_INFO,
            "text_primary": cls.COLOR_TEXT_PRIMARY,
            "text_secondary": cls.COLOR_TEXT_SECONDARY,
        }
        return colors.get(name, cls.COLOR_BG_PRIMARY)
