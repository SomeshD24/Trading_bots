import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

from feed import ChoiceAPIFeed
from symbol_master import SymbolMaster
from option_selector import OptionSelector

def fix_state():
    print("Initializing feed and symbol master...")
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
    
    if not session_id or session_id == "mock_session_token":
        print("Could not login to real API.")
        return
        
    master.fetch_master(os.getenv("CHOICE_BASE_URL"), session_id)
    
    feed.start_websocket()
    time.sleep(2) # Give WS time to connect
    
    selector = OptionSelector(feed)
    
    state_file = 'state_snapshot.json'
    with open(state_file, 'r') as f:
        state = json.load(f)
        
    for leg_id, leg in state.get('legs', {}).items():
        entry_ltp = leg.get('entry_price', 24552.0)
        feed.current_ltp = entry_ltp
        direction = state.get('direction', 'ABOVE')
        
        monthly_exp = state.get('monthly_expiry')
        next_monthly_exp = state.get('next_monthly_expiry')
        weekly_exp = state.get('weekly_expiry')
        
        print(f"Selecting new Short Opt for {monthly_exp} based on > 100 rules...")
        new_short = selector.select_short_opt(entry_ltp, direction, monthly_exp, next_monthly_exp)
        if new_short:
            old_short = leg.get('short_opt', {})
            new_short['order_id'] = old_short.get('order_id', 'short_mock_id')
            new_short['side'] = old_short.get('side', 'SELL')
            print(f"Old Short: {old_short}")
            print(f"New Short: {new_short}")
            leg['short_opt'] = new_short
        else:
            print("Failed to find short opt.")
            
        print(f"Selecting new Long Opt for {weekly_exp} based on 5-15 rules...")
        new_long = selector.select_long_opt(entry_ltp, direction, weekly_exp)
        if new_long:
            old_long = leg.get('long_opt', {})
            new_long['order_id'] = old_long.get('order_id', 'long_mock_id')
            new_long['side'] = old_long.get('side', 'BUY')
            print(f"Old Long: {old_long}")
            print(f"New Long: {new_long}")
            leg['long_opt'] = new_long
        else:
            print("Failed to find long opt.")
            
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
        print("Updated state_snapshot.json")
        
    feed.stop_websocket()

if __name__ == "__main__":
    fix_state()
