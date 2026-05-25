import pandas as pd


def calculate_costs(results_df: pd.DataFrame, price_per_kwh: float):
    """Flat-price cost: cost = energy_kwh × price_per_kwh."""
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
    Simplified German-style time-of-use tariff table.

    Important:
    - These are scenario assumptions, not live market prices.
    - Defaults are calibrated around German 2025 dynamic-tariff average levels
      and typical intraday behavior: lower prices at night / renewable-rich midday,
      higher prices in morning and evening demand peaks.
    - Users can edit all prices in the Streamlit sidebar.
    """
    return pd.DataFrame(
        [
            {
                "period": "Night / off-peak",
                "start_hour": 0,
                "end_hour": 6,
                "price_eur_per_kwh": float(night_price),
                "interpretation": "Low-demand night hours. Delayed training can become cheaper if shifted here.",
            },
            {
                "period": "Morning peak",
                "start_hour": 6,
                "end_hour": 10,
                "price_eur_per_kwh": float(morning_price),
                "interpretation": "Morning demand peak; usually more expensive than night or midday.",
            },
            {
                "period": "Midday / renewable window",
                "start_hour": 10,
                "end_hour": 16,
                "price_eur_per_kwh": float(midday_price),
                "interpretation": "Often cheaper when solar generation is high.",
            },
            {
                "period": "Evening peak",
                "start_hour": 16,
                "end_hour": 21,
                "price_eur_per_kwh": float(evening_peak_price),
                "interpretation": "High demand period; usually expensive.",
            },
            {
                "period": "Late evening",
                "start_hour": 21,
                "end_hour": 24,
                "price_eur_per_kwh": float(late_price),
                "interpretation": "Demand decreases after evening peak.",
            },
        ]
    )


def _price_for_hour(hour: float, price_table: pd.DataFrame) -> tuple[float, str]:
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
) -> tuple[pd.DataFrame, float]:
    """
    Calculates cost with time-of-day prices.

    Formulas:
    energy_mwh(t) = total_power_mw(t) × delta_seconds(t) / 3600
    energy_kwh(t) = energy_mwh(t) × 1000
    clock_hour(t) = simulation_start_hour + elapsed_time(t)
    cost(t) = energy_kwh(t) × price(clock_hour(t))
    total_cost = Σ cost(t)

    Delayed training does not reduce energy by itself. It changes the clock_hour(t)
    of the workload, so cost can change if the shifted work lands in cheaper or
    more expensive tariff periods.
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


def calculate_cost_projection(avg_power_mw: float, price_per_kwh: float):
    """Projection based on average power and a flat price."""
    avg_power_kw = avg_power_mw * 1000.0
    return {
        "1h_cost": avg_power_kw * 1 * price_per_kwh,
        "6h_cost": avg_power_kw * 6 * price_per_kwh,
        "24h_cost": avg_power_kw * 24 * price_per_kwh,
        "30d_cost": avg_power_kw * 24 * 30 * price_per_kwh,
    }
