import schedule
import time
import threading
import datetime
from logger import logger

from expiry_calc import is_holiday_or_weekend

class BotScheduler:
    def __init__(self, bot, rollover_manager, feed):
        self.bot = bot
        self.rollover_manager = rollover_manager
        self.feed = feed
        self.is_running = False
        self.thread = None

    def _run_scheduler(self):
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        self.is_running = True
        
        # Check every day at 10:00 AM for Weekly Rollover
        schedule.every().day.at("10:00").do(self.check_and_trigger_weekly_rollover)
        
        # Check every day at 15:00 (3:00 PM) for Monthly Rollover
        schedule.every().day.at("15:00").do(self.check_and_trigger_monthly_rollover)
        
        # Auto Start/Stop (Market hours)
        schedule.every().day.at("09:15").do(self.trigger_market_open)
        schedule.every().day.at("15:40").do(self.trigger_market_close)
        
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Scheduler stopped.")

    def check_and_trigger_weekly_rollover(self):
        from expiry_calc import get_weekly_expiry, get_previous_business_day
        import datetime
        
        current_held_expiry_str = self.bot.state_manager.state.get("weekly_expiry")
        if not current_held_expiry_str:
            return
            
        current_held_expiry = datetime.datetime.strptime(current_held_expiry_str, "%Y-%m-%d").date()
        target_roll_day = get_previous_business_day(current_held_expiry)
        
        if datetime.date.today() == target_roll_day:
            logger.info("Today is the Weekly Rollover day. Triggering...")
            # We must get the NEXT weekly expiry to roll into.
            # Passing current_held_expiry + 1 day guarantees we jump to the subsequent expiry.
            next_base_date = current_held_expiry + datetime.timedelta(days=1)
            self.bot.state_manager.state["weekly_expiry"] = get_weekly_expiry(next_base_date).isoformat()
            self.bot.state_manager.save()
            self.rollover_manager.perform_weekly_rollover(self.feed.current_ltp)
        else:
            logger.info(f"Skipping weekly rollover. Scheduled for: {target_roll_day}")

    def check_and_trigger_monthly_rollover(self):
        from expiry_calc import get_current_and_next_monthly_expiries
        import datetime
        current_exp, next_exp = get_current_and_next_monthly_expiries()
        
        # Monthly rollover occurs ON the day of the monthly expiry at 3:00 PM (or as required)
        # If expiry shifts to Monday due to holiday, current_exp will automatically be Monday.
        if datetime.date.today() == current_exp:
            logger.info("Today is the Monthly Expiry/Rollover day. Triggering...")
            self.bot.state_manager.state["next_monthly_expiry"] = next_exp.isoformat()
            self.bot.state_manager.save()
            self.rollover_manager.perform_monthly_rollover(self.feed.current_ltp)
        else:
            logger.info(f"Skipping monthly rollover. Scheduled for: {current_exp}")

    def trigger_market_open(self):
        if not is_holiday_or_weekend(datetime.date.today()):
            logger.info("Market Open: Auto-starting bot...")
            self.bot.start()
        else:
            logger.info("Market Open skipped (Weekend/Holiday).")

    def trigger_market_close(self):
        if not is_holiday_or_weekend(datetime.date.today()):
            logger.info("Market Close: Auto-stopping bot...")
            self.bot.stop()
        else:
            logger.info("Market Close skipped (Weekend/Holiday).")
