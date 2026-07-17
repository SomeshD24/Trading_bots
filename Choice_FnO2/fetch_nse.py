import requests, json, time
url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br'
}
session = requests.Session()
session.get('https://www.nseindia.com', headers=headers, timeout=10)
time.sleep(1)
r = session.get(url, headers=headers, timeout=10)
if r.status_code == 200:
    data = r.json()
    records = data['records']['data']
    for row in records:
        if '14-Jul' in row['expiryDate']:
            ce = row.get('CE', {})
            if ce and 5 <= ce.get('lastPrice', 0) <= 15:
                print(f"Strike: {ce['strikePrice']}, Premium: {ce['lastPrice']}")
else:
    print('Failed', r.status_code, r.text[:200])
