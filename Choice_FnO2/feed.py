import time
import random
import threading
import json
import os
import base64
import zlib
import requests
import websocket
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from logger import logger

# Configuration from env
CHOICE_VENDOR_ID = os.getenv("CHOICE_VENDOR_ID")
CHOICE_VENDOR_KEY = os.getenv("CHOICE_VENDOR_KEY")
CHOICE_API_KEY = os.getenv("CHOICE_API_KEY")
CHOICE_MOBILE_NO = os.getenv("CHOICE_MOBILE_NO")
CHOICE_AES_KEY = os.getenv("CHOICE_AES_KEY")
CHOICE_AES_IV = os.getenv("CHOICE_AES_IV")

def parse_crypto_param(s, expected_len):
    if not s:
        return b'\0' * expected_len
    # Try hex
    if len(s) == expected_len * 2:
        try:
            return bytes.fromhex(s)
        except ValueError:
            pass
    # Try plain ascii
    if len(s) == expected_len:
        return s.encode('utf-8')
    # Try base64
    try:
        padded = s + "=" * ((4 - len(s) % 4) % 4)
        decoded = base64.b64decode(padded)
        if len(decoded) == expected_len:
            return decoded
    except Exception:
        pass
    # Fallback: encode and truncate/pad
    return s.encode('utf-8').ljust(expected_len, b'\0')[:expected_len]

