"""
Enhanced Power Model with Dynamic PUE and Utilization-Based CPU/Memory Behavior

Features:
- Dynamic CPU/Memory power scaling based on utilization
- Environmental temperature-dependent cooling efficiency
- Configurable PUE with dynamic overhead modeling
- Node-to-center-to-facility power transformation
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


def calculate_dynamic_cpu_power(
    cpu_util_percent: pd.Series,
    base_cpu_power: float = 150.0,
    idle_power_ratio: float = 0.3,
) -> pd.Series:
    """
    Calculates CPU power based on utilization with idle baseline.
    
    Formula: cpu_power = base_cpu_power × (idle_ratio + (1 - idle_ratio) × cpu_util / 100)
    This models: CPU consumption proportional to workload above idle baseline.
    """
    cpu_util_percent = cpu_util_percent.clip(0, 100)
    return base_cpu_power * (idle_power_ratio + (1 - idle_power_ratio) * cpu_util_percent / 100.0)


def calculate_memory_power(
    gpu_util_percent: pd.Series,
    cpu_util_percent: pd.Series,
    base_memory_power: float = 40.0,
    idle_power_ratio: float = 0.5,
) -> pd.Series:
    """
    Calculates Memory power based on GPU and CPU utilization.
    
    Memory activity correlates with both GPU and CPU workload.
    Uses average utilization for more realistic behavior.
    """
    avg_util = (gpu_util_percent + cpu_util_percent) / 2.0
    avg_util = avg_util.clip(0, 100)
    return base_memory_power * (idle_power_ratio + (1 - idle_power_ratio) * avg_util / 100.0)


def calculate_environmental_pue(
    ambient_temp_celsius: float = 20.0,
    baseline_pue: float = 1.3,
    temp_efficiency_factor: float = 0.02,
) -> float:
    """
    Calculates PUE adjusted for ambient temperature.
    
    Formula: pue = baseline_pue × (1 + temp_efficiency_factor × (ambient_temp - 20))
    - Higher ambient temperature increases cooling load
    - This models: cooling efficiency degradation at higher temperatures
    """
    temp_deviation = ambient_temp_celsius - 20.0  # Reference is 20°C
    pue = baseline_pue * (1.0 + temp_efficiency_factor * temp_deviation)
    return max(pue, 1.0)  # PUE cannot be below 1.0


def convert_training_profile_to_center(
    profile_df: pd.DataFrame,
    nodes_per_center: int,
    cpu_power_per_node: float = 150.0,
    ram_power_per_node: float = 40.0,
    storage_power_per_node: float = 10.0,
    network_power_per_node: float = 10.0,
    pue: float = 1.3,
    dynamic_cpu_power: bool = True,
    dynamic_memory_power: bool = True,
    ambient_temp_celsius: Optional[float] = None,
    dynamic_pue: bool = False,
) -> pd.DataFrame:
    """
    Enhanced version that converts GPU profile to facility-level power demand.

    Important columns:
    - center_it_power_w: useful IT workload power (GPU + CPU + Memory + Storage + Network)
    - center_overhead_power_w: cooling/infrastructure overhead from PUE
    - center_total_power_w: IT + overhead
    - center_total_power_mw: converted to MW for pandapower

    Parameters:
    -----------
    dynamic_cpu_power : bool
        If True, scale CPU power based on CPU utilization
    dynamic_memory_power : bool
        If True, scale Memory power based on utilization
    ambient_temp_celsius : float or None
        Ambient temperature for environmental PUE adjustment
    dynamic_pue : bool
        If True, adjust PUE based on temperature; if False, use constant PUE
    """
    df = profile_df.copy()

    # Calculate CPU power (dynamic or static)
    if dynamic_cpu_power and "cpu_util_percent" in df.columns:
        cpu_power = calculate_dynamic_cpu_power(df["cpu_util_percent"], cpu_power_per_node)
    else:
        cpu_power = cpu_power_per_node

    # Calculate Memory power (dynamic or static)
    if dynamic_memory_power and "gpu_util_percent" in df.columns and "cpu_util_percent" in df.columns:
        memory_power = calculate_memory_power(
            df["gpu_util_percent"],
            df.get("cpu_util_percent", pd.Series(50.0, index=df.index)),
            ram_power_per_node,
        )
    else:
        memory_power = ram_power_per_node

    # Node-level power
    df["cpu_power_w"] = cpu_power if isinstance(cpu_power, pd.Series) else pd.Series([cpu_power] * len(df), index=df.index)
    df["memory_power_w"] = memory_power if isinstance(memory_power, pd.Series) else pd.Series([memory_power] * len(df), index=df.index)
    
    df["node_power_w"] = (
        df["gpu_power_w"]
        + df["cpu_power_w"]
        + df["memory_power_w"]
        + storage_power_per_node
        + network_power_per_node
    )

    # Center IT power
    df["center_it_power_w"] = df["node_power_w"] * nodes_per_center
    
    # Calculate PUE
    if dynamic_pue and ambient_temp_celsius is not None:
        df["pue"] = calculate_environmental_pue(ambient_temp_celsius, pue)
    else:
        df["pue"] = float(pue)
    
    df["baseline_pue"] = float(pue)

    # Center total power
    df["center_total_power_w"] = df["center_it_power_w"] * df["pue"]
    df["center_overhead_power_w"] = df["center_total_power_w"] - df["center_it_power_w"]
    df["center_total_power_mw"] = df["center_total_power_w"] / 1_000_000

    return df


def convert_multi_center_profile(
    profile_df: pd.DataFrame,
    nodes_per_center: int,
    num_centers: int,
    cpu_power_per_node: float = 150.0,
    ram_power_per_node: float = 40.0,
    storage_power_per_node: float = 10.0,
    network_power_per_node: float = 10.0,
    pue: float = 1.3,
    dynamic_cpu_power: bool = True,
    dynamic_memory_power: bool = True,
) -> pd.DataFrame:
    """
    Converts profile for multiple synchronized centers.
    """
    center_profile = convert_training_profile_to_center(
        profile_df,
        nodes_per_center,
        cpu_power_per_node,
        ram_power_per_node,
        storage_power_per_node,
        network_power_per_node,
        pue,
        dynamic_cpu_power,
        dynamic_memory_power,
    )
    
    # Scale for multiple centers
    center_profile["facility_it_power_w"] = center_profile["center_it_power_w"] * num_centers
    center_profile["facility_overhead_power_w"] = center_profile["center_overhead_power_w"] * num_centers
    center_profile["facility_total_power_w"] = center_profile["center_total_power_w"] * num_centers
    center_profile["facility_total_power_mw"] = center_profile["facility_total_power_w"] / 1_000_000
    
    return center_profile
