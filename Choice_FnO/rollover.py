import datetime
from logger import log_rollover
from option_selector import round_nearest

def format_full_option_symbol(symbol_master, expiry_date_str, strike, opt_type):
    if not expiry_date_str or not strike or not opt_type:
        return "N/A"
    if symbol_master:
        t = symbol_master.get_option_token(expiry_date_str, strike, opt_type)
        if t:
            sym = symbol_master.get_symbol(t)
            if sym and sym != "UNKNOWN_SYMBOL":
                return sym
    try:
        exp_dt = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        exp_str = exp_dt.strftime("%d%b%y").upper()
        return f"NIFTY {exp_str} {strike} {opt_type}"
    except Exception:
        return f"NIFTY {strike} {opt_type}"

def format_full_future_symbol(symbol_master, expiry_date_str):
    if not expiry_date_str:
        return "N/A"
    try:
        exp_dt = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        sym1 = f"NIFTY{exp_dt.strftime('%y%b').upper()}FUT"
        sym2 = f"NIFTY {exp_dt.strftime('%d%b%y').upper()} FUT"
        if symbol_master:
            for s in [sym1, sym2]:
                t = symbol_master.get_token(s)
                if t:
                    sym = symbol_master.get_symbol(t)
                    if sym and sym != "UNKNOWN_SYMBOL":
                        return sym
        exp_str = exp_dt.strftime("%d%b%y").upper()
        return f"NIFTY {exp_str} FUT"
    except Exception:
        return "NIFTY_FUT"

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
            
            # Calculate realized PnL of old long_opt FIRST
            old_long = leg["long_opt"]
            old_long_t = self.option_selector.feed.symbol_master.get_option_token(old_long['expiry'], old_long['strike'], old_long['type'])
            old_long_sym = self.option_selector.feed.symbol_master.get_symbol(old_long_t) if old_long_t else f"NIFTY_{old_long['strike']}_{old_long['type']}"
            
            rest_prices = self.option_selector.feed.get_multiple_touchline([old_long_sym]) if old_long_t else {}
            old_long_price = rest_prices.get(old_long_sym) or self.option_selector.feed.prices.get(old_long_sym, old_long['premium'])
            
            # Close old weekly long_opt
            self.order_manager.place_market_order(
                f"NIFTY_{old_long['strike']}_{old_long['type']}", "SELL", price_hint=old_long_price
            )
            
            long_pnl = (old_long_price - old_long['premium']) * 65
            leg["realized_pnl"] = leg.get("realized_pnl", 0.0) + long_pnl
            leg["hist_long_pnl"] = leg.get("hist_long_pnl", 0.0) + long_pnl
            
            
            # Update state
            new_long_opt["order_id"] = new_long_order["order_id"]
            new_long_opt["side"] = "BUY"
            
            sm = self.option_selector.feed.symbol_master if self.option_selector.feed else None
            old_long_full = format_full_option_symbol(sm, old_long['expiry'], old_long['strike'], old_long['type'])
            new_long_full = format_full_option_symbol(sm, new_long_opt['expiry'], new_long_opt['strike'], new_long_opt['type'])
            
            log_rollover(leg_id, "OPTION", old_long['premium'], new_long_opt['premium'], old_long['strike'], new_long_opt['strike'], 
                         old_long_full, new_long_full, new_weekly_expiry)
            
            leg["long_opt"] = new_long_opt
            self.state_manager.update_leg(leg_id, leg)
            print(f"Weekly rollover completed for {leg_id}")


    def perform_monthly_rollover(self, current_ltp):
        """
        Tuesday 3PM: roll future and short_opt to next month if their expiry is current_month_expiry.
        Since all legs enter the new future at the exact same market starting price,
        all rolled legs receive the same newly selected option strike for the next month.
        """
        state = self.state_manager.state
        current_month_expiry = state["monthly_expiry"]
        next_month_expiry = state["next_monthly_expiry"]
        direction = state["direction"]
        
        any_leg_rolled = False
        
        # 1. Calculate price shift and new future entry price
        shift = 0
        import datetime as dt
        new_fut_ltp = None
        try:
            m_exp = dt.datetime.strptime(next_month_expiry, "%Y-%m-%d")
            sym1 = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
            sym2 = f"NIFTY {m_exp.strftime('%d %b %Y').upper()} FUT"
            sym3 = f"NIFTY {m_exp.strftime('%y %b').upper()} FUT"
            fut_candidates = [sym1, sym2, sym3]
            
            if self.option_selector.feed:
                rest_prices = self.option_selector.feed.get_multiple_touchline(fut_candidates)
                for sym in fut_candidates:
                    if rest_prices.get(sym):
                        new_fut_ltp = rest_prices.get(sym)
                        break
                    if self.option_selector.feed.prices.get(sym):
                        new_fut_ltp = self.option_selector.feed.prices.get(sym)
                        break

            if new_fut_ltp:
                shift = round_nearest(new_fut_ltp - current_ltp, 10)
                print(f"Rollover Shift calculated: {shift} (Old LTP: {current_ltp}, New LTP: {new_fut_ltp})")
            else:
                print(f"Could not fetch live LTP for next monthly future ({sym1}). Shift is 0.")
        except Exception as e:
            print(f"Error calculating rollover shift: {e}")
            new_fut_ltp = None
            
        new_entry = new_fut_ltp if new_fut_ltp else (current_ltp + shift)

        # 2. Select unified new short option for next month (same strike across all rolled legs)
        # Search from furthest OTM (ATM ± 30) down to base (ATM ± 6) for first option with premium > 100
        unified_new_short_opt = None
        if direction != "FLAT":
            atm = self.option_selector.get_atm_strike(new_entry)
            opt_type = "PE" if direction == "ABOVE" else "CE"
            step = -50 if direction == "ABOVE" else 50
            target_strikes = [atm + (i * step) for i in range(30, 5, -1)]

            s_strike, s_prem = self.option_selector._evaluate_short_opt_rest(target_strikes, opt_type, next_month_expiry)
            if s_strike is not None:
                unified_new_short_opt = {
                    "strike": s_strike, "type": opt_type, "expiry": next_month_expiry, "premium": s_prem
                }
            else:
                # Fallback starting from ATM ± 6 strikes (300pts OTM)
                base_strike = atm + (6 * step)
                unified_new_short_opt = {
                    "strike": base_strike, "type": opt_type, "expiry": next_month_expiry, "premium": 150.0
                }

        # 3. Roll each open leg
        for leg_id, leg in state["legs"].items():
            if leg["status"] != "OPEN":
                continue
                
            leg_monthly_exp = leg.get("monthly_expiry", current_month_expiry)
            if leg_monthly_exp == current_month_expiry:
                old_short = leg.get("short_opt", {})
                
                # Preserve original entry price before updating to new entry
                if "original_entry_price" not in leg:
                    leg["original_entry_price"] = leg.get("entry_price")

                # Construct proper contract symbols for futures
                try:
                    m_old = dt.datetime.strptime(leg_monthly_exp, "%Y-%m-%d")
                    old_fut_sym = f"NIFTY{m_old.strftime('%y%b').upper()}FUT"
                except Exception:
                    old_fut_sym = "NIFTY_FUT"

                try:
                    m_new = dt.datetime.strptime(next_month_expiry, "%Y-%m-%d")
                    new_fut_sym = f"NIFTY{m_new.strftime('%y%b').upper()}FUT"
                except Exception:
                    new_fut_sym = "NIFTY_FUT"

                # Close old future
                fut_side_to_close = "SELL" if leg["future_side"] == "LONG" else "BUY"
                self.order_manager.place_market_order(old_fut_sym, fut_side_to_close, price_hint=current_ltp)
                
                fut_pnl = (current_ltp - leg['entry_price']) * 65 if leg['future_side'] == "LONG" else (leg['entry_price'] - current_ltp) * 65
                leg["hist_fut_pnl"] = leg.get("hist_fut_pnl", 0.0) + fut_pnl

                # Close old short option if expiring this month
                short_pnl = 0.0
                if old_short.get("expiry") == current_month_expiry:
                    old_short_t = self.option_selector.feed.symbol_master.get_option_token(old_short['expiry'], old_short['strike'], old_short['type']) if self.option_selector.feed.symbol_master else None
                    old_short_sym = self.option_selector.feed.symbol_master.get_symbol(old_short_t) if old_short_t else f"NIFTY_{old_short['strike']}_{old_short['type']}"
                    
                    rest_prices = self.option_selector.feed.get_multiple_touchline([old_short_sym]) if old_short_t else {}
                    old_short_price = rest_prices.get(old_short_sym) or self.option_selector.feed.prices.get(old_short_sym, old_short['premium'])
                    
                    short_side_to_close = "BUY"
                    self.order_manager.place_market_order(
                        old_short_sym, short_side_to_close, price_hint=old_short_price
                    )
                    short_pnl = (old_short['premium'] - old_short_price) * 65
                    leg["hist_short_pnl"] = leg.get("hist_short_pnl", 0.0) + short_pnl

                leg["realized_pnl"] = leg.get("realized_pnl", 0.0) + fut_pnl + short_pnl

                # Apply the market spread shift to the grid levels (trigger)
                new_trigger = leg.get("trigger_price", leg["entry_price"]) + shift
                
                # New future order
                new_fut_order = self.order_manager.place_market_order(new_fut_sym, leg["future_side"], price_hint=new_entry)
                
                # Subscribe feed to new future contract
                if self.option_selector.feed:
                    self.option_selector.feed.subscribe_symbols([new_fut_sym])
                    self.option_selector.feed.active_symbols.add(new_fut_sym)

                # Log FUTURE Rollover
                sm = self.option_selector.feed.symbol_master if self.option_selector.feed else None
                old_fut_full = format_full_future_symbol(sm, leg_monthly_exp)
                new_fut_full = format_full_future_symbol(sm, next_month_expiry)
                log_rollover(leg_id, "FUTURE", leg['entry_price'], new_entry, "N/A", "N/A", old_fut_full, new_fut_full, next_month_expiry)

                # Open unified new short_opt for this leg if old short_opt was expiring
                if old_short.get("expiry") == current_month_expiry and unified_new_short_opt:
                    new_short_opt = dict(unified_new_short_opt)
                    new_short_t = self.option_selector.feed.symbol_master.get_option_token(new_short_opt['expiry'], new_short_opt['strike'], new_short_opt['type']) if self.option_selector.feed.symbol_master else None
                    new_short_sym = self.option_selector.feed.symbol_master.get_symbol(new_short_t) if new_short_t else f"NIFTY_{new_short_opt['strike']}_{new_short_opt['type']}"

                    new_short_order = self.order_manager.place_market_order(
                        new_short_sym, "SELL", price_hint=new_short_opt['premium']
                    )
                    new_short_opt["order_id"] = new_short_order["order_id"]
                    new_short_opt["side"] = "SELL"
                    leg["short_opt"] = new_short_opt

                    old_short_full = format_full_option_symbol(sm, old_short.get('expiry'), old_short.get('strike'), old_short.get('type'))
                    new_short_full = format_full_option_symbol(sm, new_short_opt.get('expiry'), new_short_opt.get('strike'), new_short_opt.get('type'))
                    log_rollover(leg_id, "OPTION", old_short.get('premium'), new_short_opt['premium'], old_short.get('strike'), new_short_opt['strike'], 
                                 old_short_full, new_short_full, next_month_expiry)

                leg["entry_price"] = new_entry
                leg["trigger_price"] = new_trigger
                leg["future_order_id"] = new_fut_order["order_id"]
                leg["monthly_expiry"] = next_month_expiry
                
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
                next_month_d = datetime.datetime.strptime(state["monthly_expiry"], "%Y-%m-%d").date() + datetime.timedelta(days=15)
                _, next_next_exp = get_current_and_next_monthly_expiries(next_month_d)
                state["next_monthly_expiry"] = next_next_exp.isoformat()
            except Exception:
                pass
                
            self.state_manager.save()

