import os
import json
import time
import sys
from dotenv import load_dotenv
load_dotenv()

from feed import ChoiceAPIFeed
from symbol_master import SymbolMaster
from option_selector import OptionSelector

def fix_state(custom_strike=None, custom_premium=None):
    state_file = 'state_snapshot.json'
    if not os.path.exists(state_file):
        print(f"State file {state_file} not found.")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    master = SymbolMaster()
    feed = ChoiceAPIFeed(master)
    
    session_id = feed.login_with_otp(
        os.getenv("CHOICE_VENDOR_ID"),
        os.getenv("CHOICE_VENDOR_KEY"),
        os.getenv("CHOICE_API_KEY"),
        os.getenv("CHOICE_MOBILE_NO"),
        os.getenv("CHOICE_AES_KEY"),
        os.getenv("CHOICE_AES_IV")
    )
    
    if session_id and session_id != "mock_session_token":
        print("Logged in to Choice API. Fetching scrip master...")
        master.fetch_master(os.getenv("CHOICE_BASE_URL"), session_id)
        selector = OptionSelector(feed)
        
        for leg_id, leg in state.get('legs', {}).items():
            if leg.get('status') != 'OPEN':
                continue
            entry_ltp = leg.get('entry_price', 24314.3)
            feed.current_ltp = entry_ltp
            direction = state.get('direction', 'BELOW')
            monthly_exp = state.get('monthly_expiry')
            next_monthly_exp = state.get('next_monthly_expiry')
            
            print(f"Selecting new Short Opt for {leg_id} (LTP: {entry_ltp}, Dir: {direction})...")
            new_short = selector.select_short_opt(entry_ltp, direction, monthly_exp, next_monthly_exp)
            if new_short:
                old_short = leg.get('short_opt', {})
                new_short['order_id'] = old_short.get('order_id', 'short_mock_id')
                new_short['side'] = old_short.get('side', 'SELL')
                print(f"Old Short: {old_short}")
                print(f"New Short: {new_short}")
                leg['short_opt'] = new_short
            else:
                print(f"Failed to find short opt via API for {leg_id}")
    else:
        print("API session offline/mock. Updating active legs based on ATM ± 6 to ATM ± 30 >100 rule...")
        direction = state.get('direction', 'BELOW')
        step = -50 if direction == "ABOVE" else 50
        opt_type = "PE" if direction == "ABOVE" else "CE"
        monthly_exp = state.get('monthly_expiry', '2026-08-25')

        for leg_id, leg in state.get('legs', {}).items():
            if leg.get('status') != 'OPEN':
                continue
            entry_ltp = leg.get('entry_price', 24314.3)
            atm = int(round(entry_ltp / 50.0) * 50)
            
            target_strike = int(custom_strike) if custom_strike else (atm + (6 * step))
            target_premium = float(custom_premium) if custom_premium else 150.0

            old_short = leg.get('short_opt', {})
            leg['short_opt'] = {
                'strike': target_strike,
                'type': opt_type,
                'expiry': monthly_exp,
                'premium': target_premium,
                'order_id': old_short.get('order_id', 'mock_id'),
                'side': 'SELL'
            }
            leg['hist_short_pnl'] = 0.0
            leg['realized_pnl'] = leg.get('hist_fut_pnl', 0.0) + leg.get('hist_long_pnl', 0.0)
            print(f"Updated {leg_id}: Short Opt set to {target_strike} {opt_type} @ {target_premium}")

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
        print("Successfully updated state_snapshot.json!")

if __name__ == "__main__":
    strike_arg = sys.argv[1] if len(sys.argv) > 1 else None
    prem_arg = sys.argv[2] if len(sys.argv) > 2 else None
    fix_state(custom_strike=strike_arg, custom_premium=prem_arg)
