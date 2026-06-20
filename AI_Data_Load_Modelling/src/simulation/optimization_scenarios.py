"""
Optimization Scenarios Module

Implements optimization strategies including GPU power limiting, PUE improvements,
workload shifting, and data center load balancing for HPC energy efficiency analysis.
"""

import pandas as pd
import numpy as np


def apply_optimization_scenario(
    profile,
    scenario="baseline",
    gpu_power_factor=1.0,
    pue_factor=1.0,
    delay_steps=0,
    gpu_slowdown_sensitivity=1.0,
    account_for_runtime_slowdown=False,
    gpu_runtime_model=None,
):
    """
    Apply optimization scenario to a workload profile.
    
    Adjusts GPU power consumption based on limiting factors and PUE improvements.
    
    Args:
        profile: DataFrame with workload profile (gpu_power_w, delta_seconds, etc.)
        scenario: Optimization scenario name (baseline, gpu_limiting, pue_improvement, etc.)
        gpu_power_factor: Multiplier for GPU power (0.0-1.0)
        pue_factor: Power Usage Effectiveness multiplier
        delay_steps: Number of steps to delay workload
        gpu_slowdown_sensitivity: Sensitivity to performance slowdown
        account_for_runtime_slowdown: Whether to account for runtime slowdown
        gpu_runtime_model: Runtime model for performance impact
        
    Returns:
        DataFrame: Optimized profile with adjusted power values
    """
    optimized = profile.copy()
    
    # Apply GPU power limiting
    if "gpu_power_w" in optimized.columns and gpu_power_factor != 1.0:
        optimized["gpu_power_w"] = optimized["gpu_power_w"] * gpu_power_factor
    
    # Apply PUE factor adjustment
    if "total_power_mw" in optimized.columns and pue_factor != 1.0:
        optimized["total_power_mw"] = optimized["total_power_mw"] * pue_factor
    
    # Apply delay if specified
    if delay_steps > 0 and len(optimized) > delay_steps:
        # Shift the profile forward
        optimized["elapsed_hours"] = optimized["elapsed_hours"].shift(delay_steps).fillna(0)
    
    return optimized


def apply_center_level_load_balancing(
    profile,
    number_of_centers=3,
    max_active_centers=None,
    strategy="round_robin",
):
    """
    Apply load balancing across multiple data centers.
    
    Distributes workload across data centers to optimize resource utilization.
    
    Args:
        profile: DataFrame with workload profile
        number_of_centers: Total number of data centers available
        max_active_centers: Maximum number of centers to use simultaneously
        strategy: Load balancing strategy (round_robin, least_loaded, random)
        
    Returns:
        DataFrame: Load-balanced profile
    """
    balanced = profile.copy()
    
    if max_active_centers is None:
        max_active_centers = number_of_centers
    
    # Apply load balancing by distributing power across centers
    if max_active_centers > 0 and number_of_centers > 0:
        distribution_factor = min(max_active_centers, number_of_centers) / number_of_centers
        
        if "total_power_mw" in balanced.columns:
            balanced["total_power_mw"] = balanced["total_power_mw"] * distribution_factor
        if "gpu_power_w" in balanced.columns:
            balanced["gpu_power_w"] = balanced["gpu_power_w"] * distribution_factor
    
    return balanced


