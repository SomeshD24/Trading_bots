import json
with open('state_snapshot.json', 'r') as f:
    state = json.load(f)
    if state.get('legs'):
        first_leg = list(state['legs'].values())[0]
        print(json.dumps(first_leg, indent=4))
