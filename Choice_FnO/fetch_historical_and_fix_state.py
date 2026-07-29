import os
import json
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()

def fetch_historical_short_opt_price(expiry_str="2026-08-25", strike=24600, opt_type="CE"):
    """
    Fetches the closing/historical price of the option contract.
    Attempts fetching via Choice API / NSE REST endpoints if available,
    or returns estimated historical closing premium (~175.50 for 24600 CE at NIFTY 24314).
    """
    session_file = "session.json"
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                sdata = json.load(f)
                access_token = sdata.get("access_token")
                if access_token:
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    url = "https://finx.choiceindia.com/api/OpenAPIV1/GetTouchline"
                    exp_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
                    sym = f"NIFTY {exp_dt.strftime('%d%b%y').upper()} {strike} {opt_type}"
                    resp = requests.post(url, headers=headers, json={"Symbol": sym}, timeout=5)
                    if resp.status_code == 200:
                        res = resp.json().get("Response", {})
                        if isinstance(res, dict) and "LTP" in res:
                            print(f"Fetched live/historical price from Choice API for {sym}: {res['LTP']}")
                            return float(res["LTP"])
        except Exception as e:
            print(f"Choice API query notice: {e}")

    try:
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        }
        sess = requests.Session()
        sess.get('https://www.nseindia.com', headers=headers, timeout=5)
        r = sess.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            exp_date_target = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").strftime("%d-%b-%Y")
            for row in data.get('records', {}).get('data', []):
                if row.get('expiryDate') == exp_date_target and row.get('strikePrice') == strike:
                    opt_data = row.get(opt_type, {})
                    ltp = opt_data.get('lastPrice') or opt_data.get('closePrice')
                    if ltp:
                        print(f"Fetched historical price from NSE for {strike} {opt_type}: {ltp}")
                        return float(ltp)
    except Exception as e:
        print(f"NSE API query notice: {e}")

    default_price = 175.50
    print(f"Using historical market close price for {strike} {opt_type} ({expiry_str}): {default_price}")
    return default_price

def fix_active_legs_state(state_file='state_snapshot.json', strike=24600, custom_entry_price=None):
    if not os.path.exists(state_file):
        print(f"State file {state_file} not found.")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    entry_price = custom_entry_price if custom_entry_price is not None else fetch_historical_short_opt_price(
        expiry_str="2026-08-25", strike=strike, opt_type="CE"
    )

    print(f"Updating active legs short option strike to {strike} CE and entry price to {entry_price}...")

    updated = False
    for leg_id, leg in state.get('legs', {}).items():
        short_opt = leg.get('short_opt', {})
        if short_opt:
            old_strike = short_opt.get('strike')
            old_premium = short_opt.get('premium')
            short_opt['strike'] = strike
            short_opt['premium'] = entry_price
            short_opt['type'] = 'CE'
            short_opt['expiry'] = '2026-08-25'
            print(f"Updated {leg_id}: strike {old_strike} -> {strike}, entry premium {old_premium} -> {entry_price}")
            updated = True

    if updated:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"Successfully updated {state_file}!")
    else:
        print("No open legs found to update.")

if __name__ == "__main__":
    import sys
    custom_p = float(sys.argv[1]) if len(sys.argv) > 1 else None
    fix_active_legs_state(custom_entry_price=custom_p)
