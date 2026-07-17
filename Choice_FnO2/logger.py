import logging
import csv
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Basic app logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Bot")

def log_trade(action, symbol, qty, price, order_type="MARKET"):
    filename = os.path.join(LOG_DIR, "trade_log.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "action", "symbol", "qty", "price", "order_type"])
        writer.writerow([datetime.now().isoformat(), action, symbol, qty, price, order_type])

def log_order(order_id, symbol, side, qty, status, price=None):
    filename = os.path.join(LOG_DIR, "order_log.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "order_id", "symbol", "side", "qty", "status", "price"])
        writer.writerow([datetime.now().isoformat(), order_id, symbol, side, qty, status, price])

def log_rollover(old_entry, new_entry, old_strike, new_strike, old_sym, new_sym, target_expiry):
    filename = os.path.join(LOG_DIR, "rollover_log.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "old_entry", "new_entry", "old_strike", "new_strike", "old_sym", "new_sym", "target_expiry"])
        writer.writerow([datetime.now().isoformat(), old_entry, new_entry, old_strike, new_strike, old_sym, new_sym, target_expiry])

def log_leg(leg_id, leg, pnl=0.0):
    filename = os.path.join(LOG_DIR, "leg_log.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "leg_id", "status", "entry_time", 
                "future_side", "future_entry", "future_exit",
                "short_strike", "short_type", "short_entry_premium", "short_exit_premium",
                "long_strike", "long_type", "long_entry_premium", "long_exit_premium",
                "fut_pnl", "short_pnl", "long_pnl",
                "realized_pnl"
            ])
        writer.writerow([
            datetime.now().isoformat(), 
            leg_id, 
            leg.get("status"), 
            leg.get("entry_time"),
            leg.get("future_side"), 
            leg.get("entry_price"),
            leg.get("future_exit", "N/A"),
            leg.get("short_opt", {}).get("strike"), 
            leg.get("short_opt", {}).get("type"), 
            leg.get("short_opt", {}).get("premium"),
            leg.get("short_exit", "N/A"),
            leg.get("long_opt", {}).get("strike"), 
            leg.get("long_opt", {}).get("type"), 
            leg.get("long_opt", {}).get("premium"),
            leg.get("long_exit", "N/A"),
            round(leg.get("fut_pnl", 0.0), 2),
            round(leg.get("short_pnl", 0.0), 2),
            round(leg.get("long_pnl", 0.0), 2),
            round(pnl, 2)
        ])
