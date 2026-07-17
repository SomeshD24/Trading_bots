import csv
with open('logs/leg_log.csv') as f:
    r = csv.DictReader(f)
    sum_pnl = 0
    sum_cols = 0
    for row in r:
        if row['leg_id'] in ['L1', 'L13_20260708']: continue
        realized = float(row['realized_pnl'])
        fut = float(row['fut_pnl'])
        short = float(row['short_pnl'])
        long = float(row['long_pnl'])
        sum_pnl += realized
        sum_cols += fut + short + long
        print(f"{row['leg_id']}: realized={realized}, cols_sum={fut+short+long}")
    print(f'TOTAL realized={sum_pnl}, cols_sum={sum_cols}')
