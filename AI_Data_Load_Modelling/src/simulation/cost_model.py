"""
Cost Model with Time-of-Use Pricing & Live SMARD API Integration

Calculates operational costs with:
- Flat-rate pricing
- Time-of-day (ToD) pricing reflecting German grid dynamics
- LIVE SMARD day-ahead prices (with fallback to static ToD)
- Cost projections
"""

import pandas as pd
from typing import Tuple, Optional, Dict
from datetime import datetime

# Try to import SMARD API module; graceful fallback if unavailable
try:
    from smard_api_integration import get_prices_with_fallback, get_smard_price_for_hour
    SMARD_AVAILABLE = True
except ImportError:
    SMARD_AVAILABLE = False


def calculate_costs(results_df: pd.DataFrame, price_per_kwh: float) -> Tuple[pd.DataFrame, float]:
    """Flat-price cost calculation."""
    df = results_df.copy()
    if "energy_mwh" not in df.columns:
        if "total_power_mw" not in df.columns or "delta_seconds" not in df.columns:
            raise ValueError("results_df must contain energy_mwh or total_power_mw + delta_seconds")
        df["energy_mwh"] = df["total_power_mw"] * df["delta_seconds"] / 3600.0

    df["energy_kwh"] = df["energy_mwh"] * 1000.0
    df["price_period"] = "Flat price"
    df["price_eur_per_kwh"] = float(price_per_kwh)
    df["cost_eur"] = df["energy_kwh"] * df["price_eur_per_kwh"]
    return df, float(df["cost_eur"].sum())


def build_tou_price_table(
    night_price: float = 0.27,
    morning_price: float = 0.44,
    midday_price: float = 0.31,
    evening_peak_price: float = 0.50,
    late_price: float = 0.35,
) -> pd.DataFrame:
    """
    German-style time-of-use tariff table.
    
    Defaults calibrated around German 2025 dynamic-tariff levels with
    typical intraday behavior: lower night/midday (solar), higher morning/evening peaks.
    """
    return pd.DataFrame([
        {
            "period": "Night / off-peak",
            "start_hour": 0,
            "end_hour": 6,
            "price_eur_per_kwh": float(night_price),
        },
        {
            "period": "Morning peak",
            "start_hour": 6,
            "end_hour": 10,
            "price_eur_per_kwh": float(morning_price),
        },
        {
            "period": "Midday / renewable window",
            "start_hour": 10,
            "end_hour": 16,
            "price_eur_per_kwh": float(midday_price),
        },
        {
            "period": "Evening peak",
            "start_hour": 16,
            "end_hour": 21,
            "price_eur_per_kwh": float(evening_peak_price),
        },
        {
            "period": "Late evening",
            "start_hour": 21,
            "end_hour": 24,
            "price_eur_per_kwh": float(late_price),
        },
    ])


def _price_for_hour(hour: float, price_table: pd.DataFrame) -> Tuple[float, str]:
    """Get price and period name for a given hour (0-24)."""
    hour = float(hour) % 24.0
    for _, row in price_table.iterrows():
        if float(row["start_hour"]) <= hour < float(row["end_hour"]):
            return float(row["price_eur_per_kwh"]), str(row["period"])
    last = price_table.iloc[-1]
    return float(last["price_eur_per_kwh"]), str(last["period"])


def calculate_time_of_day_costs(
    results_df: pd.DataFrame,
    price_table: pd.DataFrame,
    simulation_start_hour: float = 12.0,
) -> Tuple[pd.DataFrame, float]:
    """
    Calculates cost with time-of-day prices.
    
    Clock hour calculation allows modeling impact of schedule shifting
    on operational costs.
    """
    df = results_df.copy()
    if "delta_seconds" not in df.columns or "total_power_mw" not in df.columns:
        raise ValueError("results_df must contain delta_seconds and total_power_mw")

    if "energy_mwh" not in df.columns:
        df["energy_mwh"] = df["total_power_mw"] * df["delta_seconds"] / 3600.0

    df["energy_kwh"] = df["energy_mwh"] * 1000.0

    if "elapsed_seconds" in df.columns:
        interval_mid_seconds = df["elapsed_seconds"] - df["delta_seconds"] / 2.0
    else:
        interval_mid_seconds = df["delta_seconds"].cumsum() - df["delta_seconds"] / 2.0

    df["clock_hour"] = (float(simulation_start_hour) + interval_mid_seconds / 3600.0) % 24.0

    prices = []
    periods = []
    for hour in df["clock_hour"]:
        price, period = _price_for_hour(hour, price_table)
        prices.append(price)
        periods.append(period)

    df["price_period"] = periods
    df["price_eur_per_kwh"] = prices
    df["cost_eur"] = df["energy_kwh"] * df["price_eur_per_kwh"]
    return df, float(df["cost_eur"].sum())


