import math
import time
from logger import logger

def round_nearest(value, base):
    return int(base * round(float(value)/base))

class OptionSelector:
    def __init__(self, feed):
        # feed is an instance of the market data feed, used to query premiums
        self.feed = feed
        self.strike_step = 50

    def get_atm_strike(self, future_ltp):
        return round_nearest(future_ltp, self.strike_step)

    def _evaluate_short_opt_rest(self, target_strikes, opt_type, expiry):
        """
        Uses REST API to evaluate short options instantly without WebSocket polling.
        Returns (strike, premium) or (None, None).
        """
        if not getattr(self.feed, 'symbol_master', None):
            return None, None
            
        symbols = []
        strike_to_symbol = {}
        for strike in target_strikes:
            token = self.feed.symbol_master.get_option_token(expiry, strike, opt_type)
            if token:
                sym = self.feed.symbol_master.get_symbol(token)
                if sym and sym != "UNKNOWN_SYMBOL":
                    symbols.append(sym)
                    strike_to_symbol[strike] = sym
                    
        if not symbols:
            return None, None
            
        prices = self.feed.get_multiple_touchline(symbols)
        for strike in target_strikes:
            sym = strike_to_symbol.get(strike)
            if sym and sym in prices:
                premium = prices[sym]
                if premium > 100:
                    return strike, premium
                    
        return None, None

    def _prefilter_and_wait_long_opt(self, target_strikes, opt_type, expiry, max_wait_sec=5):
        """
        1. Uses REST API to find up to 5 strikes in the 5-15 premium band.
        2. Subscribes ONLY those 5 strikes to the live WebSocket.
        3. Waits for one of them to hit the 8-12 premium band.
        """
        if not getattr(self.feed, 'symbol_master', None):
            return None, None
            
        symbols = []
        strike_to_symbol = {}
        for strike in target_strikes:
            token = self.feed.symbol_master.get_option_token(expiry, strike, opt_type)
            if token:
                sym = self.feed.symbol_master.get_symbol(token)
                if sym and sym != "UNKNOWN_SYMBOL":
                    symbols.append(sym)
                    strike_to_symbol[strike] = sym
                    
        if not symbols:
            return None, None
            
        # 1. Pre-filter using REST API
        rest_prices = self.feed.get_multiple_touchline(symbols)
        filtered_strikes = []
        for strike in target_strikes:
            sym = strike_to_symbol.get(strike)
            if sym and sym in rest_prices:
                premium = rest_prices[sym]
                if 5 <= premium <= 15:
                    filtered_strikes.append(strike)
                if len(filtered_strikes) >= 5:
                    break
                    
        if not filtered_strikes:
            logger.warning("No strikes found in the 5-15 range via REST pre-filtering.")
            return None, None
            
        # 2. Subscribe the filtered range of strikes
        symbols_to_subscribe = [strike_to_symbol[s] for s in filtered_strikes]
        logger.info(f"REST pre-filtered to 5-15 band. Subscribing to {len(symbols_to_subscribe)} options for final 8-12 evaluation: {symbols_to_subscribe}")
        self.feed.subscribe_symbols(symbols_to_subscribe)
        
        # 3. Instantly check if REST prices already hit the 8-12 band to avoid waiting for WebSocket
        for strike in filtered_strikes:
            sym = strike_to_symbol.get(strike)
            if sym and sym in rest_prices:
                premium = rest_prices[sym]
                if 8 <= premium <= 12:
                    logger.info(f"Instantly selected {sym} from REST prices in 8-12 band (premium: {premium}).")
                    return strike, premium
        
        # 4. If none were strictly 8-12, wait and poll for the 8-12 band from WebSocket
        start_time = time.time()
        while time.time() - start_time < max_wait_sec:
            for strike in filtered_strikes:
                sym = strike_to_symbol.get(strike)
                if sym and sym in self.feed.prices:
                    premium = self.feed.prices[sym]
                    if 8 <= premium <= 12:
                        return strike, premium
            time.sleep(0.5)
            
        logger.warning(f"Timeout waiting for option prices or no strike met the 8-12 criteria from the filtered list.")
        return None, None

    def select_short_opt(self, future_ltp, direction, current_monthly_expiry, next_monthly_expiry):
        """
        short_opt: Strike = ATM ± 6 strikes (300pts OTM, put if ABOVE / call if BELOW).
        Start from ATM towards ATM ± 6 taking first one with premium > 100.
        If not found, go to next month and repeat.
        """
        atm = self.get_atm_strike(future_ltp)
        opt_type = "PE" if direction == "ABOVE" else "CE"
        step = -50 if direction == "ABOVE" else 50
        
        # Check from furthest OTM (ATM ± 30) down to base (ATM ± 6)
        # The first one with premium > 100 will naturally be the furthest OTM option > 100.
        # If none are > 100 (meaning even ATM ± 6 is < 100), it returns None and falls back to next month.
        target_strikes = [atm + (i * step) for i in range(30, 5, -1)]

        strike, premium = self._evaluate_short_opt_rest(target_strikes, opt_type, current_monthly_expiry)
        if strike is not None:
            return {
                "strike": strike,
                "type": opt_type,
                "expiry": current_monthly_expiry,
                "premium": premium
            }

        # Else, next month, same strikes
        strike, premium = self._evaluate_short_opt_rest(target_strikes, opt_type, next_monthly_expiry)
        if strike is not None:
            return {
                "strike": strike,
                "type": opt_type,
                "expiry": next_monthly_expiry,
                "premium": premium
            }
                
        return None

    def select_long_opt(self, future_ltp, direction, weekly_expiry):
        """
        long_opt: weekly expiry, premium band 8-12, closest strike to ATM first, expand outward.
        """
        atm = self.get_atm_strike(future_ltp)
        opt_type = "CE" if direction == "ABOVE" else "PE"
        
        # Pre-generate outward strikes from ATM
        outward_strikes = []
        offset = 0
        for _ in range(40): # covers 2000 points
            s = atm + offset if direction == "ABOVE" else atm - offset
            outward_strikes.append(s)
            offset += 50
            
        strike, premium = self._prefilter_and_wait_long_opt(outward_strikes, opt_type, weekly_expiry, max_wait_sec=5)
        
        if strike is not None:
            return {
                "strike": strike,
                "type": opt_type,
                "expiry": weekly_expiry,
                "premium": premium
            }
                
        return None
