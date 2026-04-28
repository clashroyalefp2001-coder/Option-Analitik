# backtest/costs.py
"""Учет издержек и проскальзывания."""

def calculate_transaction_costs(price, quantity, commission_pct=0.0004, slippage_pct=0.0005):
    """
    Рассчитывает полные издержки на одну сделку.
    По умолчанию: комиссия Мосбиржи ~0.04% + проскальзывание 0.05%.
    """
    commission = abs(price * quantity * commission_pct)
    slippage = abs(price * quantity * slippage_pct)
    return commission + slippage

def adjust_price_for_entry(price, is_buy, slippage_pct=0.0005):
    """Корректировка цены входа: если покупаем - проскальзывание вверх, если продаем - вниз."""
    if is_buy:
        return price * (1 + slippage_pct)
    else:
        return price * (1 - slippage_pct)
