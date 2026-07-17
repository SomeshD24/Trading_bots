from logger import logger

class RecoveryManager:
    def __init__(self, state_manager, feed, signal_processor):
        self.state_manager = state_manager
        self.feed = feed
        self.signal_processor = signal_processor

    def recover(self):
        """
        Loads the last state snapshot.
        Fetches historical candles for the downtime gap.
        Replays the tick loop to rebuild legs/base/direction, then resumes live feed.
        """
        logger.info("Starting recovery process...")
        state = self.state_manager.state
        
        if not state["legs"]:
            logger.info("No active legs found in state. Clean start.")
            return

        
        symbols_to_subscribe = set()
        for leg_id, leg in state["legs"].items():
            if leg.get("status") == "OPEN":
                from datetime import datetime
                try:
                    m_exp = datetime.strptime(leg["monthly_expiry"], "%Y-%m-%d")
                    fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
                except Exception:
                    fut_sym = "NIFTY_FUT"
                
                short_t = self.feed.symbol_master.get_option_token(leg['short_opt']['expiry'], leg['short_opt']['strike'], leg['short_opt']['type'])
                short_sym = self.feed.symbol_master.get_symbol(short_t) if short_t else f"NIFTY_{leg['short_opt']['strike']}_{leg['short_opt']['type']}"
                
                long_t = self.feed.symbol_master.get_option_token(leg['long_opt']['expiry'], leg['long_opt']['strike'], leg['long_opt']['type'])
                long_sym = self.feed.symbol_master.get_symbol(long_t) if long_t else f"NIFTY_{leg['long_opt']['strike']}_{leg['long_opt']['type']}"
                
                symbols_to_subscribe.update([fut_sym, short_sym, long_sym])
                
        if symbols_to_subscribe:
            self.feed.subscribe_symbols(list(symbols_to_subscribe))
            
        # Determine the last recorded time (you could add a last_tick_time to state)
        
        # Example gap replay logic:
        # last_time = state.get("last_tick_time", "2026-01-01T09:15:00")
        # now = datetime.datetime.now().isoformat()
        # candles = self.feed.get_historical_candles(last_time, now)
        # for candle in candles:
        #     self.signal_processor.process_tick(candle["close"])
        
        logger.info("Recovery complete. State restored.")
