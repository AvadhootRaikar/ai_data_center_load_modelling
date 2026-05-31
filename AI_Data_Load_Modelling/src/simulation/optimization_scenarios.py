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
    audit_notes = {
        "scenario": scenario,
        "gpu_power_factor": gpu_power_factor,
        "pue_factor": pue_factor,
        "delay_steps": delay_steps,
        "gpu_slowdown_sensitivity": gpu_slowdown_sensitivity,
        "account_for_runtime_slowdown": account_for_runtime_slowdown,
        "enable_load_balancing": enable_load_balancing,
        "summary": (
            f"Scenario: {scenario}\n"
            f"GPU Power Limiting: {(1-gpu_power_factor)*100:.0f}%\n"
            f"PUE Improvement: {(1-pue_factor)*100:.0f}%\n"
            f"Load Balancing: {'Enabled' if enable_load_balancing else 'Disabled'}\n"
            f"Energy Savings: {energy_savings_mwh:.4f} MWh ({energy_savings_pct:.1f}%)\n"
            f"Cost Savings: {cost_savings_eur:.2f} EUR\n"
            f"Carbon Reduction: {carbon_reduction_kg:.0f} kg CO2e"
        )
    }
    
    return audit_df, audit_notes
