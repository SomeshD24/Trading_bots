import schedule
import time
import threading
import datetime
from logger import logger

from expiry_calc import is_holiday_or_weekend, get_ist_today, get_ist_now

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
        
        # Check every day at 10:00 AM IST for Weekly Rollover
        schedule.every().day.at("10:00", "Asia/Kolkata").do(self.check_and_trigger_weekly_rollover)
        
        # Check every day at 15:00 (3:00 PM IST) for Monthly Rollover
        schedule.every().day.at("15:00", "Asia/Kolkata").do(self.check_and_trigger_monthly_rollover)
        
        # Auto Start/Stop (Market hours IST)
        schedule.every().day.at("09:15", "Asia/Kolkata").do(self.trigger_market_open)
        schedule.every().day.at("15:40", "Asia/Kolkata").do(self.trigger_market_close)
        
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started with Asia/Kolkata (IST) timezone.")
        
        # Catch up check: if starting past 15:00 IST on monthly expiry day, check if rollover was missed
        self._check_missed_monthly_rollover()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Scheduler stopped.")

    def _get_effective_ltp(self):
        """Returns the best available LTP from websocket, REST touchline, or saved state."""
        ltp = self.feed.current_ltp
        if not ltp or ltp <= 0:
            ltp = self.bot.state_manager.state.get("last_ltp", 0.0)
            try:
                m_exp_str = self.bot.state_manager.state.get("monthly_expiry")
                if m_exp_str:
                    m_exp = datetime.datetime.strptime(m_exp_str, "%Y-%m-%d")
                    fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
                    rest_p = self.feed.get_multiple_touchline([fut_sym])
                    if fut_sym in rest_p and rest_p[fut_sym] > 0:
                        ltp = rest_p[fut_sym]
            except Exception:
                pass
        return ltp

    def _check_missed_monthly_rollover(self):
        from expiry_calc import get_current_and_next_monthly_expiries
        try:
            current_exp, _ = get_current_and_next_monthly_expiries()
            today_ist = get_ist_today()
            now_ist = get_ist_now()
            
            # If today is monthly expiry day and current IST time is past 15:00
            if today_ist == current_exp and now_ist.hour >= 15:
                state_expiry = self.bot.state_manager.state.get("monthly_expiry")
                # If state still points to today's expiring month, rollover hasn't run yet!
                if state_expiry == current_exp.isoformat():
                    logger.info("Missed monthly rollover detected on startup past 15:00 IST. Triggering now...")
                    self.check_and_trigger_monthly_rollover()
        except Exception as e:
            logger.error(f"Error during missed monthly rollover check: {e}")

    def check_and_trigger_weekly_rollover(self):
        from expiry_calc import get_weekly_expiry, get_previous_business_day
        import datetime
        
        current_held_expiry_str = self.bot.state_manager.state.get("weekly_expiry")
        if not current_held_expiry_str:
            return
            
        current_held_expiry = datetime.datetime.strptime(current_held_expiry_str, "%Y-%m-%d").date()
        target_roll_day = get_previous_business_day(current_held_expiry)
        
        if get_ist_today() == target_roll_day:
            logger.info("Today is the Weekly Rollover day. Triggering...")
            next_base_date = current_held_expiry + datetime.timedelta(days=1)
            self.bot.state_manager.state["weekly_expiry"] = get_weekly_expiry(next_base_date).isoformat()
            self.bot.state_manager.save()
            
            ltp = self._get_effective_ltp()
            self.rollover_manager.perform_weekly_rollover(ltp)
        else:
            logger.info(f"Skipping weekly rollover. Scheduled for: {target_roll_day}")

    def check_and_trigger_monthly_rollover(self):
        from expiry_calc import get_current_and_next_monthly_expiries
        import datetime
        current_exp, next_exp = get_current_and_next_monthly_expiries()
        
        if get_ist_today() == current_exp:
            logger.info("Today is the Monthly Expiry/Rollover day. Triggering...")
            self.bot.state_manager.state["next_monthly_expiry"] = next_exp.isoformat()
            self.bot.state_manager.save()
            
            ltp = self._get_effective_ltp()
            self.rollover_manager.perform_monthly_rollover(ltp)
        else:
            logger.info(f"Skipping monthly rollover. Scheduled for: {current_exp}")

    def trigger_market_open(self):
        if not is_holiday_or_weekend(get_ist_today()):
            logger.info("Market Open: Auto-starting bot...")
            self.bot.start()
        else:
            logger.info("Market Open skipped (Weekend/Holiday).")

    def trigger_market_close(self):
        if not is_holiday_or_weekend(get_ist_today()):
            logger.info("Market Close: Auto-stopping bot...")
            self.bot.stop()
        else:
            logger.info("Market Close skipped (Weekend/Holiday).")
