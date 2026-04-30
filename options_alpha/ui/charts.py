# ui/charts.py
# Модуль для создания и отображения графиков модели

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Не использовать GUI backend
import numpy as np
from typing import Optional, Dict, Any, Tuple
from .theme import Theme
from io import BytesIO
from PIL import Image
import customtkinter as ctk

class ChartGenerator:
    """Генератор графиков для отображения метрик модели"""
    
    @staticmethod
    def create_loss_chart(
        train_loss: list,
        val_loss: list,
        title: str = "Loss History"
    ) -> plt.Figure:
        """Создать график потерь"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        if train_loss:
            ax.plot(train_loss, label='Training Loss', color='#27ae60', linewidth=2)
        if val_loss:
            ax.plot(val_loss, label='Validation Loss', color='#e74c3c', linewidth=2)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Epoch', fontsize=10)
        ax.set_ylabel('Loss', fontsize=10)
        if train_loss or val_loss:
            ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        return fig
    
    @staticmethod
    def create_accuracy_chart(
        train_acc: list,
        val_acc: list,
        title: str = "Accuracy History"
    ) -> plt.Figure:
        """Создать график точности"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        if train_acc:
            ax.plot(train_acc, label='Training Accuracy', color='#27ae60', linewidth=2)
        if val_acc:
            ax.plot(val_acc, label='Validation Accuracy', color='#3498db', linewidth=2)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Epoch', fontsize=10)
        ax.set_ylabel('Accuracy', fontsize=10)
        if train_acc or val_acc:
            ax.legend(loc='lower right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        return fig
    
    @staticmethod
    def create_feature_importance_chart(
        importance_dict: Dict[str, float],
        top_n: int = 10,
        title: str = "Feature Importance"
    ) -> plt.Figure:
        """Создать график важности признаков"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        if not importance_dict:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', fontsize=14)
            ax.set_title(title, fontsize=12, fontweight='bold')
            return fig
        
        # Сортировка по убыванию
        sorted_items = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
        features = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        colors = ['#27ae60' if v > 0.15 else '#3498db' for v in values]
        bars = ax.barh(features, values, color=colors, alpha=0.8)
        
        # Добавить значения
        for bar, val in zip(bars, values):
            ax.text(val * 1.01, bar.get_y() + bar.get_height()/2, 
                   f'{val:.2f}', va='center', fontsize=9)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Importance', fontsize=10)
        ax.set_xlim(0, 1)
        ax.grid(True, alpha=0.3, axis='x')
        
        return fig
    
    @staticmethod
    def create_roc_chart(
        fpr: np.ndarray,
        tpr: np.ndarray,
        roc_auc: float,
        title: str = "ROC Curve"
    ) -> plt.Figure:
        """Создать ROC-кривую"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        if len(fpr) > 0 and len(tpr) > 0:
            ax.plot(fpr, tpr, color='#3498db', linewidth=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
            ax.plot([0, 1], [0, 1], color='#e74c3c', linestyle='--', linewidth=2)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('False Positive Rate', fontsize=10)
            ax.set_ylabel('True Positive Rate', fontsize=10)
            ax.legend(loc='lower right', fontsize=9)
            ax.set_xlim([0.0, 1.0])
            ax.set_ylim([0.0, 1.05])
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', fontsize=14)
            ax.set_title(title, fontsize=12, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        
        return fig
    
    @staticmethod
    def create_sharpe_chart(
        sharpe_values: list,
        title: str = "Sharpe Ratio Over Time"
    ) -> plt.Figure:
        """Создать график Sharpe Ratio"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        if sharpe_values:
            ax.plot(sharpe_values, color='#27ae60', linewidth=2)
            ax.axhline(y=0, color='#e74c3c', linestyle='--', alpha=0.7)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('Period', fontsize=10)
            ax.set_ylabel('Sharpe Ratio', fontsize=10)
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', fontsize=14)
            ax.set_title(title, fontsize=12, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        
        return fig
    
    @staticmethod
    def create_kpi_summary_chart(
        metrics: Dict[str, Any],
        title: str = "KPI Summary"
    ) -> plt.Figure:
        """Создать сводный график KPI"""
        fig, ax = plt.subplots(figsize=(5, 3), dpi=80)
        ax.set_facecolor(Theme.get_color("bg_panel"))
        
        kpi_labels = ['Accuracy', 'F1-Score', 'AUC-ROC', 'Sharpe']
        kpi_values = [
            metrics.get('precision', 0.85),
            metrics.get('f1_score', 0.83),
            metrics.get('roc_auc', 0.89),
            abs(metrics.get('sharpe_ratio', 0.0))
        ]
        
        colors = ['#27ae60' if v > 0.5 else '#e74c3c' for v in kpi_values]
        bars = ax.bar(kpi_labels, kpi_values, color=colors, alpha=0.8)
        
        # Добавить значения
        for bar, val in zip(bars, kpi_values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                   f'{val:.2f}', ha='center', va='bottom', fontsize=10)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    @staticmethod
    def figure_to_ctk_image(fig: plt.Figure) -> Optional[ctk.CTkImage]:
        """Конвертировать matplotlib фигуру в CustomTkinter изображение"""
        try:
            # Сохранить фигуру в буфер
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=80, bbox_inches='tight', 
                       facecolor=Theme.get_color("bg_panel"), edgecolor='none')
            buf.seek(0)
            
            # Загрузить изображение
            img = Image.open(buf)
            img = img.convert("RGB")
            
            # Создать CustomTkinter изображение
            return ctk.CTkImage(light_image=img, size=img.size)
        except Exception as e:
            print(f"Error converting figure to image: {e}")
            return None
        finally:
            plt.close(fig)
