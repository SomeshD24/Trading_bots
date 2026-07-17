import json
import time
import os
from dotenv import load_dotenv
load_dotenv()

from feed import ChoiceAPIFeed
from symbol_master import SymbolMaster
from option_selector import OptionSelector

print('Initializing feed and symbol master...')
master = SymbolMaster()
feed = ChoiceAPIFeed(master)
session_id = feed.login_with_otp(
    os.getenv('CHOICE_VENDOR_ID'),
    os.getenv('CHOICE_VENDOR_KEY'),
    os.getenv('CHOICE_API_KEY'),
    os.getenv('CHOICE_MOBILE_NO'),
    os.getenv('CHOICE_AES_KEY'),
    os.getenv('CHOICE_AES_IV')
)

master.fetch_master(os.getenv('CHOICE_BASE_URL'), session_id)
feed.start_websocket()
time.sleep(2)

selector = OptionSelector(feed)

state_file = 'state_snapshot.json'
with open(state_file, 'r') as f:
    state = json.load(f)

for leg_id, leg in state.get('legs', {}).items():
    if leg_id != 'L21_20260714':
        continue
    print(f'Fixing {leg_id}')
    entry_ltp = leg.get('entry_price')
    feed.current_ltp = entry_ltp
    direction = state.get('direction', 'ABOVE')
    
    monthly_exp = state.get('monthly_expiry')
    next_monthly_exp = state.get('next_monthly_expiry')
    
    new_short = selector.select_short_opt(entry_ltp, direction, monthly_exp, next_monthly_exp)
    if new_short:
        old_short = leg.get('short_opt', {})
        new_short['order_id'] = old_short.get('order_id', 'short_mock_id')
        new_short['side'] = old_short.get('side', 'SELL')
        leg['short_opt'] = new_short
        print(f'New short: {new_short}')

with open(state_file, 'w') as f:
    json.dump(state, f, indent=4)

feed.stop_websocket()
