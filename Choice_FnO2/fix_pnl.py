import json

with open('state_snapshot.json', 'r') as f:
    state = json.load(f)

for leg_id, leg in state.get('legs', {}).items():
    if "realized_pnl" not in leg:
        leg['realized_pnl'] = 0.0

with open('state_snapshot.json', 'w') as f:
    json.dump(state, f, indent=4)
