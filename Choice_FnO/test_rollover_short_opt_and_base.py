import sys
import datetime

sys.path.insert(0, "c:\\Choice_FnO")

from state import BotState
from symbol_master import SymbolMaster
from feed import ChoiceAPIFeed
from orders import OrderManager
from option_selector import OptionSelector
from rollover import RolloverManager
from expiry_calc import get_current_and_next_monthly_expiries

def test_short_opt_selection_order():
    print("--- TEST 1: Short Option Search Order Starting from ATM +/- 6 ---")
    
    # Mock feed with controlled touchline prices
    class MockFeed:
        def __init__(self):
            self.symbol_master = SymbolMaster()
            self.symbol_master._populate_mock_tokens()
            self.prices = {}
            
            exp_date = datetime.datetime.strptime("2026-08-25", "%Y-%m-%d").date()
            for s in [23750, 23800, 23850, 23900, 23950, 24000, 24050, 24100]:
                token = f"tok_{s}"
                sym = f"NIFTY_{s}_PE"
                self.symbol_master.option_chain[(exp_date, "PE", float(s))] = token
                self.symbol_master.token_to_symbol[token] = sym
                self.symbol_master.symbol_to_token[sym] = token

        def get_multiple_touchline(self, symbols):
            # Return custom prices for test
            # ATM = 24100, ABOVE trend (opt_type = PE)
            # i=6: 23800 PE -> premium 120 (> 100) -> should be selected first!
            # i=7: 23750 PE -> premium 105 (> 100) -> was selected in old code because it checked i=30..6!
            # i=5: 23850 PE -> premium 160 (> 100)
            return {
                "NIFTY_23800_PE": 120.0,
                "NIFTY_23750_PE": 105.0,
                "NIFTY_23850_PE": 160.0
            }

    feed = MockFeed()
    opt_selector = OptionSelector(feed)

    # Let's override _evaluate_short_opt_rest for direct verification
    # When ATM = 24100, direction = "ABOVE", current_monthly_expiry = "2026-08-25"
    # target_strikes evaluated in order: [23800, 23850, 23900, 23950, 24000, 24050, 24100]
    res = opt_selector.select_short_opt(24100, "ABOVE", "2026-08-25", "2026-09-29")
    print(f"Selected short option: {res}")
    
    assert res is not None, "Failed to select short option"
    assert res["strike"] == 23800, f"Expected strike 23800 (ATM - 6 strikes), but got {res['strike']}"
    assert res["premium"] == 120.0, f"Expected premium 120.0, but got {res['premium']}"
    print("[OK] Short option search starting from ATM +/- 6 PASSED.")


def test_monthly_rollover_base_update():
    print("\n--- TEST 2: Monthly Rollover Base Update with Future Shift ---")
    state_mgr = BotState()
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
            }
        }
    }

    class MockFeedWithPrices:
        def __init__(self):
            self.symbol_master = SymbolMaster()
            self.symbol_master._populate_mock_tokens()
            self.prices = {}
            self.active_symbols = set()
            
            for s in [23750, 23800, 23850, 23900, 23950, 24000, 24050, 24100, 24150]:
                token = f"tok_next_{s}"
                sym = f"NIFTY_{s}_PE"
                self.symbol_master.option_chain[(next_exp, "PE", float(s))] = token
                self.symbol_master.token_to_symbol[token] = sym
                self.symbol_master.symbol_to_token[sym] = token

        def subscribe_symbols(self, symbols):
            self.active_symbols.update(symbols)

        def get_multiple_touchline(self, symbols):
            next_m_str = next_exp.strftime('%y%b').upper()
            target_sym = f"NIFTY{next_m_str}FUT"
            # Return new future LTP 24150 (shift = 24150 - 24100 = +50)
            res = {}
            for s in symbols:
                if s == target_sym or "FUT" in s:
                    res[s] = 24150.0
                elif "PE" in s:
                    res[s] = 130.0
            return res

    feed = MockFeedWithPrices()
    
    class MockOrderManager(OrderManager):
        def place_market_order(self, symbol, side, qty=1, price_hint=0):
            return {
                "order_id": "mock-order",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "status": "CLOSED",
                "fill_price": price_hint
            }

    order_mgr = MockOrderManager(feed.symbol_master, paper_trade=True)
    opt_selector = OptionSelector(feed)
    rollover_mgr = RolloverManager(state_mgr, opt_selector, order_mgr)

    old_base = state_mgr.state["base"] # 24000
    print(f"Base before rollover: {old_base}")

    # Trigger rollover with current LTP 24100, new future LTP 24150 (shift +50)
    rollover_mgr.perform_monthly_rollover(24100)

    new_base = state_mgr.state["base"]
    print(f"Base after rollover: {new_base}")

    assert new_base == old_base + 50, f"Expected new base to be {old_base + 50}, but got {new_base}"
    print("[OK] Base update on monthly rollover PASSED.")

if __name__ == "__main__":
    test_short_opt_selection_order()
    test_monthly_rollover_base_update()