def get_encrypted_mobile(mobile_no, key_str, iv_str):
    key = parse_crypto_param(key_str, 32)
    iv = parse_crypto_param(iv_str, 16)
        
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(mobile_no.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')

class ChoiceAPIFeed:
    def __init__(self, symbol_master=None):
        self.symbol_master = symbol_master
        self.callbacks = []
        self.is_running = False
        self.current_ltp = 0.00 # Real price will populate this
        self.thread = None
        
        self.session_id = None
        self.access_token = None
        self.user_code = None
        self.active_symbols = set()
        
        self.ws = None
        self.prices = {} # symbol -> LTP mapping

    def login_with_otp(self, vendor_id, vendor_key, api_key, mobile_no, aes_key, aes_iv):
        """ Fully automates the Choice API OTP Login flow and caches session daily to prevent OTP spam """
        
        # 0. Check cached session
        session_file = "session.json"
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    if data.get("date") == today and data.get("session_id"):
                        logger.info(f"Loaded cached session for today: {today}")
                        self.session_id = data["session_id"]
                        self.access_token = data.get("access_token")
                        self.user_code = data.get("user_code")
                        return self.session_id
            except Exception as e:
                logger.error(f"Failed to load cached session: {e}")
        
        logger.info(f"Starting SSO Flow for Mobile: {mobile_no}")
        if not all([vendor_id, vendor_key, api_key, mobile_no, aes_key, aes_iv]):
            logger.error("Missing required credentials for SSO flow. Falling back to mock session.")
            self.session_id = "MOCK_SESSION"
            self.user_code = "MOCK_USER"
            self.access_token = "MOCK_TOKEN"
            return "mock_session_token"
            
        try:
            enc_mobile = get_encrypted_mobile(mobile_no, aes_key, aes_iv)
            
            headers = {
                "VendorId": vendor_id,
                "VendorKey": vendor_key,
                "Bearer": api_key,
                "Content-Type": "application/json"
            }
            
            # 1. LoginTOTP
            url0 = "https://finx.choiceindia.com/api/OpenAPIV1/LoginTOTP"
            payload0 = {"MobileNo": enc_mobile}
            resp0 = requests.post(url0, headers=headers, json=payload0)
            if resp0.status_code != 200 or resp0.json().get("Status") != "Success":
                logger.error(f"LoginTOTP failed: {resp0.text}")
                return None
                
            # 2. GetClientLoginTOTP
            url1 = "https://finx.choiceindia.com/api/OpenAPIV1/GetClientLoginTOTP"
            payload1 = {"MobileNo": enc_mobile}
            resp1 = requests.post(url1, headers=headers, json=payload1)
            
            if resp1.status_code != 200 or resp1.json().get("Status") != "Success":
                logger.error(f"GetClientLoginTOTP failed: {resp1.text}")
                return None
                
            otp = resp1.json().get("Response")
            logger.info(f"Got OTP successfully from Choice API: {otp}")
            
            # 3. ValidateTOTP
            url2 = "https://finx.choiceindia.com/api/OpenAPIV1/ValidateTOTP"
            payload2 = {"MobileNo": enc_mobile, "OTP": str(otp)}
            
            resp2 = requests.post(url2, headers=headers, json=payload2)
            if resp2.status_code != 200 or resp2.json().get("Status") != "Success":
                logger.error(f"ValidateTOTP failed: {resp2.text}")
                return None
                
            response_data = resp2.json().get("Response", {})
            
            # Extract session id dynamically
            if isinstance(response_data, str):
                self.session_id = response_data
            elif isinstance(response_data, dict):
                for key in ("SessionId", "sessionId", "session_id", "AccessToken", "LogonMessage"):
                    val = response_data.get(key)
                    if val and isinstance(val, str) and val.strip():
                        self.session_id = val.strip()
                        break
            
            if not self.session_id:
                logger.error(f"Could not extract SessionId from ValidateTOTP: {resp2.text}")
                return None
            
            if isinstance(response_data, dict):
                self.user_code = response_data.get("UserCode")
                self.access_token = response_data.get("AccessToken")
            else:
                self.user_code = None
                self.access_token = None
                
            # Cache the new session
            try:
                with open(session_file, "w") as f:
                    json.dump({
                        "date": today,
                        "session_id": self.session_id,
                        "access_token": self.access_token,
                        "user_code": self.user_code
                    }, f)
                logger.info("Session cached successfully for today.")
            except Exception as e:
                logger.error(f"Failed to cache session: {e}")
            
            logger.info(f"SSO Login Successful. SessionId: {self.session_id}")
            return self.session_id
        except Exception as e:
            logger.error(f"Exception during SSO flow: {e}")
            return None

    def subscribe(self, callback):
        self.callbacks.append(callback)

    def start_websocket(self):
        if not self.session_id or not self.access_token:
            logger.warning("Starting websocket without proper authentication tokens. Live data may fail.")
        
        self.is_running = True
        self.thread = threading.Thread(target=self._ws_run, daemon=True)
        self.thread.start()
        logger.info("Websocket feed thread started.")

    def stop_websocket(self):
        self.is_running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Websocket feed stopped.")

    # -------------------------------------------------------------
    # FIX PROTOCOL / WEBSOCKET LOGIC
    # -------------------------------------------------------------
    def _now(self):
        return datetime.now().strftime("%Y-%m-%d %H%M%S")

    def _clean_msg(self, msg: str) -> str:
        while "||" in msg:
            msg = msg.replace("||", "|")
        return msg

    def _fix_message_length(self, msg: str) -> str:
        msg = self._clean_msg(msg)
        parts = msg.split("|")
        parts = [p for p in parts if p and not p.startswith("65=")]
        temp = "|".join(parts) + "|"
        body_length = len(temp)
        parts.insert(2, f"65={body_length}")
        final_msg = "|".join(parts) + "|"
        return self._clean_msg(final_msg)

    def _pack_message(self, msg: str) -> bytes:
        compressed = zlib.compress(msg.encode("ascii"), level=6)
        packet_len = len(compressed)
        header = b"\x05" + f"{packet_len:05d}".encode()
        return header + compressed

    def _unpack_packet(self, data: bytes):
        packets = []
        try:
            idx = 0
            while idx < len(data):
                packet_type = data[idx:idx + 1]
                if packet_type not in [b"\x05", b"\x02"]:
                    break
                packet_len = int(data[idx + 1:idx + 6].decode())
                body_start = idx + 6
                body_end = body_start + packet_len
                body = data[body_start:body_end]

                if packet_type == b"\x05":
                    decompressed = zlib.decompress(body)
                    text = decompressed.decode("ascii", errors="ignore")
                else:
                    text = body.decode("ascii", errors="ignore")

                text = text.replace("\x00", "")
                for p in text.split("\x02"):
                    p = p.strip()
                    if p:
                        packets.append(p)
                idx = body_end
        except Exception as e:
            logger.error(f"UNPACK ERROR: {e}")
        return packets

    def _parse_fix(self, msg: str):
        parsed = {}
        for item in msg.split("|"):
            if "=" in item:
                k, v = item.split("=", 1)
                parsed[k] = v
        return parsed

    def _login_request(self):
        msg = (
            f"63=FIX3.0|"
            f"64=101|"
            f"66={self._now()}|"
            f"67={self.user_code}|"
            f"68={self.access_token}|"
        )
        return self._fix_message_length(msg)

    def _touchline_request(self, tokens=None):
        token_block = ""
        
        if not tokens:
            # Default to Nifty Future
            target_token = self.symbol_master.get_token("NIFTY_FUT") if self.symbol_master else None
            if target_token:
                token_block += f"1=2$7={target_token}|"
        else:
            # 1=2 for FO
            for sym, t in tokens.items():
                if sym != "NIFTY_SPOT":
                    token_block += f"1=2$7={t}|"

        msg = (
            f"63=FIX3.0|"
            f"64=206|"
            f"66={self._now()}|"
            f"{token_block}"
            f"230=1|"
            f"4={self.session_id}|"
        )
        return self._fix_message_length(msg)

    def subscribe_symbols(self, symbols):
        """ Dynamically subscribe to new symbols during runtime """
        new_symbols = set(symbols) - self.active_symbols if symbols else self.active_symbols
        self.active_symbols.update(symbols)
        
        if not self.ws or not self.session_id:
            return

        tokens = {}
        for sym in new_symbols:
            if self.symbol_master:
                t = self.symbol_master.get_token(sym)
                if t:
                    tokens[sym] = t
        
        if tokens:
            logger.info(f"Subscribed to active symbols: {list(tokens.keys())}")
            # Chunk the requests to prevent payload size limits (e.g., 20 tokens per request)
            token_items = list(tokens.items())
            chunk_size = 20
            for i in range(0, len(token_items), chunk_size):
                chunk = dict(token_items[i:i+chunk_size])
                sub_msg = self._touchline_request(chunk)
                self.ws.send(self._pack_message(sub_msg), opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(0.1) # Small delay to prevent flooding


    def _on_open(self, ws):
        logger.info("WEBSOCKET CONNECTED to Choice Datafeed.")
        if self.user_code and self.access_token:
            login_msg = self._login_request()
            ws.send(self._pack_message(login_msg), opcode=websocket.ABNF.OPCODE_BINARY)
        else:
            logger.warning("No auth tokens to send FIX login. Waiting for reconnection.")

    def _on_message(self, ws, message):
        try:
            if isinstance(message, str):
                message = message.encode()

            packets = self._unpack_packet(message)
            for packet in packets:
                parsed = self._parse_fix(packet)
                msg_code = parsed.get("64")

                if msg_code == "102":
                    if parsed.get("70") == "10000":
                        logger.info("FIX LOGIN SUCCESS")
                        # Trigger subscription for all tracked symbols upon successful connection
                        self.subscribe_symbols([])
                    else:
                        logger.error(f"FIX LOGIN FAILED => {parsed}")

                elif msg_code == "209": # Touchline data
                    ltp = parsed.get("8")
                    token = parsed.get("7")
                    
                    if ltp and token:
                        try:
                            price_float = float(ltp)
                            # Choice API returns all prices with implied 2 decimal places (or based on PriceDivisor)
                            # We should universally divide by 100.0 to get the Rupee value
                            price_float /= 100.0
                            
                            price = round(price_float, 2)
                            
                            # Map token back to symbol if we have master
                            symbol = self.symbol_master.get_symbol(token) if self.symbol_master else None
                            if symbol:
                                self.prices[symbol] = price
                                
                            # Use actual Nifty Futures for the main ladder signal
                            if symbol and "FUT" in symbol:
                                self.current_ltp = price
                                for cb in self.callbacks:
                                    cb(self.current_ltp)
                                    
                                # We no longer populate mock prices. The OptionSelector will subscribe to the necessary symbols
                                # and wait for them to stream naturally through the websocket.
                        except ValueError:
                            pass
        except Exception as e:
            import traceback
            logger.error(f"Error in _on_message: {e}\n{traceback.format_exc()}")
                        
    def _on_error(self, ws, error):
        logger.error(f"WEBSOCKET ERROR => {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WEBSOCKET CLOSED => Code={close_status_code} | Msg={close_msg}")

    def _ws_run(self):
        websocket.enableTrace(False)
        url = "wss://brd.choiceindia.co.in:4520"
        
        while self.is_running:
            if not self.access_token or not self.session_id:
                logger.error("No valid tokens. Waiting for proper authentication...")
                time.sleep(5)
                continue

            try:
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"WebSocket Loop Error: {e}")
            
            if self.is_running:
                logger.warning("Reconnecting websocket in 3 seconds...")
                time.sleep(3)

    # -------------------------------------------------------------
    # REST API LIVE PRICES (MULTIPLE TOUCHLINE)
    # -------------------------------------------------------------
    def get_multiple_touchline(self, symbols):
        """ Fetches live prices for multiple symbols instantly via REST API. Returns dict {symbol: premium} """
        if not self.session_id:
            return {}
            
        tokens = []
        for sym in symbols:
            t = self.symbol_master.get_token(sym)
            if t:
                # Choice API expects SegmentId@Token. Segment 2 is NSE Derivatives.
                tokens.append(f"2@{t}")
                
        if not tokens:
            return {}
            
        url = "https://finx.choiceindia.com/api/OpenAPI/MultipleTouchline"
        headers = {
            "VendorId": os.getenv("CHOICE_VENDOR_ID", ""),
            "VendorKey": os.getenv("CHOICE_VENDOR_KEY", ""),
            "Authorization": f"Bearer {self.session_id}",
            "Content-Type": "application/json"
        }
        
        # Max 50 symbols per request, chunk if necessary
        result_prices = {}
        
        chunk_size = 50
        for i in range(0, len(tokens), chunk_size):
            chunk = tokens[i:i+chunk_size]
            payload = {"MultipleSegToken": ",".join(chunk)}
            
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("Status") == "Success":
                        items = data.get("Response", {}).get("MultipleTouchline", [])
                        for item in items:
                            token_val = str(item.get("Token"))
                            price = float(item.get("LTP", 0.0))
                            sym = self.symbol_master.get_symbol(token_val)
                            if sym and price > 0:
                                result_prices[sym] = price
            except Exception as e:
                logger.error(f"MultipleTouchline REST API Error: {e}")
                
        return result_prices
