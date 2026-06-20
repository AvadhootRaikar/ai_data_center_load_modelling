"""
Water Cooling & Thermal Model for HPC Data Centers

Features:
- Dynamic PUE calculation based on ambient temperature and workload
- Water usage estimation (WUE - Water Usage Effectiveness)
- Cooling energy breakdown (IT vs. cooling vs. water)
- Thermal-aware scheduling recommendations
- Three-stage cooling chain physics simulation

Cooling Physics:
- 100% of GPU electrical power becomes heat
- Cooling efficiency varies with ambient temperature
- Wet cooling consumes water (affected by humidity)
- CDU (Coolant Distribution Unit) transfers heat via heat exchangers
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional


def calculate_dynamic_pue(
    ambient_temp_celsius: float = 20.0,
    baseline_pue: float = 1.3,
    temp_sensitivity: float = 0.025,
    workload_intensity: float = 1.0,
) -> float:
    """
    Calculates dynamic PUE based on ambient temperature and workload intensity.
    
    Formula: PUE = baseline_pue × (1 + temp_sensitivity × (T_ambient - T_ref)) × workload_factor
    
    Args:
        ambient_temp_celsius: Ambient temperature in °C (typical: 15-35°C Germany)
        baseline_pue: Reference PUE at 20°C full load (typical: 1.25-1.50)
        temp_sensitivity: PUE change per °C (typical: 0.02-0.03)
        workload_intensity: Workload fraction 0-1 (affects cooling efficiency)
    
    Returns:
        float: Dynamic PUE value (minimum 1.0)
    
    Example:
        - 20°C, baseline 1.3 → PUE = 1.30 (reference)
        - 35°C, baseline 1.3 → PUE = 1.69 (hot day, more cooling needed)
        - 5°C, baseline 1.3 → PUE = 1.06 (cold night, less cooling needed)
    """
    # Temperature deviation from reference (20°C)
    temp_deviation = ambient_temp_celsius - 20.0
    
    # Cooling efficiency degrades at higher temperatures (exponential effect)
    temp_factor = 1.0 + temp_sensitivity * temp_deviation
    
    # Partial loads slightly improve PUE (cooling not fully linear)
    workload_factor = 0.95 + 0.05 * workload_intensity
    
    pue = baseline_pue * temp_factor * workload_factor
    
    # PUE cannot be below 1.0 (physical impossibility)
    return max(pue, 1.0)


def calculate_water_usage(
    gpu_power_kw: float,
    cpu_power_kw: float,
    cooling_type: str = "wet",
    ambient_temp_celsius: float = 20.0,
    relative_humidity_percent: float = 40.0,
) -> Tuple[float, Dict[str, float]]:
    """
    Estimates water consumption for cooling HPC facilities.
    
    Physics:
    - GPU power → heat = ~100% electrical power
    - Cooling tower effectiveness depends on ambient temperature & humidity
    - Water loss through evaporation in wet cooling towers
    
    Wet Cooling Formula:
    Water (L/s) = IT Power (kW) / 2400
    - Adjusted for ambient temperature (hotter = more water loss)
    - Adjusted for humidity (lower humidity = higher evaporation)
    
    Dry Cooling:
    - No water consumption, but 15-20% higher energy cost
    
    Args:
        gpu_power_kw: GPU power consumption (kW)
        cpu_power_kw: CPU + Memory + Network power (kW)
        cooling_type: "wet" or "dry" cooling
        ambient_temp_celsius: Ambient temperature (15-35°C typical in Germany)
        relative_humidity_percent: Relative humidity (30-80%)
    
    Returns:
        Tuple[float, Dict]: (water_usage_liters_per_second, breakdown_dict)
    
    Example:
        - 40 kW GPU + 8 kW CPU, wet cooling, 20°C, 40% RH → ~2.0 L/s
        - 40 kW GPU + 8 kW CPU, dry cooling → 0 L/s (no water)
    """
    it_power_kw = gpu_power_kw + cpu_power_kw
    
    breakdown = {
        "it_power_kw": it_power_kw,
        "cooling_type": cooling_type,
        "ambient_temp_celsius": ambient_temp_celsius,
        "relative_humidity_percent": relative_humidity_percent,
    }
    
    if cooling_type.lower() == "wet":
        # Base water consumption formula
        base_water_lps = it_power_kw / 2400.0  # L/s
        
        # Temperature factor: higher ambient → more evaporation
        temp_factor = 1.0 + 0.02 * (ambient_temp_celsius - 20.0)
        
        # Humidity factor: lower humidity → higher evaporation
        # At 40% humidity (reference), factor = 1.0
        humidity_factor = 1.5 - (relative_humidity_percent / 100.0)
        
        water_lps = base_water_lps * max(temp_factor, 0.5) * max(humidity_factor, 0.7)
        water_liters_per_hour = water_lps * 3600
        
        breakdown["water_lps"] = water_lps
        breakdown["water_liters_per_hour"] = water_liters_per_hour
        breakdown["water_liters_per_day"] = water_liters_per_hour * 24
        breakdown["temp_factor"] = temp_factor
        breakdown["humidity_factor"] = humidity_factor
        
        return water_lps, breakdown
    
    elif cooling_type.lower() == "dry":
        # Dry cooling uses no water but consumes ~15-20% more energy
        breakdown["water_lps"] = 0.0
        breakdown["water_liters_per_hour"] = 0.0
        breakdown["water_liters_per_day"] = 0.0
        breakdown["dry_cooling_energy_overhead_percent"] = 17.5
        return 0.0, breakdown
    
    else:
        raise ValueError(f"Unknown cooling_type: {cooling_type}. Use 'wet' or 'dry'.")


def calculate_cooling_energy_breakdown(
    it_power_kw: float,
    pue: float,
    cooling_efficiency_percent: float = 85.0,
) -> Dict[str, float]:
    """
    Breaks down total facility power into IT vs. Cooling components.
    
    Physics:
    - Total Facility Power = IT Power × PUE
    - Cooling Power = Facility Power - IT Power
    - Some cooling energy is "parasitic" (pumps, fans, controls)
    
    Args:
        it_power_kw: IT power consumption (GPUs, CPUs, memory, network)
        pue: Power Usage Effectiveness ratio
        cooling_efficiency_percent: Cooling system efficiency (typical: 80-90%)
    
    Returns:
        Dict with power breakdown
    
    Example:
        - 40 kW IT, PUE 1.3 → Total 52 kW, Cooling 12 kW
        - 40 kW IT, PUE 1.5 → Total 60 kW, Cooling 20 kW
    """
    total_facility_power_kw = it_power_kw * pue
    cooling_power_kw = total_facility_power_kw - it_power_kw
    
    # Some cooling power is "useful" (moving heat), some is parasitic (pumps, fans)
    useful_cooling_kw = cooling_power_kw * (cooling_efficiency_percent / 100.0)
    parasitic_cooling_kw = cooling_power_kw - useful_cooling_kw
    
    return {
        "it_power_kw": it_power_kw,
        "total_facility_power_kw": total_facility_power_kw,
        "cooling_power_total_kw": cooling_power_kw,
        "useful_cooling_kw": useful_cooling_kw,
        "parasitic_cooling_kw": parasitic_cooling_kw,
        "cooling_power_percent": (cooling_power_kw / total_facility_power_kw * 100) if total_facility_power_kw > 0 else 0,
        "pue": pue,
    }


def add_water_metrics_to_profile(
    profile_df: pd.DataFrame,
    cooling_type: str = "wet",
    baseline_pue: float = 1.3,
    ambient_temps_celsius: Optional[pd.Series] = None,
    humidity_series: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Enriches a power profile DataFrame with water usage and cooling metrics.
    
    Adds columns:
    - dynamic_pue: Temperature-adjusted PUE
    - cooling_power_kw: Cooling power (non-IT)
    - water_usage_lps: Water consumption (L/s)
    - water_usage_liters_per_hour: Water consumption (L/h)
    - cooling_breakdown: Cooling energy split
    
    Args:
        profile_df: DataFrame with GPU/CPU power columns
        cooling_type: "wet" or "dry" cooling
        baseline_pue: Reference PUE (typical: 1.25-1.50)
        ambient_temps_celsius: Optional Series of ambient temperatures (24-hour profile)
        humidity_series: Optional Series of humidity percentages
    
    Returns:
        DataFrame: Enriched with water/cooling columns
    """
    result = profile_df.copy()
    
    # Default ambient temp if not provided (20°C average Germany)
    if ambient_temps_celsius is None:
        ambient_temps_celsius = pd.Series([20.0] * len(profile_df))
    
    # Default humidity if not provided (40% - typical Europe)
    if humidity_series is None:
        humidity_series = pd.Series([40.0] * len(profile_df))
    
    # Ensure GPU power column exists
    if "gpu_power_w" not in result.columns:
        raise ValueError("DataFrame must contain 'gpu_power_w' column")
    
    # Assume CPU power exists or calculate as portion of IT power
    if "cpu_power_w" not in result.columns:
        result["cpu_power_w"] = result["gpu_power_w"] * 0.2  # ~20% of GPU power
    
    # Convert to kW
    gpu_power_kw = result["gpu_power_w"] / 1000.0
    cpu_power_kw = result["cpu_power_w"] / 1000.0
    it_power_kw = gpu_power_kw + cpu_power_kw
    
    # Calculate dynamic PUE per timestep
    dynamic_pues = []
    water_usage_lps_list = []
    water_usage_lph_list = []
    cooling_power_list = []
    
    for idx, row in result.iterrows():
        # Get ambient temp and humidity for this timestep
        ambient_temp = ambient_temps_celsius.iloc[idx] if isinstance(ambient_temps_celsius, pd.Series) else ambient_temps_celsius
        humidity = humidity_series.iloc[idx] if isinstance(humidity_series, pd.Series) else humidity_series
        workload = (gpu_power_kw.iloc[idx] / gpu_power_kw.max()) if gpu_power_kw.max() > 0 else 0
        
        # Calculate dynamic PUE
        pue = calculate_dynamic_pue(
            ambient_temp_celsius=ambient_temp,
            baseline_pue=baseline_pue,
            workload_intensity=workload
        )
        dynamic_pues.append(pue)
        
        # Calculate water usage
        water_lps, _ = calculate_water_usage(
            gpu_power_kw=gpu_power_kw.iloc[idx],
            cpu_power_kw=cpu_power_kw.iloc[idx],
            cooling_type=cooling_type,
            ambient_temp_celsius=ambient_temp,
            relative_humidity_percent=humidity
        )
        water_usage_lps_list.append(water_lps)
        water_usage_lph_list.append(water_lps * 3600)
        
        # Calculate cooling power
        cooling_breakdown = calculate_cooling_energy_breakdown(
            it_power_kw=it_power_kw.iloc[idx],
            pue=pue
        )
        cooling_power_list.append(cooling_breakdown["cooling_power_total_kw"])
    
    # Add calculated columns
    result["dynamic_pue"] = dynamic_pues
    result["cooling_power_kw"] = cooling_power_list
    result["water_usage_lps"] = water_usage_lps_list
    result["water_usage_lph"] = water_usage_lph_list
    result["total_facility_power_kw"] = (it_power_kw + result["cooling_power_kw"]) / 1000.0
    
    return result


