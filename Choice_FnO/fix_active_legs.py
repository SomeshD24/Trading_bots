import json
import os

def fix_active_legs(state_file='state_snapshot.json'):
    if not os.path.exists(state_file):
        print(f"File {state_file} does not exist.")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    updated = False
    for leg_id, leg in state.get('legs', {}).items():
        short_opt = leg.get('short_opt', {})
        if short_opt and short_opt.get('expiry') == '2026-08-25' and short_opt.get('strike') == 24300:
            print(f"Fixing wrong rolled over short_opt for {leg_id}: 24300 CE -> 24600 CE")
            short_opt['strike'] = 24600
            updated = True

    if updated:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"Successfully updated {state_file}")
    else:
        print(f"No wrong 24300 CE short options found in {state_file}")

if __name__ == "__main__":
    fix_active_legs()