def build_optimization_audit(
    baseline_energy_mwh,
    optimized_energy_mwh,
    baseline_projection,
    optimized_projection,
    scenario,
    optimized_profile,
    gpu_power_factor,
    gpu_slowdown_sensitivity,
    account_for_runtime_slowdown,
    pue_factor,
    delay_steps,
    enable_load_balancing,
    **kwargs
):
    """
    Build audit trail comparing baseline vs optimized scenarios.
    
    Creates detailed audit information for transparency and analysis.
    
    Args:
        baseline_energy_mwh: Baseline energy consumption
        optimized_energy_mwh: Optimized energy consumption
        baseline_projection: Baseline cost/carbon projections
        optimized_projection: Optimized cost/carbon projections
        scenario: Scenario name
        optimized_profile: Optimized workload profile
        gpu_power_factor: GPU power limiting factor applied
        gpu_slowdown_sensitivity: Slowdown sensitivity parameter
        account_for_runtime_slowdown: Whether slowdown was accounted for
        pue_factor: PUE improvement factor applied
        delay_steps: Number of delay steps applied
        enable_load_balancing: Whether load balancing was applied
        **kwargs: Additional parameters
        
    Returns:
        tuple: (audit_df, audit_notes) where audit_df is DataFrame with audit records
               and audit_notes is dict with descriptive notes
    """
    
    # Calculate metrics
    energy_savings_mwh = baseline_energy_mwh - optimized_energy_mwh
    energy_savings_pct = (energy_savings_mwh / max(baseline_energy_mwh, 1e-9)) * 100
    
    cost_savings_eur = (baseline_projection.get("annual_cost_eur", 0) - 
                       optimized_projection.get("annual_cost_eur", 0))
    carbon_reduction_kg = (baseline_projection.get("annual_carbon_kg", 0) - 
                           optimized_projection.get("annual_carbon_kg", 0))
    
    # Build audit dataframe
    audit_data = {
        "Metric": [
            "Baseline Energy",
            "Optimized Energy",
            "Energy Savings",
            "Energy Savings %",
            "Baseline Cost",
            "Optimized Cost",
            "Cost Savings",
            "Baseline Carbon",
            "Optimized Carbon",
            "Carbon Reduction",
        ],
        "Value": [
            f"{baseline_energy_mwh:.4f} MWh",
            f"{optimized_energy_mwh:.4f} MWh",
            f"{energy_savings_mwh:.4f} MWh",
            f"{energy_savings_pct:.1f}%",
            f"{baseline_projection.get('annual_cost_eur', 0):.2f} EUR",
            f"{optimized_projection.get('annual_cost_eur', 0):.2f} EUR",
            f"{cost_savings_eur:.2f} EUR",
            f"{baseline_projection.get('annual_carbon_kg', 0):.0f} kg CO2e",
            f"{optimized_projection.get('annual_carbon_kg', 0):.0f} kg CO2e",
            f"{carbon_reduction_kg:.0f} kg CO2e",
        ],
    }
    
    audit_df = pd.DataFrame(audit_data)
    
    # Build audit notes
    gpu_limit_pct = (1-gpu_power_factor)*100
    pue_improvement_pct = (1-pue_factor)*100
    
    # Determine formula description
    if gpu_power_factor < 1.0:
        formula = f"GPU power capped to {gpu_power_factor*100:.0f}% of baseline"
    elif pue_factor < 1.0:
        formula = f"PUE improved from 1.3 to {1.3*pue_factor:.2f}"
    elif enable_load_balancing:
        formula = "Load balancing across data centers with dynamic scaling"
    else:
        formula = "Workload timing optimization based on grid pricing signals"
    
    audit_notes = {
        "scenario": scenario,
        "formula": formula,
        "gpu_power_factor": gpu_power_factor,
        "pue_factor": pue_factor,
        "delay_steps": delay_steps,
        "gpu_slowdown_sensitivity": gpu_slowdown_sensitivity,
        "account_for_runtime_slowdown": account_for_runtime_slowdown,
        "enable_load_balancing": enable_load_balancing,
        "performance_model": "GPU utilization-based" if account_for_runtime_slowdown else "not active",
        "summary": (
            f"Scenario: {scenario}\n"
            f"GPU Power Limiting: {gpu_limit_pct:.0f}%\n"
            f"PUE Improvement: {pue_improvement_pct:.0f}%\n"
            f"Load Balancing: {'Enabled' if enable_load_balancing else 'Disabled'}\n"
            f"Energy Savings: {energy_savings_mwh:.4f} MWh ({energy_savings_pct:.1f}%)\n"
            f"Cost Savings: {cost_savings_eur:.2f} EUR\n"
            f"Carbon Reduction: {carbon_reduction_kg:.0f} kg CO2e"
        )
    }
    
    return audit_df, audit_notes


