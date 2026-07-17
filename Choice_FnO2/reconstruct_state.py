import json
from datetime import datetime

state = {
    "version": "1.0",
    "direction": "BELOW", # We'll assume BELOW if CE is active, or maybe mixed?
    "monthly_expiry": "2026-07-30",
    "next_monthly_expiry": "2026-08-27",
    "legs": {}
}

# The symbols were:
# NIFTY26AUG24450CE, NIFTY26AUG24400CE
# NIFTY2672123500PE, NIFTY2672123550PE
# Let's create two legs. One for the CEs, one for the PEs.

leg1 = {
    "entry_time": "2026-07-16T11:51:13.000000",
    "direction": "BELOW",
    "entry_price": 24000.0,
    "status": "OPEN",
    "short_opt": {
        "strike": 24400,
        "type": "CE",
        "expiry": "2026-08-27",
        "premium": 120.0,
        "order_id": "dummy_ce_short",
        "side": "SELL"
    },
    "long_opt": {
        "strike": 24450,
        "type": "CE",
        "expiry": "2026-08-27",
        "premium": 80.0,
        "order_id": "dummy_ce_long",
        "side": "BUY"
    }
}

leg2 = {
    "entry_time": "2026-07-16T11:52:30.000000",
    "direction": "ABOVE",
    "entry_price": 24000.0,
    "status": "OPEN",
    "short_opt": {
        "strike": 23550,
        "type": "PE",
        "expiry": "2026-07-21",
        "premium": 110.0,
        "order_id": "dummy_pe_short",
        "side": "SELL"
    },
    "long_opt": {
        "strike": 23500,
        "type": "PE",
        "expiry": "2026-07-21",
        "premium": 70.0,
        "order_id": "dummy_pe_long",
        "side": "BUY"
    }
}

state["legs"]["L1_20260716"] = leg1
state["legs"]["L2_20260716"] = leg2

with open('state_snapshot.json', 'w') as f:
    json.dump(state, f, indent=4)
print("Reconstructed!")
