import json
with open('state_snapshot.json', 'r') as f:
    state = json.load(f)

for leg in state['legs'].values():
    print(f"Leg: {leg.get('entry_time')} - short: {leg.get('short_opt')}")
