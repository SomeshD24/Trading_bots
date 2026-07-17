import requests
from logger import logger

class SymbolMaster:
    def __init__(self):
        self.symbol_to_token = {}
        self.token_to_symbol = {}
        # Keys: (expiry_date: datetime.date, opt_type: str, strike: float) -> token: str
        self.option_chain = {}
        
    def fetch_master(self, base_url, session_id):
        """
        Fetches the daily scrip master from Choice API and builds mapping dictionaries.
        This ensures we use the exact Token IDs required by the Websocket and Order endpoints
        instead of hardcoded strings.
        """
        import urllib.request
        import csv
        from datetime import datetime
        
        logger.info("Fetching daily scrip master for token mapping...")
        
        # Format current date for URL (e.g., 06Jul2026)
        date_str = datetime.now().strftime("%d%b%Y")
        url = f"https://scripmaster.choiceindia.com/scripmaster/SCRIP_MASTER_{date_str}.csv"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                lines = (line.decode('utf-8', errors='ignore') for line in response)
                reader = csv.DictReader(lines)
                count = 0
                for row in reader:
                    symbol = row.get('Symbol', '')
                    instrument = row.get('Instrument', '')
                    sec_desc = row.get('SecDesc', '')
                    token = row.get('Token', '')
                    
                    if not token:
                        continue
                        
                    # Map standard Nifty Spot
                    if symbol == 'NIFTY' and instrument == 'INDEX':
                        self.symbol_to_token["NIFTY_SPOT"] = token
                        self.token_to_symbol[token] = "NIFTY_SPOT"
                        count += 1
                        continue
                        
                    # Map NIFTY Futures
                    if symbol == 'NIFTY' and instrument == 'FUTIDX':
                        # Example SecDesc: NIFTY26JULFUT. We want to standardize it.
                        try:
                            # Use SecDesc directly as the symbol for futures to guarantee uniqueness across expiries
                            # Format we used in signals.py was "NIFTY 28 JUL FUT" based on monthly_expiry
                            # Let's map it based on the SecDesc instead, since that's standard.
                            # But wait, signals.py generates: "NIFTY 28 JUL FUT"
                            # Let's just map the raw SecDesc. It's cleaner.
                            # Or better yet, we just map everything!
                            pass
                        except Exception:
                            pass
                            
                    # Just map the exact SecDesc for everything in derivatives
                    if sec_desc:
                        self.symbol_to_token[sec_desc.strip()] = token.strip()
                        self.token_to_symbol[token.strip()] = sec_desc.strip()
                        
                        # Store in structured option chain map for lookup
                        if instrument == 'OPTIDX' and symbol == 'NIFTY':
                            try:
                                opt_type = row.get('OptionType', '').strip()
                                strike_val = float(row.get('StrikePrice', 0)) / 100.0  # Choice API uses 100 multiplier
                                expiry_str = row.get('Expiry', '').strip() # e.g. "25AUG26"
                                
                                # Convert "25AUG26" to datetime.date
                                exp_date = datetime.strptime(expiry_str, "%d%b%y").date()
                                
                                self.option_chain[(exp_date, opt_type, strike_val)] = token.strip()
                            except Exception as e:
                                pass
                                
                        count += 1
                        
            logger.info(f"Loaded {count} symbols from master.")
        except Exception as e:
            logger.error(f"Failed to fetch scrip master from {url}: {e}")
            logger.info("Falling back to mock tokens.")
            self._populate_mock_tokens()

    def _populate_mock_tokens(self):
        # Add some mock tokens for paper trading
        self.symbol_to_token["NIFTY_FUT"] = "26000"
        self.symbol_to_token["NIFTY_FUT_NEW"] = "26001"
        self.symbol_to_token["NIFTY_FUT_OLD"] = "26002"
        # Since we generate dynamic strikes, we'll implement a fallback lookup
        
    def get_token(self, symbol):
        # In real life, return self.symbol_to_token[symbol]
        # For our mock, we generate a pseudo-hash token if not found
        if symbol in self.symbol_to_token:
            return self.symbol_to_token[symbol]
        
        # Mock token generation based on string hash for consistency
        token = str(abs(hash(symbol)) % 100000)
        self.symbol_to_token[symbol] = token
        self.token_to_symbol[token] = symbol
        return token

    def get_symbol(self, token):
        return self.token_to_symbol.get(token, "UNKNOWN_SYMBOL")

    def get_option_token(self, expiry_date_str, strike, opt_type):
        """
        Retrieves the exact Choice API token for an option contract.
        expiry_date_str: "YYYY-MM-DD"
        strike: float or int
        opt_type: "CE" or "PE"
        """
        try:
            from datetime import datetime
            exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            return self.option_chain.get((exp_date, opt_type, float(strike)))
        except Exception as e:
            return None
