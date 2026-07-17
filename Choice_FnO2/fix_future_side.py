import json

with open('state_snapshot.json', 'r') as f:
    state = json.load(f)

for leg_id, leg in state.get('legs', {}).items():
    if "future_side" not in leg:
        # If direction is BELOW (Calls), it means we are short futures
        if leg.get('direction') == 'BELOW':
            leg['future_side'] = 'SHORT'
        else:
            leg['future_side'] = 'LONG'
        
    if "future_order_id" not in leg:
        leg['future_order_id'] = "dummy_future_id"

with open('state_snapshot.json', 'w') as f:
    json.dump(state, f, indent=4)
print("Added future_side to state!")
