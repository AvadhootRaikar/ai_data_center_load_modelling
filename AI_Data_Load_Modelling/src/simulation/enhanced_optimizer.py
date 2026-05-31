"""
Enhanced Optimization Strategies Module

Provides advanced optimization strategies including:
- Optimal PUE targeting and cooling efficiency improvements
- Time-of-use (ToU) based workload scheduling for cost/carbon reduction
- Smart data center utilization with predictive optimization
"""

import pandas as pd
import numpy as np


# Optimal PUE targets by data center cooling technology
OPTIMAL_PUE_TARGETS = {
    "baseline": 1.3,           # Traditional cooling
    "efficient": 1.2,          # Improved cooling efficiency
    "advanced": 1.1,           # Advanced liquid cooling
    "extreme": 1.05,           # Immersion or optimized cooling
}

# Carbon intensity by time of day (g CO2/kWh) - German grid average
CARBON_INTENSITY_PROFILE = {
    "00-06": 150,   # Night - coal backup
    "06-09": 140,   # Morning - gas plants
    "09-12": 100,   # Mid-morning - renewables + gas
    "12-15": 80,    # Afternoon - peak renewables
    "15-18": 120,   # Evening transition
    "18-21": 160,   # Evening - peak demand
    "21-00": 155,   # Late evening
}

# Time-of-use electricity pricing (EUR/kWh) - typical German rates
PRICING_PROFILE = {
    "00-06": 0.18,   # Cheap night rate
    "06-09": 0.25,   # Morning rate
    "09-12": 0.22,   # Mid-morning rate
    "12-15": 0.20,   # Afternoon rate
    "15-18": 0.24,   # Evening transition
    "18-21": 0.30,   # Peak rate
    "21-00": 0.28,   # Late evening rate
}


def calculate_optimal_pue(cooling_technology="efficient"):
    """
    Get optimal PUE for given cooling technology.
    
    Args:
        cooling_technology: Type of cooling (baseline, efficient, advanced, extreme)
        
    Returns:
        float: Optimal PUE value
    """
    return OPTIMAL_PUE_TARGETS.get(cooling_technology, 1.3)


def get_tou_price_for_time(hour):
    """
    Get time-of-use electricity price for given hour.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        float: Price in EUR/kWh
    """
    if 0 <= hour < 6:
        return PRICING_PROFILE["00-06"]
    elif 6 <= hour < 9:
        return PRICING_PROFILE["06-09"]
    elif 9 <= hour < 12:
        return PRICING_PROFILE["09-12"]
    elif 12 <= hour < 15:
        return PRICING_PROFILE["12-15"]
    elif 15 <= hour < 18:
        return PRICING_PROFILE["15-18"]
    elif 18 <= hour < 21:
        return PRICING_PROFILE["18-21"]
    else:
        return PRICING_PROFILE["21-00"]


def get_carbon_intensity_for_time(hour):
    """
    Get carbon intensity of grid for given hour.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        float: Carbon intensity in g CO2/kWh
    """
    if 0 <= hour < 6:
        return CARBON_INTENSITY_PROFILE["00-06"]
    elif 6 <= hour < 9:
        return CARBON_INTENSITY_PROFILE["06-09"]
    elif 9 <= hour < 12:
        return CARBON_INTENSITY_PROFILE["09-12"]
    elif 12 <= hour < 15:
        return CARBON_INTENSITY_PROFILE["12-15"]
    elif 15 <= hour < 18:
        return CARBON_INTENSITY_PROFILE["15-18"]
    elif 18 <= hour < 21:
        return CARBON_INTENSITY_PROFILE["18-21"]
    else:
        return CARBON_INTENSITY_PROFILE["21-00"]


def find_optimal_scheduling_window(profile, optimization_target="cost"):
    """
    Find optimal time window to schedule workload for cost or carbon minimization.
    
    Args:
        profile: DataFrame with workload profile
        optimization_target: "cost" or "carbon"
        
    Returns:
        dict: Contains best start hour, savings percentage, and details
    """
    if len(profile) == 0:
        return {"best_hour": 0, "savings_pct": 0.0, "metric": 0.0}
    
    workload_duration_hours = len(profile) / 3600 if "delta_seconds" not in profile.columns else profile["delta_seconds"].sum() / 3600
    total_energy = profile["total_power_mw"].sum() if "total_power_mw" in profile.columns else 0.0427
    
    best_hour = 0
    best_savings = 0.0
    baseline_metric = 0.0
    
    # Calculate baseline (worst case - peak hours 18-21)
    baseline_metric = total_energy * get_tou_price_for_time(18) * 1000 if optimization_target == "cost" else total_energy * get_carbon_intensity_for_time(18)
    
    # Find best hour to start
    for start_hour in range(24):
        metric_sum = 0.0
        for i in range(int(workload_duration_hours)):
            hour = (start_hour + i) % 24
            if optimization_target == "cost":
                metric_sum += get_tou_price_for_time(hour)
            else:  # carbon
                metric_sum += get_carbon_intensity_for_time(hour)
        
        avg_metric = metric_sum / max(1, int(workload_duration_hours))
        metric_cost = total_energy * avg_metric * (1000 if optimization_target == "cost" else 1)
        
        savings = baseline_metric - metric_cost
        if savings > best_savings:
            best_savings = savings
            best_hour = start_hour
    
    savings_pct = (best_savings / max(baseline_metric, 1e-9)) * 100 if baseline_metric > 0 else 0.0
    
    return {
        "best_hour": best_hour,
        "savings_pct": savings_pct,
        "baseline_metric": baseline_metric,
        "optimized_metric": baseline_metric - best_savings,
    }


