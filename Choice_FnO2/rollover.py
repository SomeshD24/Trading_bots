import datetime
from logger import log_rollover
from option_selector import round_nearest

class RolloverManager:
    def __init__(self, state_manager, option_selector, order_manager):
        self.state_manager = state_manager
        self.option_selector = option_selector
        self.order_manager = order_manager

    def perform_weekly_rollover(self, current_ltp):
        """
        Monday: buy new weekly long_opt first (fresh band search 8-12), then close old weekly long_opt.
        """
        state = self.state_manager.state
        new_weekly_expiry = state["weekly_expiry"] # Should be updated by scheduler before calling this
        
        for leg_id, leg in state["legs"].items():
            if leg["status"] != "OPEN":
                continue
                
            if leg["long_opt"]["expiry"] == new_weekly_expiry:
                print(f"Leg {leg_id} already has long_opt for {new_weekly_expiry}. Skipping weekly rollover.")
                continue
                
            # Buy new weekly long_opt
            direction = state["direction"]
            new_long_opt = self.option_selector.select_long_opt(current_ltp, direction, new_weekly_expiry)
            if not new_long_opt:
                print(f"Could not find new long opt for weekly rollover of {leg_id}")
                continue
                
            new_long_order = self.order_manager.place_market_order(
                f"NIFTY_{new_long_opt['strike']}_{new_long_opt['type']}", "BUY", price_hint=new_long_opt['premium']
            )
            
            # Close old weekly long_opt
            old_long = leg["long_opt"]
            self.order_manager.place_market_order(
                f"NIFTY_{old_long['strike']}_{old_long['type']}", "SELL"
            )
            
            # Calculate realized PnL of old long_opt
            old_long_t = self.option_selector.feed.symbol_master.get_option_token(old_long['expiry'], old_long['strike'], old_long['type'])
            old_long_sym = self.option_selector.feed.symbol_master.get_symbol(old_long_t) if old_long_t else f"NIFTY_{old_long['strike']}_{old_long['type']}"
            old_long_price = self.option_selector.feed.prices.get(old_long_sym, old_long['premium'])
            long_pnl = (old_long_price - old_long['premium']) * 65
            leg["realized_pnl"] = leg.get("realized_pnl", 0.0) + long_pnl
            leg["hist_long_pnl"] = leg.get("hist_long_pnl", 0.0) + long_pnl
            
            
            # Update state
            new_long_opt["order_id"] = new_long_order["order_id"]
            new_long_opt["side"] = "BUY"
            
            log_rollover(old_long['premium'], new_long_opt['premium'], old_long['strike'], new_long_opt['strike'], 
                         f"NIFTY_{old_long['strike']}_{old_long['type']}", f"NIFTY_{new_long_opt['strike']}_{new_long_opt['type']}", new_weekly_expiry)
            
            leg["long_opt"] = new_long_opt
            self.state_manager.update_leg(leg_id, leg)
            print(f"Weekly rollover completed for {leg_id}")


    def perform_monthly_rollover(self, current_ltp):
        """
        Tuesday 3PM: roll future and short_opt to next month if their expiry is current_month_expiry.
        """
        state = self.state_manager.state
        current_month_expiry = state["monthly_expiry"]
        next_month_expiry = state["next_monthly_expiry"]
        direction = state["direction"]
        
        any_leg_rolled = False
        
        # 1. Calculate price shift between old future and new future
        shift = 0
        import datetime as dt
        try:
            m_exp = dt.datetime.strptime(next_month_expiry, "%Y-%m-%d")
            new_fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
            rest_prices = self.option_selector.feed.get_multiple_touchline([new_fut_sym])
            new_fut_ltp = rest_prices.get(new_fut_sym)
            if new_fut_ltp:
                shift = round_nearest(new_fut_ltp - current_ltp, 10)
                print(f"Rollover Shift calculated: {shift} (Old LTP: {current_ltp}, New LTP: {new_fut_ltp})")
        except Exception as e:
            print(f"Error calculating rollover shift: {e}")
            
        for leg_id, leg in state["legs"].items():
            if leg["status"] != "OPEN":
                continue
                
            if leg["short_opt"]["expiry"] == current_month_expiry:
                # Close old future + short_opt
                fut_side_to_close = "SELL" if leg["future_side"] == "LONG" else "BUY"
                self.order_manager.place_market_order("NIFTY_FUT_OLD", fut_side_to_close)
                
                short_side_to_close = "BUY" # we are short, so we buy back
                old_short = leg["short_opt"]
                self.order_manager.place_market_order(
                    f"NIFTY_{old_short['strike']}_{old_short['type']}", short_side_to_close
                )
                
                # Calculate realized PnL of old future and short_opt
                old_short_t = self.option_selector.feed.symbol_master.get_option_token(old_short['expiry'], old_short['strike'], old_short['type'])
                old_short_sym = self.option_selector.feed.symbol_master.get_symbol(old_short_t) if old_short_t else f"NIFTY_{old_short['strike']}_{old_short['type']}"
                old_short_price = self.option_selector.feed.prices.get(old_short_sym, old_short['premium'])
                
                fut_pnl = (current_ltp - leg['entry_price']) * 65 if leg['future_side'] == "LONG" else (leg['entry_price'] - current_ltp) * 65
                short_pnl = (old_short['premium'] - old_short_price) * 65
                leg["realized_pnl"] = leg.get("realized_pnl", 0.0) + fut_pnl + short_pnl
                leg["hist_fut_pnl"] = leg.get("hist_fut_pnl", 0.0) + fut_pnl
                leg["hist_short_pnl"] = leg.get("hist_short_pnl", 0.0) + short_pnl

                
                # Apply the market spread shift to the grid levels (trigger)
                new_trigger = leg.get("trigger_price", leg["entry_price"]) + shift
                
                # All legs enter the new future at the exact same market starting price
                new_entry = new_fut_ltp if new_fut_ltp else (current_ltp + shift)
                
                # New future order
                new_fut_order = self.order_manager.place_market_order("NIFTY_FUT_NEW", leg["future_side"], price_hint=new_entry)
                
                # New short_opt calculation uses the actual entry market price
                atm = self.option_selector.get_atm_strike(new_entry)
                opt_type = "PE" if direction == "ABOVE" else "CE"
                offset = -300 if direction == "ABOVE" else 300
                base_strike = atm + offset
                
                # Try new target expiry
                new_short_opt = None
                premium = self.option_selector.feed.get_option_premium(base_strike, opt_type, next_month_expiry)
                if premium > 100:
                    new_short_opt = {
                        "strike": base_strike, "type": opt_type, "expiry": next_month_expiry, "premium": premium
                    }
                else:
                    current_strike = base_strike
                    while True:
                        premium = self.option_selector.feed.get_option_premium(current_strike, opt_type, next_month_expiry)
                        if premium > 100:
                            new_short_opt = {
                                "strike": current_strike, "type": opt_type, "expiry": next_month_expiry, "premium": premium
                            }
                            break
                        current_strike += -50 if direction == "ABOVE" else 50
                        if abs(current_strike - atm) > 2000: break

                if not new_short_opt:
                    print(f"Could not find new short opt for monthly rollover of {leg_id}")
                    continue
                    
                new_short_order = self.order_manager.place_market_order(
                    f"NIFTY_{new_short_opt['strike']}_{new_short_opt['type']}", "SELL", price_hint=new_short_opt['premium']
                )
                
                # Update State
                log_rollover(leg["entry_price"], new_entry, old_short["strike"], new_short_opt["strike"], 
                             f"NIFTY_{old_short['strike']}_{old_short['type']}", f"NIFTY_{new_short_opt['strike']}_{new_short_opt['type']}", next_month_expiry)
                
                leg["entry_price"] = new_entry
                leg["trigger_price"] = new_trigger
                leg["future_order_id"] = new_fut_order["order_id"]
                leg["monthly_expiry"] = next_month_expiry
                new_short_opt["order_id"] = new_short_order["order_id"]
                new_short_opt["side"] = "SELL"
                leg["short_opt"] = new_short_opt
                
                self.state_manager.update_leg(leg_id, leg)
                any_leg_rolled = True
                print(f"Monthly rollover completed for {leg_id}")
                
        if any_leg_rolled:
            if state["base"] is not None:
                state["base"] += shift
            state["monthly_expiry"] = state["next_monthly_expiry"]
            
            from expiry_calc import get_current_and_next_monthly_expiries
            import datetime
            try:
                # Calculate the NEXT next month's expiry to have it ready for the following month
                # Just call the helper but feed it a date that is clearly in the next month
                next_month_d = datetime.datetime.strptime(state["monthly_expiry"], "%Y-%m-%d").date() + datetime.timedelta(days=15)
                _, next_next_exp = get_current_and_next_monthly_expiries(next_month_d)
                state["next_monthly_expiry"] = next_next_exp.isoformat()
            except Exception:
                pass
                
            self.state_manager.save()
