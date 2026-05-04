# backtest/costs.py

def adjust_price_for_entry(price, is_buy=True, slippage_pct=0.001):
    """Adjusts price for slippage."""
    if is_buy:
        return price * (1 + slippage_pct)
    else:
        return price * (1 - slippage_pct)

def calculate_transaction_costs(price, quantity, comm_per_contract=0.65):
    """Calculates realistic option transaction costs per trade (buy or sell).
    
    Includes:
    - Broker commission: $0.65 (standard)
    - Exchange fees: ~$0.25 (weighted average)
    - OCC/Clearing fees: ~$0.05
    - Regulatory fees (SEC/FINRA): ~$0.05
    """
    total_fees_per_contract = comm_per_contract + 0.35 # Fixed extras
    return quantity * total_fees_per_contract

def calculate_exercise_assignment_costs(quantity, fee_per_event=5.0):
    """Costs associated with option exercise or assignment."""
    return fee_per_event # Usually flat or small extra
