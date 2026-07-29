import json
import os

def fix_cloud_pnl_and_legs(state_file='state_snapshot.json'):
    """
    Restores account-level realized_pnl (126704.50), closed_legs history,
    and individual active leg PnLs.
    """
    if not os.path.exists(state_file):
        print(f"State file {state_file} not found.")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    # 1. Restore account-level realized PnL
    target_account_realized_pnl = 126704.49866104094
    state['realized_pnl'] = target_account_realized_pnl

    # 2. Restore closed_legs if missing or empty
    initial_file = 'state_snapshot.initial.json'
    if (not state.get('closed_legs') or len(state.get('closed_legs', [])) == 0) and os.path.exists(initial_file):
        with open(initial_file, 'r') as f:
            init_data = json.load(f)
            if init_data.get('closed_legs'):
                state['closed_legs'] = init_data['closed_legs']
                state['total_legs_opened'] = init_data.get('total_legs_opened', 29)
                print(f"Restored {len(state['closed_legs'])} closed legs from initial snapshot.")

    # 3. Restore individual active leg PnLs
    active_leg_pnl_map = {
        'L1_20260707': {
            'hist_fut_pnl': 11225.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -1150.5,
            'realized_pnl': -9516.0
        },
        'L2_20260708': {
            'hist_fut_pnl': 23016.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -2427.75,
            'realized_pnl': 997.75
        },
        'L3_20260708': {
            'hist_fut_pnl': 23016.5,
            'hist_short_pnl': -19591.0,
            'hist_long_pnl': -2431.0,
            'realized_pnl': 994.5
        }
    }

    legs = state.get('legs', {})
    for leg_id, pnl_data in active_leg_pnl_map.items():
        if leg_id in legs:
            legs[leg_id]['hist_fut_pnl'] = pnl_data['hist_fut_pnl']
            legs[leg_id]['hist_short_pnl'] = pnl_data['hist_short_pnl']
            legs[leg_id]['hist_long_pnl'] = pnl_data['hist_long_pnl']
            legs[leg_id]['realized_pnl'] = pnl_data['realized_pnl']
            print(f"Restored PnL for {leg_id}: realized_pnl = {pnl_data['realized_pnl']}")

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
    print(f"Successfully fixed account realized PnL ({target_account_realized_pnl}) and leg PnLs in {state_file}!")

if __name__ == "__main__":
    fix_cloud_pnl_and_legs()