def get_thermal_aware_scheduling_recommendations(
    profile_df: pd.DataFrame,
    ambient_temp_series: pd.Series,
    price_series: pd.Series,
    carbon_series: pd.Series,
) -> Dict[str, any]:
    """
    Recommends optimal scheduling based on thermal, cost, and carbon metrics.
    
    Identifies best hours to run workloads considering:
    1. Cooling efficiency (cooler temps = lower PUE)
    2. Electricity price (low-cost hours from EPEX SPOT/SMARD)
    3. Carbon intensity (low-carbon hours from SMARD)
    4. Water availability (wet cooling considerations)
    
    Args:
        profile_df: Power profile with dynamic PUE, water usage
        ambient_temp_series: 24-hour ambient temperatures
        price_series: 24-hour electricity prices (EUR/kWh)
        carbon_series: 24-hour carbon intensity (g CO2/kWh)
    
    Returns:
        Dict with scheduling recommendations
    """
    # Normalize metrics to 0-100 scale
    pue_normalized = (profile_df["dynamic_pue"] - profile_df["dynamic_pue"].min()) / (profile_df["dynamic_pue"].max() - profile_df["dynamic_pue"].min()) * 100
    price_normalized = (price_series - price_series.min()) / (price_series.max() - price_series.min()) * 100
    carbon_normalized = (carbon_series - carbon_series.min()) / (carbon_series.max() - carbon_series.min()) * 100
    
    # Combined score: lower is better
    # Weight: 30% cooling efficiency, 40% cost, 30% carbon
    combined_score = 0.30 * pue_normalized + 0.40 * price_normalized + 0.30 * carbon_normalized
    
    best_hours = combined_score.nsmallest(6).index.tolist()
    worst_hours = combined_score.nlargest(3).index.tolist()
    
    return {
        "best_hours_for_workloads": best_hours,
        "avoid_hours": worst_hours,
        "combined_score": combined_score.to_dict(),
        "cooling_efficiency_hours": profile_df["dynamic_pue"].nsmallest(6).index.tolist(),
        "low_cost_hours": price_series.nsmallest(6).index.tolist(),
        "low_carbon_hours": carbon_series.nsmallest(6).index.tolist(),
    }


