#!/usr/bin/env python3
"""Quick SMARD API Test"""

import requests
from datetime import datetime, timedelta

# Get current week timestamp
now = datetime.now()
# Find most recent Friday (SMARD weeks end on Friday)
days_since_friday = (now.weekday() - 4) % 7
last_friday = now - timedelta(days=days_since_friday)
timestamp_ms = int(last_friday.timestamp() * 1000)

print("🔍 Fetching SMARD prices for week of:", last_friday.strftime('%Y-%m-%d'))
print()

# Fetch prices
url = f'https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_{timestamp_ms}.json'
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    if 'series' in data and data['series']:
        prices = data['series'][:24]  # Get first 24 hours
        print('✅ Successfully fetched 24-hour prices from SMARD!')
        print()
        print('Hourly Prices (EUR/MWh → EUR/kWh):')
        print('─' * 50)
        for i, (ts, price_mwh) in enumerate(prices):
            price_kwh = price_mwh / 1000
            dt = datetime.fromtimestamp(ts/1000)
            print(f'Hour {i:02d} ({dt.strftime("%H:%M")}): €{price_mwh:7.2f}/MWh → €{price_kwh:.4f}/kWh')
        
        print('─' * 50)
        prices_kwh = [p[1]/1000 for p in prices]
        print(f'Min: €{min(prices_kwh):.4f}/kWh')
        print(f'Max: €{max(prices_kwh):.4f}/kWh')
        print(f'Avg: €{sum(prices_kwh)/len(prices_kwh):.4f}/kWh')
    else:
        print('❌ No data in SMARD response')
else:
    print(f'❌ API Error: Status {response.status_code}')
