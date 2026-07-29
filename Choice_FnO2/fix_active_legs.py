import json
import os

def fix_active_legs(state_file='state_snapshot.json'):
    """
    Restores the exact active legs state, closed legs history, and realized PnL.
    """
    # Load initial state to preserve all 24 closed_legs and account realized_pnl
    initial_file = 'state_snapshot.initial.json'
    if os.path.exists(initial_file):
        with open(initial_file, 'r') as f:
            state = json.load(f)
    elif os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
    else:
        state = {}

    state['base'] = 24500
    state['direction'] = 'BELOW'
    state['monthly_expiry'] = '2026-08-25'
    state['next_monthly_expiry'] = '2026-09-29'
    state['weekly_expiry'] = '2026-08-04'

    state['legs'] = {
        'L1_20260707': {
            'trigger_price': 24450,
            'entry_price': 23985.6,
            'original_entry_price': 23985.6,
            'future_side': 'LONG',
            'future_order_id': '9ca2fb5c-20ec-4e61-bc81-93e0c06f2214',
            'monthly_expiry': '2026-08-25',
            'short_opt': {
                'strike': 24300,
                'type': 'CE',
                'expiry': '2026-08-25',
                'premium': 150.0,
                'order_id': 'e9337b01-ffb8-4957-8293-ab4d9a129852',
                'side': 'SELL'
            },
            'long_opt': {
                'strike': 23150,
                'type': 'PE',
                'expiry': '2026-08-04',
                'premium': 11.050000190734863,
                'order_id': 'fd64c0cb-3678-40ab-aa99-3e243a0673bc',
                'side': 'BUY'
            },
            'status': 'OPEN',
            'entry_time': '2026-07-07T15:12:16.617306',
            'hist_fut_pnl': 11225.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -1150.5,
            'realized_pnl': -9516.0
        },
        'L2_20260708': {
            'trigger_price': 24400,
            'entry_price': 23985.6,
            'original_entry_price': 23985.6,
            'future_side': 'LONG',
            'future_order_id': '28db26c2-7a11-449c-8c29-96f68d901705',
            'monthly_expiry': '2026-08-25',
            'short_opt': {
                'strike': 24300,
                'type': 'CE',
                'expiry': '2026-08-25',
                'premium': 150.0,
                'order_id': '5887b405-97a5-4e7a-8926-490f97fff55a',
                'side': 'SELL'
            },
            'long_opt': {
                'strike': 23150,
                'type': 'PE',
                'expiry': '2026-08-04',
                'premium': 11.0,
                'order_id': '21e2341e-61dd-4607-a9d5-a89084f074ad',
                'side': 'BUY'
            },
            'status': 'OPEN',
            'entry_time': '2026-07-08T10:18:48.802286',
            'hist_fut_pnl': 23016.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -2427.75,
            'realized_pnl': 997.75
        },
        'L3_20260708': {
            'trigger_price': 24350,
            'entry_price': 23985.6,
            'original_entry_price': 23985.6,
            'future_side': 'LONG',
            'future_order_id': 'e28d0e6a-caa5-4fab-8007-e6836ae6cb8b',
            'monthly_expiry': '2026-08-25',
            'short_opt': {
                'strike': 24300,
                'type': 'CE',
                'expiry': '2026-08-25',
                'premium': 150.0,
                'order_id': '1da6573a-e9f4-466e-bdbc-1a637de662c4',
                'side': 'SELL'
            },
            'long_opt': {
                'strike': 23150,
                'type': 'PE',
                'expiry': '2026-08-04',
                'premium': 11.0,
                'order_id': '7b9cfe6b-14e5-4093-abd7-f2c7854215c5',
                'side': 'BUY'
            },
            'status': 'OPEN',
            'entry_time': '2026-07-08T10:18:49.766167',
            'hist_fut_pnl': 23016.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -2431.0,
            'realized_pnl': 994.5
        }
    }

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
    print(f"Successfully fixed {state_file} preserving closed_legs, account realized PnL, and leg histories!")

if __name__ == "__main__":
    fix_active_legs()
