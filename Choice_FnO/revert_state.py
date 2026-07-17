import json

with open('state_snapshot.json', 'r') as f:
    state = json.load(f)

# Revert L1
state['legs']['L1_20260707']['short_opt'] = {
    'strike': 24750,
    'type': 'CE',
    'expiry': '2026-07-28',
    'premium': 115.5,
    'order_id': 'e9337b01-ffb8-4957-8293-ab4d9a129852',
    'side': 'SELL'
}
state['legs']['L1_20260707']['long_opt'] = {
    'strike': 23050,
    'type': 'PE',
    'expiry': '2026-07-21',
    'premium': 11.800000190734863,
    'order_id': 'fd64c0cb-3678-40ab-aa99-3e243a0673bc',
    'side': 'BUY'
}

# Revert L2
state['legs']['L2_20260708']['short_opt'] = {
    'strike': 24550,
    'type': 'CE',
    'expiry': '2026-07-28',
    'premium': 136.5,
    'order_id': '5887b405-97a5-4e7a-8926-490f97fff55a',
    'side': 'SELL'
}
state['legs']['L2_20260708']['long_opt'] = {
    'strike': 23050,
    'type': 'PE',
    'expiry': '2026-07-21',
    'premium': 11.800000190734863,
    'order_id': '21e2341e-61dd-4607-a9d5-a89084f074ad',
    'side': 'BUY'
}

# Revert L3
state['legs']['L3_20260708']['short_opt'] = {
    'strike': 24550,
    'type': 'CE',
    'expiry': '2026-07-28',
    'premium': 136.5,
    'order_id': '1da6573a-e9f4-466e-bdbc-1a637de662c4',
    'side': 'SELL'
}
state['legs']['L3_20260708']['long_opt'] = {
    'strike': 23050,
    'type': 'PE',
    'expiry': '2026-07-21',
    'premium': 11.800000190734863,
    'order_id': '7b9cfe6b-14e5-4093-abd7-f2c7854215c5',
    'side': 'BUY'
}

# Revert L4
state['legs']['L4_20260708']['short_opt'] = {
    'strike': 24550,
    'type': 'CE',
    'expiry': '2026-07-28',
    'premium': 136.5,
    'order_id': 'd9b5c5f0-68ac-4690-99b2-ac4b4ab7f33c',
    'side': 'SELL'
}
state['legs']['L4_20260708']['long_opt'] = {
    'strike': 23050,
    'type': 'PE',
    'expiry': '2026-07-21',
    'premium': 11.800000190734863,
    'order_id': 'd48ec648-3764-4a95-9a52-92f43f874e89',
    'side': 'BUY'
}

# Revert L5
state['legs']['L5_20260708']['short_opt'] = {
    'strike': 24550,
    'type': 'CE',
    'expiry': '2026-07-28',
    'premium': 131.0500030517578,
    'order_id': 'a5189c73-705f-40d6-a081-f7f35f3c7b52',
    'side': 'SELL'
}
state['legs']['L5_20260708']['long_opt'] = {
    'strike': 23050,
    'type': 'PE',
    'expiry': '2026-07-21',
    'premium': 11.800000190734863,
    'order_id': 'ccbdf004-287a-4864-a567-0d02ffc3d8ee',
    'side': 'BUY'
}

with open('state_snapshot.json', 'w') as f:
    json.dump(state, f, indent=4)