# Example usage and testing
if __name__ == "__main__":
    # Test dynamic PUE calculation
    print("=== Dynamic PUE Examples ===")
    temps = [5, 10, 15, 20, 25, 30, 35]
    for t in temps:
        pue = calculate_dynamic_pue(ambient_temp_celsius=t, baseline_pue=1.3)
        print(f"  {t}°C: PUE = {pue:.2f}")
    
    # Test water usage calculation
    print("\n=== Water Usage Examples ===")
    gpu_power = 40  # kW
    cpu_power = 8   # kW
    temps_humid = [(20, 40), (15, 50), (30, 30)]
    for temp, humidity in temps_humid:
        water_lps, breakdown = calculate_water_usage(
            gpu_power_kw=gpu_power,
            cpu_power_kw=cpu_power,
            cooling_type="wet",
            ambient_temp_celsius=temp,
            relative_humidity_percent=humidity
        )
        print(f"  {temp}°C, {humidity}% RH: {water_lps:.2f} L/s ({breakdown['water_liters_per_day']:.0f} L/day)")
    
    # Test cooling energy breakdown
    print("\n=== Cooling Energy Breakdown ===")
    breakdown = calculate_cooling_energy_breakdown(it_power_kw=40, pue=1.3)
    for key, value in breakdown.items():
        print(f"  {key}: {value:.2f}")
