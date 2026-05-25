"""
Cost Model with Time-of-Use Pricing Support

Calculates operational costs with:
- Flat-rate pricing
- Time-of-day (ToD) pricing reflecting German grid dynamics
- Cost projections
"""

import pandas as pd
from typing import Tuple, Optional


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
