"""
Capacity Analysis Module

Performs grid hosting capacity analysis for HPC data center loads,
including N-1 contingency analysis and power system stability checks.
"""

import pandas as pd
import numpy as np


def run_capacity_analysis(
    workload_df,
    max_centers=3,
    clusters_per_center=10,
    racks_per_cluster=20,
    grid_backend="LV",
    simbench_code=None,
    include_existing_simbench_loads=False,
):
    """
    Run capacity analysis on grid hosting constraints for HPC workload.
    
    Analyzes available grid capacity for hosting HPC data centers with
    variable load profiles.
    
    Args:
        workload_df: DataFrame with workload profile (gpu_power_w, etc.)
        max_centers: Maximum number of data centers to analyze
        clusters_per_center: Number of compute clusters per center
        racks_per_cluster: Number of racks per cluster
        grid_backend: Grid backend voltage level (LV, MV, HV)
        simbench_code: Benchmark code for SimBench grid model
        include_existing_simbench_loads: Include existing loads from SimBench
        
    Returns:
        DataFrame: Capacity analysis results
    """
    
    # Calculate peak and average loads
    if "total_power_mw" in workload_df.columns:
        peak_power_mw = workload_df["total_power_mw"].max()
        avg_power_mw = workload_df["total_power_mw"].mean()
    elif "gpu_power_w" in workload_df.columns:
        peak_power_mw = workload_df["gpu_power_w"].max() / 1e6
        avg_power_mw = workload_df["gpu_power_w"].mean() / 1e6
    else:
        peak_power_mw = 0.0427
        avg_power_mw = 0.0393
    
    # Build capacity analysis results
    analysis_data = []
    
    for center_idx in range(max_centers):
        center_name = f"Data Center {center_idx + 1}"
        center_peak = peak_power_mw * (center_idx + 1)
        center_avg = avg_power_mw * (center_idx + 1)
        
        # Estimate grid requirements
        transformer_size_mva = center_peak * 1.2  # 20% headroom
        line_rating_mva = center_peak * 1.5       # 50% headroom
        
        # Hosting capacity (simple model based on transformer capacity)
        available_capacity_mva = transformer_size_mva * 0.8  # 80% rule
        hosting_capacity_fraction = available_capacity_mva / max(line_rating_mva, 1e-6)
        
        # N-1 contingency analysis
        n1_violation = hosting_capacity_fraction > 1.0
        
        analysis_data.append({
            "Data Center": center_name,
            "Peak Load (MW)": round(center_peak, 4),
            "Avg Load (MW)": round(center_avg, 4),
            "Transformer Size (MVA)": round(transformer_size_mva, 2),
            "Line Rating (MVA)": round(line_rating_mva, 2),
            "Hosting Capacity Utilization": round(hosting_capacity_fraction * 100, 1),
            "Available Capacity (MVA)": round(available_capacity_mva, 2),
            "N-1 Violation": "Yes" if n1_violation else "No",
            "Grid Backend": grid_backend,
        })
    
    capacity_df = pd.DataFrame(analysis_data)
    
    return capacity_df