def apply_thermal_aware_scheduling(
    profile,
    ambient_temps_celsius,
    price_series,
    carbon_series,
    cooling_type="wet",
    baseline_pue=1.3,
):
    """
    Apply thermal-aware scheduling optimization to minimize cost and carbon simultaneously.
    
    This scenario combines three optimization drivers:
    1. Cooling Efficiency: Run workloads during cooler hours (lower PUE)
    2. Cost Efficiency: Run workloads during low-price hours (EPEX SPOT/SMARD)
    3. Carbon Efficiency: Run workloads during low-carbon hours (SMARD)
    
    Physics:
    - Higher ambient temperature → higher PUE (more cooling energy)
    - Cooling consumes 10-30% of total facility power
    - Water cooling is most efficient at cooler temperatures
    
    Args:
        profile: DataFrame with power profile (gpu_power_w, delta_seconds, etc.)
        ambient_temps_celsius: Series of 24-hour ambient temperatures
        price_series: Series of 24-hour electricity prices (EUR/kWh)
        carbon_series: Series of 24-hour carbon intensity (g CO2/kWh)
        cooling_type: "wet" or "dry" cooling
        baseline_pue: Reference PUE at 20°C (typically 1.25-1.50)
    
    Returns:
        tuple: (optimized_profile, recommendations) where recommendations contains
               best hours to run workloads
    """
    from .water_cooling_model import (
        calculate_dynamic_pue,
        calculate_water_usage,
        get_thermal_aware_scheduling_recommendations,
    )
    
    # Enrich profile with water/cooling metrics
    enriched_profile = profile.copy()
    
    # Calculate dynamic PUE for each hour
    dynamic_pues = []
    cooling_power_list = []
    water_usage_list = []
    
    gpu_power_kw = profile.get("gpu_power_w", pd.Series([0] * len(profile))) / 1000.0
    cpu_power_kw = profile.get("cpu_power_w", pd.Series([0] * len(profile))) / 1000.0 if "cpu_power_w" in profile.columns else gpu_power_kw * 0.2
    it_power_kw = gpu_power_kw + cpu_power_kw
    
    for idx in range(len(profile)):
        ambient_temp = ambient_temps_celsius.iloc[idx] if isinstance(ambient_temps_celsius, pd.Series) else 20.0
        workload = (gpu_power_kw.iloc[idx] / gpu_power_kw.max()) if gpu_power_kw.max() > 0 else 0
        
        # Dynamic PUE based on temperature and workload
        pue = calculate_dynamic_pue(
            ambient_temp_celsius=ambient_temp,
            baseline_pue=baseline_pue,
            workload_intensity=workload
        )
        dynamic_pues.append(pue)
        
        # Cooling power = (IT Power × PUE) - IT Power
        total_facility_kw = it_power_kw.iloc[idx] * pue
        cooling_kw = total_facility_kw - it_power_kw.iloc[idx]
        cooling_power_list.append(cooling_kw)
        
        # Water usage
        water_lps, _ = calculate_water_usage(
            gpu_power_kw=gpu_power_kw.iloc[idx],
            cpu_power_kw=cpu_power_kw.iloc[idx],
            cooling_type=cooling_type,
            ambient_temp_celsius=ambient_temp,
        )
        water_usage_list.append(water_lps)
    
    enriched_profile["dynamic_pue"] = dynamic_pues
    enriched_profile["cooling_power_kw"] = cooling_power_list
    enriched_profile["water_usage_lps"] = water_usage_list
    
    # Get recommendations
    recommendations = get_thermal_aware_scheduling_recommendations(
        profile_df=enriched_profile,
        ambient_temp_series=ambient_temps_celsius,
        price_series=price_series,
        carbon_series=carbon_series,
    )
    
    # Apply optimization: scale down power during non-optimal hours
    optimized = enriched_profile.copy()
    worst_hours = set(recommendations["avoid_hours"])
    
    for col in ["gpu_power_w", "cpu_power_w"]:
        if col in optimized.columns:
            # Reduce power by 30% during worst hours, maintain during best hours
            optimized[col] = optimized[col].apply(
                lambda x: x * 0.7 if optimized.index.tolist().index(optimized[optimized[col] == x].index[0]) in worst_hours else x
            )
    
    return optimized, recommendations


def get_scenario_list():
    """
    Returns available optimization scenarios and their descriptions.
    
    Returns:
        Dict: Scenario names and descriptions
    """
    return {
        "baseline": "No optimization - reference case",
        "gpu_limiting": "Reduce GPU frequency/power (5-50% reduction)",
        "pue_improvement": "Improve cooling efficiency (PUE -2-8%)",
        "time_shifting": "Shift workload to low-price/low-carbon hours",
        "load_balancing": "Distribute load across multiple data centers",
        "smart_scheduling": "Combine time-shifting and load balancing",
        "renewable_alignment": "Run during high renewable generation",
        "thermal_aware": "Optimize for temperature + cost + carbon simultaneously",
        "water_efficient": "Minimize water consumption (dry cooling emphasis)",
        "multi_strategy": "Combined GPU limiting + PUE + scheduling",
    }
