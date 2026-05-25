"""
Carbon Intensity and Sustainability Analysis Module

Provides:
- Grid carbon intensity tracking
- Time-dependent CO2 emissions calculation
- Renewable energy profile integration
- Carbon footprint reduction metrics
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from datetime import datetime


def build_german_carbon_intensity_profile(
    night_intensity: float = 100,  # gCO2/kWh 00:00-06:00
    morning_intensity: float = 200,  # gCO2/kWh 06:00-10:00
    midday_intensity: float = 80,  # gCO2/kWh 10:00-16:00 (solar peak)
    evening_intensity: float = 250,  # gCO2/kWh 16:00-21:00 (peak demand)
    late_intensity: float = 120,  # gCO2/kWh 21:00-24:00
) -> pd.DataFrame:
    """
    Creates realistic German grid carbon intensity profile by time of day.
    
    German grid characteristics:
    - Higher renewables during midday (solar generation peak)
    - Lower at night (less peak demand, coal can ramp down)
    - Higher during evening peak (more gas/coal firing)
    
    Intensities are approximate 2025 German grid estimates.
    """
    return pd.DataFrame([
        {"period": "Night", "start_hour": 0, "end_hour": 6, "intensity_g_co2_per_kwh": float(night_intensity)},
        {"period": "Morning", "start_hour": 6, "end_hour": 10, "intensity_g_co2_per_kwh": float(morning_intensity)},
        {"period": "Midday/Solar", "start_hour": 10, "end_hour": 16, "intensity_g_co2_per_kwh": float(midday_intensity)},
        {"period": "Evening Peak", "start_hour": 16, "end_hour": 21, "intensity_g_co2_per_kwh": float(evening_intensity)},
        {"period": "Late", "start_hour": 21, "end_hour": 24, "intensity_g_co2_per_kwh": float(late_intensity)},
    ])


def _carbon_intensity_for_hour(
    hour: float,
    carbon_table: pd.DataFrame
) -> Tuple[float, str]:
    """Returns carbon intensity and period name for a given hour (0-24)."""
    hour = float(hour) % 24.0
    for _, row in carbon_table.iterrows():
        if float(row["start_hour"]) <= hour < float(row["end_hour"]):
            return float(row["intensity_g_co2_per_kwh"]), str(row["period"])
    # Fallback to last entry
    last = carbon_table.iloc[-1]
    return float(last["intensity_g_co2_per_kwh"]), str(last["period"])


def calculate_carbon_emissions(
    results_df: pd.DataFrame,
    carbon_intensity_table: Optional[pd.DataFrame] = None,
    simulation_start_hour: float = 12.0,
    constant_intensity: Optional[float] = None,
) -> Tuple[pd.DataFrame, float, pd.DataFrame]:
    """
    Calculates CO2 emissions for a simulation run.
    
    Parameters:
    -----------
    results_df : pd.DataFrame
        Simulation results with total_power_mw and delta_seconds columns
    carbon_intensity_table : pd.DataFrame or None
        Table with time-of-day carbon intensities
    simulation_start_hour : float
        Clock hour when simulation starts (for ToD carbon intensity lookup)
    constant_intensity : float or None
        If provided, uses constant carbon intensity instead of ToD
        
    Returns:
    --------
    results_df_with_carbon : pd.DataFrame
        Results with added carbon columns
    total_emissions_kg : float
        Total CO2 emissions in kg
    emissions_summary : pd.DataFrame
        Summary by period
    """
    if carbon_intensity_table is None:
        carbon_intensity_table = build_german_carbon_intensity_profile()
    
    df = results_df.copy()
    
    if "energy_mwh" not in df.columns:
        if "total_power_mw" not in df.columns or "delta_seconds" not in df.columns:
            raise ValueError("results_df must contain energy_mwh or total_power_mw + delta_seconds")
        df["energy_mwh"] = df["total_power_mw"] * df["delta_seconds"] / 3600.0
    
    df["energy_kwh"] = df["energy_mwh"] * 1000.0
    
    # Calculate carbon intensity for each timestep
    if constant_intensity is not None:
        df["carbon_intensity_g_per_kwh"] = float(constant_intensity)
        df["carbon_period"] = "Constant"
    else:
        df["carbon_intensity_g_per_kwh"] = df.apply(
            lambda row: _carbon_intensity_for_hour(
                simulation_start_hour + row.get("elapsed_hours", 0),
                carbon_intensity_table
            )[0],
            axis=1
        )
        df["carbon_period"] = df.apply(
            lambda row: _carbon_intensity_for_hour(
                simulation_start_hour + row.get("elapsed_hours", 0),
                carbon_intensity_table
            )[1],
            axis=1
        )
    
    # Calculate emissions
    df["co2_emissions_g"] = df["energy_kwh"] * df["carbon_intensity_g_per_kwh"]
    df["co2_emissions_kg"] = df["co2_emissions_g"] / 1000.0
    
    total_emissions_kg = float(df["co2_emissions_kg"].sum())
    
    # Summary by period
    if "carbon_period" in df.columns and df["carbon_period"].dtype == 'object':
        summary = df.groupby("carbon_period").agg({
            "energy_kwh": "sum",
            "co2_emissions_kg": "sum",
            "carbon_intensity_g_per_kwh": "mean",
        }).reset_index()
        summary.columns = ["period", "energy_kwh", "emissions_kg", "avg_intensity_g_per_kwh"]
    else:
        summary = pd.DataFrame()
    
    return df, total_emissions_kg, summary


def calculate_carbon_reduction_potential(
    baseline_emissions_kg: float,
    scenario_results: dict,  # {"scenario_name": (df, emissions_kg)}
) -> pd.DataFrame:
    """
    Calculates carbon reduction compared to baseline for each scenario.
    """
    reductions = []
    for scenario_name, (_, scenario_emissions_kg) in scenario_results.items():
        reduction_kg = baseline_emissions_kg - scenario_emissions_kg
        reduction_percent = (reduction_kg / baseline_emissions_kg * 100.0) if baseline_emissions_kg > 0 else 0
        reductions.append({
            "scenario": scenario_name,
            "baseline_emissions_kg": baseline_emissions_kg,
            "scenario_emissions_kg": scenario_emissions_kg,
            "reduction_kg": reduction_kg,
            "reduction_percent": reduction_percent,
        })
    
    return pd.DataFrame(reductions).sort_values("reduction_kg", ascending=False)


def estimate_renewable_energy_offset(
    total_energy_kwh: float,
    renewable_fraction: float = 0.5,
) -> dict:
    """
    Estimates offset by renewable energy sources.
    
    Parameters:
    -----------
    total_energy_kwh : float
        Total energy consumed
    renewable_fraction : float
        Fraction of grid from renewables (0-1)
        
    Returns:
    --------
    dict with renewable and non-renewable breakdowns
    """
    renewable_kwh = total_energy_kwh * renewable_fraction
    non_renewable_kwh = total_energy_kwh * (1 - renewable_fraction)
    
    # Approximate emissions from non-renewable sources
    # Using ~400 gCO2/kWh for non-renewable grid (coal/gas mix)
    non_renewable_emissions_kg = non_renewable_kwh * 0.4
    
    return {
        "total_energy_kwh": total_energy_kwh,
        "renewable_fraction": renewable_fraction,
        "renewable_energy_kwh": renewable_kwh,
        "non_renewable_energy_kwh": non_renewable_kwh,
        "emissions_from_renewables_kg": 0.0,  # Renewables have zero direct emissions
        "emissions_from_non_renewables_kg": non_renewable_emissions_kg,
        "total_operational_emissions_kg": non_renewable_emissions_kg,
        "renewable_offset_kg_co2": renewable_kwh * 0.4,  # Typical offset value
    }
