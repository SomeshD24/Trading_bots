import os
import sys
import datetime

# Point to workspace directory
sys.path.insert(0, "c:\\Choice_FnO")

from state import BotState
from symbol_master import SymbolMaster
from feed import ChoiceAPIFeed
from orders import OrderManager
from option_selector import OptionSelector
from rollover import RolloverManager
from expiry_calc import get_ist_today, get_ist_now, get_current_and_next_monthly_expiries

def test_monthly_rollover_futures():
    print("--- TEST 1: IST Timezone Check ---")
    ist_today = get_ist_today()
    ist_now = get_ist_now()
    print(f"Current IST Time: {ist_now}")
    print(f"Current IST Date: {ist_today}")
    assert ist_today is not None
    print("[OK] IST Timezone helper test PASSED.")

    print("\n--- TEST 2: Monthly Futures Rollover Contract Symbols ---")
    state_mgr = BotState()
    # Mock initial state with 1 active leg
    current_exp, next_exp = get_current_and_next_monthly_expiries()
    
    state_mgr.state = {
        "base": 24000,
        "direction": "ABOVE",
        "monthly_expiry": current_exp.isoformat(),
        "next_monthly_expiry": next_exp.isoformat(),
        "weekly_expiry": "2026-08-04",
        "legs": {
            "L1_20260728": {
                "trigger_price": 24050,
                "entry_price": 24050,
                "future_side": "LONG",
                "future_order_id": "test-order-1",
                "monthly_expiry": current_exp.isoformat(),
                "short_opt": {
                    "strike": 23750,
                    "type": "PE",
                    "expiry": current_exp.isoformat(),
                    "premium": 150.0,
                    "order_id": "short-order-1",
                    "side": "SELL"
                },
                "long_opt": {
                    "strike": 24100,
                    "type": "CE",
                    "expiry": "2026-08-04",
                    "premium": 10.0,
                    "order_id": "long-order-1",
                    "side": "BUY"
                },
                "status": "OPEN"
            },
            "L2_20260728": {
                "trigger_price": 24100,
                "entry_price": 24100,
                "future_side": "LONG",
                "future_order_id": "test-order-2",
                "monthly_expiry": current_exp.isoformat(),
                "short_opt": {
                    "strike": 23800,
                    "type": "PE",
                    "expiry": current_exp.isoformat(),
                    "premium": 140.0,
                    "order_id": "short-order-2",
                    "side": "SELL"
                },
                "long_opt": {
                    "strike": 24150,
                    "type": "CE",
                    "expiry": "2026-08-04",
                    "premium": 12.0,
                    "order_id": "long-order-2",
                    "side": "BUY"
                },
                "status": "OPEN"
            }
        }
    }

    symbol_master = SymbolMaster()
    symbol_master._populate_mock_tokens()
    feed = ChoiceAPIFeed(symbol_master)
    
    orders_placed = []
    
    class MockOrderManager(OrderManager):
        def place_market_order(self, symbol, side, qty=1, price_hint=0):
            orders_placed.append((symbol, side, price_hint))
            return {
                "order_id": f"mock-{len(orders_placed)}",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "status": "CLOSED",
                "fill_price": price_hint
            }

    order_mgr = MockOrderManager(symbol_master, paper_trade=True)
    opt_selector = OptionSelector(feed)
    rollover_mgr = RolloverManager(state_mgr, opt_selector, order_mgr)

    old_m_str = current_exp.strftime('%y%b').upper()
    new_m_str = next_exp.strftime('%y%b').upper()
    expected_old_fut = f"NIFTY{old_m_str}FUT"
    expected_new_fut = f"NIFTY{new_m_str}FUT"

    print(f"Triggering monthly rollover for 2 open legs at LTP 24100...")
    rollover_mgr.perform_monthly_rollover(24100)

    print("\nOrders placed during rollover:")
    for o in orders_placed:
        print(f"  - Symbol: {o[0]}, Side: {o[1]}, PriceHint: {o[2]}")

    # Verify both legs received the EXACT SAME new short option strike
    leg1_short_strike = state_mgr.state["legs"]["L1_20260728"]["short_opt"]["strike"]
    leg2_short_strike = state_mgr.state["legs"]["L2_20260728"]["short_opt"]["strike"]
    
    print(f"\nLeg 1 new short strike: {leg1_short_strike}")
    print(f"Leg 2 new short strike: {leg2_short_strike}")

    assert leg1_short_strike == leg2_short_strike, f"Leg 1 ({leg1_short_strike}) and Leg 2 ({leg2_short_strike}) must have the same option strike!"
    
    print("[OK] Multiple legs unified option strike test PASSED.")


if __name__ == "__main__":
    test_monthly_rollover_futures()
