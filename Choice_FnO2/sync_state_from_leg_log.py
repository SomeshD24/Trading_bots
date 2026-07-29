import os
import csv
import json

def sync_state_from_leg_log():
    """
    Scraped and updates state_snapshot.json ONLY for the current bot directory (Choice_FnO or Choice_FnO2).
    Keeps Choice_FnO and Choice_FnO2 states completely independent.
    Treats L1, L2, L3 as rolled over legs and L52 as a fresh recent leg (no rollover).
    """
    current_folder = os.path.dirname(os.path.abspath(__file__))
    state_file = os.path.join(current_folder, "state_snapshot.json")
    
    possible_logs = [
        os.path.join(current_folder, "logs", "leg_log.csv"),
        os.path.join(current_folder, "leg_log.csv")
    ]
    
    target_log = None
    for p in possible_logs:
        if os.path.exists(p):
            target_log = p
            break

    closed_legs = []
    total_realized_pnl = 0.0
    total_legs_count = 0

    if target_log:
        print(f"[{os.path.basename(current_folder)}] Reading trade history from {target_log}...")
        with open(target_log, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_legs_count += 1
                if row.get('status') == 'CLOSED':
                    pnl = float(row.get('realized_pnl', 0.0))
                    closed_legs.append({
                        'leg_id': row.get('leg_id'),
                        'pnl': pnl,
                        'close_time': row.get('timestamp')
                    })
                    total_realized_pnl += pnl

    # Load current bot's state_snapshot.json
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

    state['base'] = state.get('base', 24500)
    state['direction'] = state.get('direction', 'BELOW')
    state['monthly_expiry'] = state.get('monthly_expiry', '2026-08-25')
    state['next_monthly_expiry'] = state.get('next_monthly_expiry', '2026-09-29')
    state['weekly_expiry'] = state.get('weekly_expiry', '2026-08-04')
    if closed_legs:
        state['closed_legs'] = closed_legs
        state['realized_pnl'] = total_realized_pnl
    state['total_legs_opened'] = max(total_legs_count, state.get('total_legs_opened', len(closed_legs)))

    # Active open legs for this bot instance
    legs = state.get('legs', {})
    
    # 1. Rolled over active legs (L1, L2, L3)
    rolled_over_pnl = {
        'L1_20260707': {'fut': 52591.5, 'short': -20228.0, 'long': -11196.25, 'total': 21167.25},
        'L2_20260708': {'fut': 64382.5, 'short': -20228.0, 'long': -12467.0, 'total': 31687.50},
        'L3_20260708': {'fut': 64382.5, 'short': -20228.0, 'long': -12470.25, 'total': 31684.25}
    }
    
    for leg_id, pnl_info in rolled_over_pnl.items():
        if leg_id in legs:
            legs[leg_id]['short_opt'] = {
                'strike': 24750,
                'type': 'CE',
                'expiry': '2026-08-25',
                'premium': 107.05,
                'order_id': legs[leg_id].get('short_opt', {}).get('order_id', 'short-opt-id'),
                'side': 'SELL'
            }
            legs[leg_id]['hist_fut_pnl'] = pnl_info['fut']
            legs[leg_id]['hist_short_pnl'] = pnl_info['short']
            legs[leg_id]['hist_long_pnl'] = pnl_info['long']
            legs[leg_id]['realized_pnl'] = pnl_info['total']

    # 2. Fresh recent leg L52 (no rollover)
    if 'L52_20260729' in legs:
        legs['L52_20260729']['short_opt'] = {
            'strike': 24750,
            'type': 'CE',
            'expiry': '2026-08-25',
            'premium': 107.05000305175781,
            'order_id': legs['L52_20260729'].get('short_opt', {}).get('order_id', 'mock-order-52-short'),
            'side': 'SELL'
        }
        legs['L52_20260729']['hist_fut_pnl'] = 2171.0
        legs['L52_20260729']['hist_short_pnl'] = -630.5
        legs['L52_20260729']['hist_long_pnl'] = -13.0
        legs['L52_20260729']['realized_pnl'] = 1527.50

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4)

    print(f"[{os.path.basename(current_folder)}] Successfully synced state in {state_file}! Parsed {len(state.get('closed_legs', []))} closed legs. Realized PnL: INR {state.get('realized_pnl', 0.0):,.2f}")

if __name__ == "__main__":
    sync_state_from_leg_log()
