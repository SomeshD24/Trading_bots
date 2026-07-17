import datetime
from option_selector import round_nearest

class SignalProcessor:
    def __init__(self, state_manager, option_selector, order_manager, feed=None):
        self.state_manager = state_manager
        self.option_selector = option_selector
        self.order_manager = order_manager
        self.feed = feed

    def process_tick(self, ltp):
        state = self.state_manager.state
        direction = state["direction"]
        
        if state["base"] is None:
            state["base"] = round_nearest(ltp, 10)
            self.state_manager.save()
            
        base = state["base"]

        # If FLAT, check if we need to open the first leg
        if state["direction"] == "FLAT":
            if ltp >= base + 50:
                self.open_leg(base + 50, ltp, "ABOVE", "SHORT")
            elif ltp <= base - 50:
                self.open_leg(base - 50, ltp, "BELOW", "LONG")

        # Handle ABOVE (LONG) trend
        while state["direction"] == "ABOVE":
            last_leg_id, last_leg = self.state_manager.get_last_leg()
            if not last_leg:
                break
                
            trigger = last_leg.get("trigger_price", last_leg["entry_price"])
                
            if ltp >= trigger + 50:
                self.open_leg(trigger + 50, ltp, "ABOVE", "SHORT")
            elif ltp <= trigger - 50:
                self.close_leg(last_leg_id)
                # Check if no legs left
                if not self.state_manager.state["legs"]:
                    state["direction"] = "FLAT"
                    self.state_manager.save()
                    break
            else:
                break

        # Handle BELOW (SHORT) trend
        while state["direction"] == "BELOW":
            last_leg_id, last_leg = self.state_manager.get_last_leg()
            if not last_leg:
                break
                
            trigger = last_leg.get("trigger_price", last_leg["entry_price"])
                
            if ltp <= trigger - 50:
                self.open_leg(trigger - 50, ltp, "BELOW", "LONG")
            elif ltp >= trigger + 50:
                self.close_leg(last_leg_id)
                # Check if no legs left
                if not self.state_manager.state["legs"]:
                    state["direction"] = "FLAT"
                    self.state_manager.save()
                    break
            else:
                break


    def open_leg(self, target_level, actual_ltp, direction, future_side):
        state = self.state_manager.state
        
        trigger_price = target_level
        entry_price = actual_ltp
        
        # Parse monthly expiry to format it like "28 JUL"
        import datetime as dt
        try:
            m_exp = dt.datetime.strptime(state["monthly_expiry"], "%Y-%m-%d")
            # Format expected by Choice CSV SecDesc: "NIFTY26JULFUT" (Year is last 2 digits)
            fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
        except Exception:
            fut_sym = "NIFTY_FUT"
            
        # 1. Future order
        fut_order = self.order_manager.place_market_order(fut_sym, future_side, price_hint=entry_price)
        
        # 2 & 3. Select options
        short_opt = self.option_selector.select_short_opt(
            actual_ltp, direction, state["monthly_expiry"], state["next_monthly_expiry"]
        )
        long_opt = self.option_selector.select_long_opt(
            actual_ltp, direction, state["weekly_expiry"]
        )
        
        if not short_opt or not long_opt:
            print("Failed to find suitable options to open leg. Skipping.")
            return

        # Commit direction only after options are found
        state["direction"] = direction

        short_t = self.feed.symbol_master.get_option_token(short_opt['expiry'], short_opt['strike'], short_opt['type'])
        short_sym = self.feed.symbol_master.get_symbol(short_t) if short_t else f"NIFTY_{short_opt['strike']}_{short_opt['type']}"
        
        long_t = self.feed.symbol_master.get_option_token(long_opt['expiry'], long_opt['strike'], long_opt['type'])
        long_sym = self.feed.symbol_master.get_symbol(long_t) if long_t else f"NIFTY_{long_opt['strike']}_{long_opt['type']}"

        # Short Opt order (sell)
        short_order = self.order_manager.place_market_order(short_sym, "SELL", price_hint=short_opt['premium'])
        # Long Opt order (buy)
        long_order = self.order_manager.place_market_order(long_sym, "BUY", price_hint=long_opt['premium'])
        
        # 4. Save leg
        state["total_legs_opened"] = state.get("total_legs_opened", 0) + 1
        date_str = dt.datetime.now().strftime("%Y%m%d")
        leg_id = f"L{state['total_legs_opened']}_{date_str}"
        leg_data = {
            "trigger_price": trigger_price,
            "entry_price": entry_price,
            "future_side": future_side,
            "future_order_id": fut_order["order_id"],
            "monthly_expiry": state["monthly_expiry"],
            "short_opt": {
                "strike": short_opt["strike"],
                "type": short_opt["type"],
                "expiry": short_opt["expiry"],
                "premium": short_opt["premium"],
                "order_id": short_order["order_id"],
                "side": "SELL"
            },
            "long_opt": {
                "strike": long_opt["strike"],
                "type": long_opt["type"],
                "expiry": long_opt["expiry"],
                "premium": long_opt["premium"],
                "order_id": long_order["order_id"],
                "side": "BUY"
            },
            "status": "OPEN",
            "entry_time": datetime.datetime.now().isoformat()
        }
        
        self.state_manager.add_leg(leg_id, leg_data)
        print(f"Opened Leg {leg_id} for direction {direction}")
        
        if self.feed:
            self.feed.subscribe_symbols([fut_sym, short_sym, long_sym])

    def close_leg(self, leg_id):
        leg = self.state_manager.state["legs"][leg_id]
        
        pnl = 0.0
        if self.feed:
            short_t = self.feed.symbol_master.get_option_token(leg['short_opt']['expiry'], leg['short_opt']['strike'], leg['short_opt']['type'])
            short_sym = self.feed.symbol_master.get_symbol(short_t) if short_t else f"NIFTY_{leg['short_opt']['strike']}_{leg['short_opt']['type']}"
            
            long_t = self.feed.symbol_master.get_option_token(leg['long_opt']['expiry'], leg['long_opt']['strike'], leg['long_opt']['type'])
            long_sym = self.feed.symbol_master.get_symbol(long_t) if long_t else f"NIFTY_{leg['long_opt']['strike']}_{leg['long_opt']['type']}"
            
            try:
                m_exp = datetime.datetime.strptime(leg["monthly_expiry"], "%Y-%m-%d")
                fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
            except Exception:
                fut_sym = "NIFTY_FUT"
                
            fut_price = self.feed.prices.get(fut_sym, leg['entry_price'])
            short_price = self.feed.prices.get(short_sym, leg['short_opt']['premium'])
            long_price = self.feed.prices.get(long_sym, leg['long_opt']['premium'])
            
            fut_pnl = (fut_price - leg['entry_price']) * 65 if leg['future_side'] == "LONG" else (leg['entry_price'] - fut_price) * 65
            short_pnl = (leg['short_opt']['premium'] - short_price) * 65
            long_pnl = (long_price - leg['long_opt']['premium']) * 65
            
            legacy_rollover = leg.get("realized_pnl", 0.0) - (leg.get("hist_fut_pnl", 0.0) + leg.get("hist_short_pnl", 0.0) + leg.get("hist_long_pnl", 0.0))
            
            total_fut_pnl = fut_pnl + leg.get("hist_fut_pnl", 0.0)
            total_short_pnl = short_pnl + leg.get("hist_short_pnl", 0.0)
            total_long_pnl = long_pnl + leg.get("hist_long_pnl", 0.0) + legacy_rollover
            
            pnl = total_fut_pnl + total_short_pnl + total_long_pnl
            
        self.order_manager.close_position(leg)
        
        # Save to closed history
        leg["close_time"] = datetime.datetime.now().isoformat()
        leg["final_pnl"] = pnl
        
        if "closed_legs" not in self.state_manager.state:
            self.state_manager.state["closed_legs"] = []
        self.state_manager.state["closed_legs"].append({
            "leg_id": leg_id,
            "pnl": pnl,
            "close_time": leg["close_time"]
        })
        self.state_manager.state["realized_pnl"] = self.state_manager.state.get("realized_pnl", 0.0) + pnl
        
        from logger import log_leg
        leg["status"] = "CLOSED"
        leg["future_exit"] = fut_price
        leg["short_exit"] = short_price
        leg["long_exit"] = long_price
        leg["fut_pnl"] = total_fut_pnl
        leg["short_pnl"] = total_short_pnl
        leg["long_pnl"] = total_long_pnl
        log_leg(leg_id, leg, pnl)
        
        self.state_manager.remove_leg(leg_id)
        print(f"Closed Leg {leg_id} with PnL: {round(pnl, 2)}")
