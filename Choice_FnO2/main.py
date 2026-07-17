import os
import threading
import time
from dotenv import load_dotenv

from state import BotState
from feed import ChoiceAPIFeed
from orders import OrderManager
from option_selector import OptionSelector
from signals import SignalProcessor
from rollover import RolloverManager
from recovery import RecoveryManager
from scheduler import BotScheduler
from expiry_calc import get_weekly_expiry, get_current_and_next_monthly_expiries
from symbol_master import SymbolMaster
from logger import logger

# Load env variables
load_dotenv(dotenv_path=".env")

class LadderBot:
    def __init__(self):
        self.state_manager = BotState()
        self.symbol_master = SymbolMaster()
        self.feed = ChoiceAPIFeed(self.symbol_master)
        self.order_manager = OrderManager(self.symbol_master, paper_trade=True)
        self.option_selector = OptionSelector(self.feed)
        self.signal_processor = SignalProcessor(self.state_manager, self.option_selector, self.order_manager, self.feed)
        self.rollover_manager = RolloverManager(self.state_manager, self.option_selector, self.order_manager)
        self.recovery_manager = RecoveryManager(self.state_manager, self.feed, self.signal_processor)
        self.scheduler = BotScheduler(self, self.rollover_manager, self.feed)
        
        self.is_running = False
        
        # Start the scheduler immediately in the background to listen for auto-start/stop
        self.scheduler.start()

    def initialize_expiries(self):
        # Set expiries if not set
        if not self.state_manager.state["weekly_expiry"]:
            self.state_manager.state["weekly_expiry"] = get_weekly_expiry().isoformat()
        if not self.state_manager.state["monthly_expiry"]:
            current, next_exp = get_current_and_next_monthly_expiries()
            self.state_manager.state["monthly_expiry"] = current.isoformat()
            self.state_manager.state["next_monthly_expiry"] = next_exp.isoformat()
        self.state_manager.save()

    def tick_handler(self, ltp):
        try:
            # Update last tick in state (optional, for recovery)
            self.state_manager.state["last_ltp"] = ltp
            self.signal_processor.process_tick(ltp)
        except Exception as e:
            import traceback
            logger.error(f"Error in tick_handler: {e}\n{traceback.format_exc()}")

    def start(self):
        if self.is_running:
            logger.warning("Bot is already running.")
            return

        logger.info("Starting Nifty Ladder Bot...")
        
        # 1. Initialize Expiries
        self.initialize_expiries()
        
        # 2. Connect Feed and Fetch Master
        # Authenticate first
        session_id = self.feed.login_with_otp(
            os.getenv("CHOICE_VENDOR_ID"),
            os.getenv("CHOICE_VENDOR_KEY"),
            os.getenv("CHOICE_API_KEY"),
            os.getenv("CHOICE_MOBILE_NO"),
            os.getenv("CHOICE_AES_KEY"),
            os.getenv("CHOICE_AES_IV")
        )
        
        # Fetch daily scrip master
        self.symbol_master.fetch_master(os.getenv("CHOICE_BASE_URL"), session_id)

        # 3. Recovery (runs after master is loaded so option tokens resolve correctly)
        self.recovery_manager.recover()
        
        # Ensure we always subscribe to the active month's Future contract
        from datetime import datetime
        try:
            m_exp = datetime.strptime(self.state_manager.state["monthly_expiry"], "%Y-%m-%d")
            fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
            self.feed.active_symbols.add(fut_sym)
            logger.info(f"Registered baseline futures symbol: {fut_sym}")
        except Exception as e:
            logger.error(f"Could not register futures symbol: {e}")
        
        # Subscribe and start feed
        self.feed.subscribe(self.tick_handler)
        self.feed.start_websocket()
        
        self.is_running = True
        logger.info("Bot successfully started.")

    def stop(self):
        if not self.is_running:
            logger.warning("Bot is not running.")
            return

        logger.info("Stopping Nifty Ladder Bot...")
        self.feed.stop_websocket()
        self.is_running = False
        logger.info("Bot successfully stopped.")

# Global instance for Streamlit access
bot_instance = LadderBot()

if __name__ == "__main__":
    bot = LadderBot()
    try:
        bot.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
