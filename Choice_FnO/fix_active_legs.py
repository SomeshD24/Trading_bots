import json
import os

def fix_active_legs(state_file='state_snapshot.json'):
    """
    Restores the active legs in state_snapshot.json to the exact post-rollover state:
    - Base: 24500 (remains unchanged after rollover)
    - Future Entry: 23985.6
    - Short Opt: 24300 CE (ATM 24000 + 6 strikes) @ premium 150.0
    - Monthly Expiry: 2026-08-25
    """
    active_state = {
        'base': 24500,
        'direction': 'BELOW',
        'monthly_expiry': '2026-08-25',
        'next_monthly_expiry': '2026-09-29',
        'weekly_expiry': '2026-08-04',
        'legs': {
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
                'hist_fut_pnl': -8690.5,
                'hist_short_pnl': -10266.75,
                'realized_pnl': -19678.75
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
                'hist_fut_pnl': 3100.5,
                'hist_short_pnl': -10266.75,
                'realized_pnl': -9168.25
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
                'hist_fut_pnl': 3100.5,
                'hist_short_pnl': -10266.75,
                'realized_pnl': -9171.5
            }
        }
    }

    with open(state_file, 'w') as f:
        json.dump(active_state, f, indent=4)
    print(f"Successfully updated {state_file} with post-rollover active legs (Future Entry 23985.6, Base 24500, Short Opt 24300 CE)!")

if __name__ == "__main__":
    fix_active_legs()
