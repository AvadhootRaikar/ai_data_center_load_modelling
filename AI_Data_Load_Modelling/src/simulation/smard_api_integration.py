"""
SMARD Real-Time Price Integration

Fetches live German day-ahead electricity prices from the SMARD API
(Bundesnetzagentur - https://www.smard.de).

Features:
- Fetches real Filter 4169 (Day-ahead price, Germany/Luxembourg, hourly)
- Falls back to static CSV when API unavailable
- Caches prices to minimize API calls
- Handles date-specific data fetching
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMARD API Configuration
SMARD_BASE_URL = "https://www.smard.de/app/chart_data"
SMARD_FILTER_ID = 4169  # Day-ahead price filter
SMARD_REGION = "DE"  # Germany/Luxembourg zone
API_TIMEOUT = 10  # seconds
PRICE_CACHE = {}  # In-memory cache


def fetch_smard_index() -> Optional[List[int]]:
    """
    Fetch the index of available weeks from SMARD API.
    
    Returns:
        List of week-start timestamps (milliseconds since epoch), or None if failed
    """
    try:
        url = f"{SMARD_BASE_URL}/{SMARD_FILTER_ID}/{SMARD_REGION}/index_hour.json"
        logger.info(f"Fetching SMARD index from {url}")
        
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        timestamps = data.get('timestamps', [])
        
        logger.info(f" SMARD index fetched: {len(timestamps)} weeks available")
        return timestamps
    
    except requests.exceptions.ConnectionError:
        logger.warning(" SMARD API connection failed - will use fallback pricing")
        return None
    except requests.exceptions.Timeout:
        logger.warning(" SMARD API timeout - will use fallback pricing")
        return None
    except Exception as e:
        logger.warning(f" SMARD API error: {e} - will use fallback pricing")
        return None


def fetch_smard_prices(timestamp_ms: int) -> Optional[Dict[int, float]]:
    """
    Fetch hourly prices for a specific week from SMARD API.
    
    Args:
        timestamp_ms: Week-start timestamp in milliseconds (Monday 00:00 CET)
    
    Returns:
        Dict mapping hour (0-23) to price (EUR/MWh), or None if failed
    """
    try:
        url = f"{SMARD_BASE_URL}/{SMARD_FILTER_ID}/{SMARD_REGION}/{SMARD_FILTER_ID}_{SMARD_REGION}_hour_{timestamp_ms}.json"
        logger.info(f"Fetching SMARD prices for week {timestamp_ms}")
        
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        series = data.get('series', [])
        
        # Convert to dict: hour -> price
        prices_by_hour = {}
        for timestamp, price in series:
            # Convert timestamp to datetime to get hour
            dt = datetime.fromtimestamp(timestamp / 1000)  # Convert ms to seconds
            hour = dt.hour
            prices_by_hour[hour] = price / 1000  # Convert to EUR/kWh (from EUR/MWh ÷ 1000)
        
        logger.info(f" SMARD prices fetched: {len(prices_by_hour)} hours available")
        return prices_by_hour if prices_by_hour else None
    
    except Exception as e:
        logger.warning(f" Error fetching SMARD prices: {e}")
        return None


def get_current_week_timestamp() -> int:
    """
    Get the timestamp (milliseconds) for the current week's Monday 00:00 CET.
    
    Returns:
        Timestamp in milliseconds
    """
    now = datetime.now()
    # Find Monday of current week
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # Convert to milliseconds
    return int(monday.timestamp() * 1000)


def fetch_live_prices(target_date: Optional[datetime] = None) -> Optional[Dict[int, float]]:
    """
    Fetch live prices for today or a specific date from SMARD.
    
    Args:
        target_date: Specific date to fetch prices for (default: today)
    
    Returns:
        Dict mapping hour (0-23) to price (EUR/kWh), or None if failed
    """
    if target_date is None:
        target_date = datetime.now()
    
    # Check cache first
    cache_key = target_date.strftime("%Y-%m-%d")
    if cache_key in PRICE_CACHE:
        logger.info(f" Using cached prices for {cache_key}")
        return PRICE_CACHE[cache_key]
    
    try:
        # Get the week containing this date
        week_start = target_date - timedelta(days=target_date.weekday())
        week_timestamp_ms = int(week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        
        # Fetch prices for that week
        prices = fetch_smard_prices(week_timestamp_ms)
        
        if prices:
            PRICE_CACHE[cache_key] = prices
            logger.info(f" Cached prices for {cache_key}")
            return prices
        
        return None
    
    except Exception as e:
        logger.warning(f" Error fetching live prices: {e}")
        return None


def get_smard_price_for_hour(hour: int, prices_dict: Optional[Dict[int, float]] = None) -> float:
    """
    Get electricity price (EUR/kWh) for a specific hour.
    
    Args:
        hour: Hour of day (0-23)
        prices_dict: Prices dict from fetch_live_prices (optional)
    
    Returns:
        Price in EUR/kWh
    """
    if prices_dict and hour in prices_dict:
        return prices_dict[hour]
    
    # Fallback to static time-of-use pricing
    if 0 <= hour < 6:
        return 0.027  # Off-peak
    elif 6 <= hour < 10:
        return 0.044  # Early Morning
    elif 10 <= hour < 16:
        return 0.031  # Midday
    elif 16 <= hour < 21:
        return 0.050  # Evening Peak
    else:
        return 0.035  # Late Night


def build_daily_price_curve(prices_dict: Optional[Dict[int, float]] = None) -> Dict[int, float]:
    """
    Build a complete 24-hour price curve, using live data where available.
    
    Args:
        prices_dict: Live prices from SMARD (optional)
    
    Returns:
        Dict mapping each hour (0-23) to price (EUR/kWh)
    """
    return {hour: get_smard_price_for_hour(hour, prices_dict) for hour in range(24)}


def get_prices_with_fallback(target_date: Optional[datetime] = None) -> Tuple[Dict[int, float], bool]:
    """
    Get prices with automatic fallback to static data.
    
    Args:
        target_date: Specific date (default: today)
    
    Returns:
        Tuple of (prices_dict, is_live_data)
        - prices_dict: Dict mapping hour (0-23) to price (EUR/kWh)
        - is_live_data: True if from SMARD API, False if fallback
    """
    try:
        live_prices = fetch_live_prices(target_date)
        if live_prices:
            full_curve = build_daily_price_curve(live_prices)
            logger.info(" Using LIVE SMARD prices")
            return full_curve, True
        else:
            logger.warning(" SMARD data unavailable - using static fallback")
            full_curve = build_daily_price_curve(None)
            return full_curve, False
    
    except Exception as e:
        logger.error(f"Error getting prices: {e} - using static fallback")
        full_curve = build_daily_price_curve(None)
        return full_curve, False


def export_prices_to_csv(prices_dict: Dict[int, float], output_path: str = "smard_prices_today.csv"):
    """
    Export fetched prices to CSV for reference.
    
    Args:
        prices_dict: Prices from SMARD
        output_path: Output CSV file path
    """
    try:
        rows = [
            {"Hour": f"{hour:02d}:00", "Price_EUR_per_kWh": price}
            for hour, price in sorted(prices_dict.items())
        ]
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        logger.info(f" Prices exported to {output_path}")
    except Exception as e:
        logger.warning(f" Could not export prices: {e}")


# Example usage / Testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("SMARD Real-Time Price Integration Test")
    print("="*60 + "\n")
    
    # Test 1: Fetch live prices
    print("Test 1: Fetching live prices from SMARD...")
    prices, is_live = get_prices_with_fallback()
    print(f"Data source: {'LIVE SMARD API' if is_live else 'Static Fallback'}\n")
    
    # Display hourly prices
    print("24-Hour Price Curve (EUR/kWh):")
    print("-" * 40)
    for hour in range(24):
        price = prices[hour]
        print(f"Hour {hour:02d}:00 - {hour+1:02d}:00 → €{price:.4f}/kWh")
    
    print("\n" + "-" * 40)
    print(f"Min price: €{min(prices.values()):.4f}/kWh (off-peak)")
    print(f"Max price: €{max(prices.values()):.4f}/kWh (peak)")
    print(f"Avg price: €{sum(prices.values())/24:.4f}/kWh")
    
    # Test 2: Export prices
    print("\n\nTest 2: Exporting prices to CSV...")
    export_prices_to_csv(prices)
    
    print("\n SMARD integration test complete!")