def apply_smart_pue_optimization(profile, target_cooling="advanced"):
    """
    Apply smart PUE optimization based on cooling technology improvements.
    
    Args:
        profile: DataFrame with workload profile
        target_cooling: Target cooling technology level
        
    Returns:
        dict: Contains energy savings, PUE reduction, and optimization details
    """
    baseline_pue = OPTIMAL_PUE_TARGETS["baseline"]
    optimized_pue = OPTIMAL_PUE_TARGETS.get(target_cooling, baseline_pue)
    pue_reduction_factor = optimized_pue / baseline_pue
    
    if "total_power_mw" in profile.columns:
        baseline_energy = profile["total_power_mw"].sum() * 1e-6  # Convert to MWh approximately
        optimized_energy = baseline_energy * pue_reduction_factor
    else:
        baseline_energy = 0.0405
        optimized_energy = baseline_energy * pue_reduction_factor
    
    energy_savings = baseline_energy - optimized_energy
    energy_savings_pct = (energy_savings / max(baseline_energy, 1e-9)) * 100
    
    return {
        "baseline_pue": baseline_pue,
        "optimized_pue": optimized_pue,
        "energy_savings_mwh": energy_savings,
        "energy_savings_pct": energy_savings_pct,
        "cooling_technology": target_cooling,
    }


def calculate_combined_optimization(
    profile,
    gpu_power_factor=0.8,
    cooling_technology="advanced",
    optimize_scheduling="both",
):
    """
    Calculate combined optimization impact across multiple strategies.
    
    Args:
        profile: DataFrame with workload profile
        gpu_power_factor: GPU power limiting factor (0.0-1.0)
        cooling_technology: Target cooling technology
        optimize_scheduling: "cost", "carbon", "both", or "none"
        
    Returns:
        dict: Combined optimization results and recommendations
    """
    
    # GPU power optimization
    gpu_savings = (1.0 - gpu_power_factor) * 0.0405  # MWh savings
    gpu_savings_pct = (gpu_savings / 0.0405) * 100
    
    # PUE optimization
    pue_results = apply_smart_pue_optimization(profile, cooling_technology)
    
    # Scheduling optimization
    cost_scheduling = find_optimal_scheduling_window(profile, "cost") if optimize_scheduling in ["cost", "both"] else {"savings_pct": 0.0}
    carbon_scheduling = find_optimal_scheduling_window(profile, "carbon") if optimize_scheduling in ["carbon", "both"] else {"savings_pct": 0.0}
    
    # Calculate annual impact (365 days)
    annual_gpu_savings_eur = gpu_savings * 365 * 15.00 / 0.0405  # Proportional to energy savings
    annual_pue_savings_eur = pue_results["energy_savings_mwh"] * 365 * 15.00 / 0.0405
    annual_scheduling_savings_eur = (cost_scheduling["savings_pct"] / 100) * 15.00 * 365
    
    total_annual_savings = annual_gpu_savings_eur + annual_pue_savings_eur + annual_scheduling_savings_eur
    
    # Carbon impact (kg CO2e annually)
    baseline_annual_carbon = 6080 * 365  # kg CO2e
    gpu_carbon_reduction = baseline_annual_carbon * (gpu_savings_pct / 100)
    pue_carbon_reduction = baseline_annual_carbon * (pue_results["energy_savings_pct"] / 100)
    carbon_scheduling_reduction = baseline_annual_carbon * (carbon_scheduling["savings_pct"] / 100)
    
    total_annual_carbon_reduction = gpu_carbon_reduction + pue_carbon_reduction + carbon_scheduling_reduction
    
    return {
        "gpu_optimization": {
            "gpu_power_factor": gpu_power_factor,
            "energy_savings_pct": gpu_savings_pct,
            "annual_cost_savings_eur": annual_gpu_savings_eur,
            "annual_carbon_reduction_kg": gpu_carbon_reduction,
        },
        "pue_optimization": {
            "baseline_pue": pue_results["baseline_pue"],
            "optimized_pue": pue_results["optimized_pue"],
            "cooling_technology": cooling_technology,
            "energy_savings_pct": pue_results["energy_savings_pct"],
            "annual_cost_savings_eur": annual_pue_savings_eur,
            "annual_carbon_reduction_kg": pue_carbon_reduction,
        },
        "scheduling_optimization": {
            "cost_best_hour": cost_scheduling.get("best_hour", 0),
            "cost_savings_pct": cost_scheduling.get("savings_pct", 0.0),
            "carbon_best_hour": carbon_scheduling.get("best_hour", 0),
            "carbon_savings_pct": carbon_scheduling.get("savings_pct", 0.0),
            "annual_cost_savings_eur": annual_scheduling_savings_eur,
            "annual_carbon_reduction_kg": carbon_scheduling_reduction,
        },
        "combined_totals": {
            "total_annual_cost_savings_eur": total_annual_savings,
            "total_annual_carbon_reduction_kg": total_annual_carbon_reduction,
            "payback_months": total_annual_savings / 3 if total_annual_savings > 0 else float('inf'),
        }
    }
