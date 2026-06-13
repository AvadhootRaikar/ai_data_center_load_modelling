#!/usr/bin/env python3
"""Check available SMARD data"""

import requests
import json
from datetime import datetime

print("🔍 Checking available SMARD data...")
print()

# Fetch available timestamps (weeks)
url = 'https://www.smard.de/app/chart_data/4169/DE/index_hour.json'
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    if 'timestamps' in data:
        timestamps = data['timestamps']
        print(f"✅ Found {len(timestamps)} available weeks")
        print()
        print("Latest 5 weeks available:")
        print("─" * 50)
        for ts in timestamps[:5]:
            dt = datetime.fromtimestamp(ts/1000)
            print(f"  {dt.strftime('%Y-%m-%d %A')} (timestamp: {ts})")
        
        # Try to fetch prices for the most recent week
        print()
        print("Fetching prices for most recent week...")
        latest_ts = timestamps[0]
        price_url = f'https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_{latest_ts}.json'
        price_response = requests.get(price_url)
        
        if price_response.status_code == 200:
            price_data = price_response.json()
            if 'series' in price_data and price_data['series']:
                prices = price_data['series'][:24]
                print(f"✅ Successfully fetched {len(prices)} hourly prices!")
                print()
                print('24-Hour Price Curve:')
                print('─' * 50)
                prices_kwh = []
                for i, (ts, price_mwh) in enumerate(prices):
                    price_kwh = price_mwh / 1000
                    prices_kwh.append(price_kwh)
                    dt = datetime.fromtimestamp(ts/1000)
                    print(f'Hour {i:02d}: €{price_kwh:.4f}/kWh')
                
                print('─' * 50)
                print(f'Min: €{min(prices_kwh):.4f}/kWh')
                print(f'Max: €{max(prices_kwh):.4f}/kWh')
                print(f'Avg: €{sum(prices_kwh)/len(prices_kwh):.4f}/kWh')
                print()
                print("🎉 SMARD API IS WORKING! ✅")
            else:
                print("❌ No price data found")
        else:
            print(f"❌ Price fetch failed: Status {price_response.status_code}")
    else:
        print("❌ No timestamps in response")
else:
    print(f"❌ Index fetch failed: Status {response.status_code}")