def calculate_cost_projection(avg_power_mw: float, price_per_kwh: float) -> dict:
    """Cost projection based on average power."""
    avg_power_kw = avg_power_mw * 1000.0
    return {
        "1h_cost_eur": avg_power_kw * 1 * price_per_kwh,
        "6h_cost_eur": avg_power_kw * 6 * price_per_kwh,
        "24h_cost_eur": avg_power_kw * 24 * price_per_kwh,
        "30d_cost_eur": avg_power_kw * 24 * 30 * price_per_kwh,
    }


# ============================================================================
# SMARD LIVE PRICE INTEGRATION
# ============================================================================

def calculate_time_of_day_costs_with_smard(
    results_df: pd.DataFrame,
    simulation_start_hour: float = 12.0,
    price_table: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, float, bool]:
    """
    Calculate costs using LIVE SMARD prices with fallback to static ToD.
    
    This function:
    1. Attempts to fetch LIVE prices from SMARD API
    2. Falls back to static time-of-use table if API unavailable
    3. Returns (results_df, total_cost, is_live_data)
    
    Args:
        results_df: Simulation results with delta_seconds and total_power_mw
        simulation_start_hour: Clock hour simulation starts (0-23)
        price_table: Optional static price table for fallback
    
    Returns:
        Tuple of (results_df with costs, total_cost_eur, is_live_data_bool)
    """
    df = results_df.copy()
    if "delta_seconds" not in df.columns or "total_power_mw" not in df.columns:
        raise ValueError("results_df must contain delta_seconds and total_power_mw")

    if "energy_mwh" not in df.columns:
        df["energy_mwh"] = df["total_power_mw"] * df["delta_seconds"] / 3600.0

    df["energy_kwh"] = df["energy_mwh"] * 1000.0

    # Calculate clock hour for each timestep
    if "elapsed_seconds" in df.columns:
        interval_mid_seconds = df["elapsed_seconds"] - df["delta_seconds"] / 2.0
    else:
        interval_mid_seconds = df["delta_seconds"].cumsum() - df["delta_seconds"] / 2.0

    df["clock_hour"] = (float(simulation_start_hour) + interval_mid_seconds / 3600.0) % 24.0

    # Try to get LIVE SMARD prices
    if SMARD_AVAILABLE:
        try:
            prices_dict, is_live = get_prices_with_fallback()
            prices = []
            periods = []
            
            for hour in df["clock_hour"]:
                hour_int = int(hour) % 24
                price = get_smard_price_for_hour(hour_int, prices_dict if is_live else None)
                prices.append(price)
                periods.append(f"Hour {hour_int:02d}" if is_live else "ToD Fallback")
            
            df["price_period"] = periods
            df["price_eur_per_kwh"] = prices
            df["cost_eur"] = df["energy_kwh"] * df["price_eur_per_kwh"]
            
            return df, float(df["cost_eur"].sum()), is_live
        
        except Exception as e:
            print(f"Warning: SMARD API failed ({e}) - using static fallback")
    
    # Fallback to static price table
    if price_table is None:
        price_table = build_tou_price_table()
    
    prices = []
    periods = []
    for hour in df["clock_hour"]:
        price, period = _price_for_hour(hour, price_table)
        prices.append(price)
        periods.append(period)

    df["price_period"] = periods
    df["price_eur_per_kwh"] = prices
    df["cost_eur"] = df["energy_kwh"] * df["price_eur_per_kwh"]
    
    return df, float(df["cost_eur"].sum()), False  # is_live = False (static fallback)


def get_live_hourly_prices(target_date: Optional[datetime] = None) -> Tuple[Dict[int, float], bool]:
    """
    Fetch live hourly prices from SMARD or static fallback.
    
    Args:
        target_date: Target date (default: today)
    
    Returns:
        Tuple of (hourly_prices_dict, is_live_data)
    """
    if SMARD_AVAILABLE:
        try:
            prices, is_live = get_prices_with_fallback(target_date)
            return prices, is_live
        except Exception as e:
            print(f"Warning: Could not fetch SMARD prices: {e}")
    
    # Fallback to static
    static_prices = {
        0: 0.027, 1: 0.027, 2: 0.027, 3: 0.027, 4: 0.027, 5: 0.027,  # Off-peak
        6: 0.044, 7: 0.044, 8: 0.044, 9: 0.044,  # Early Morning
        10: 0.031, 11: 0.031, 12: 0.031, 13: 0.031, 14: 0.031, 15: 0.031,  # Midday
        16: 0.050, 17: 0.050, 18: 0.050, 19: 0.050, 20: 0.050,  # Evening Peak
        21: 0.035, 22: 0.035, 23: 0.035,  # Late Night
    }
    return static_prices, False


def get_smard_status() -> Dict:
    """
    Get status of SMARD API integration.
    
    Returns:
        Dict with status information
    """
    return {
        "smard_module_available": SMARD_AVAILABLE,
        "can_fetch_live_prices": SMARD_AVAILABLE,
        "fallback_available": True,
        "default_behavior": "LIVE SMARD prices (with fallback)" if SMARD_AVAILABLE else "Static ToD pricing",
    }

