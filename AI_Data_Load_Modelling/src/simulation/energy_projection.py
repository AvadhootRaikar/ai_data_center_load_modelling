"""
Energy Projection and Metrics Calculation

Projects energy consumption and provides same-work analysis metrics.
"""

import pandas as pd


def calculate_energy_projections(results_df: pd.DataFrame) -> dict:
    """Estimates energy projections from simulated power profile."""
    df = results_df.copy()

    if "delta_seconds" not in df.columns:
        raise ValueError("delta_seconds column missing from simulation results")

    trace_duration_seconds = float(df["delta_seconds"].sum())
    trace_duration_minutes = trace_duration_seconds / 60.0
    trace_duration_hours = trace_duration_seconds / 3600.0

    if "energy_mwh" in df.columns and trace_duration_hours > 0:
        trace_energy_mwh = float(df["energy_mwh"].sum())
        avg_power_mw = trace_energy_mwh / trace_duration_hours
    else:
        avg_power_mw = float(df["total_power_mw"].mean())
        trace_energy_mwh = avg_power_mw * trace_duration_hours

    peak_power_mw = float(df["total_power_mw"].max())

    return {
        "trace_duration_seconds": trace_duration_seconds,
        "trace_duration_minutes": trace_duration_minutes,
        "trace_duration_hours": trace_duration_hours,
        "trace_energy_mwh": trace_energy_mwh,
        "average_power_mw": avg_power_mw,
        "peak_power_mw": peak_power_mw,
        "energy_1h_mwh": avg_power_mw * 1,
        "energy_6h_mwh": avg_power_mw * 6,
        "energy_24h_mwh": avg_power_mw * 24,
        "energy_30d_mwh": avg_power_mw * 24 * 30,
    }


def calculate_energy_for_hours(avg_power_mw: float, hours: float) -> float:
    """Energy projection: MWh = MW × hours."""
    return float(avg_power_mw) * float(hours)


def calculate_same_work_metrics(
    baseline_results: pd.DataFrame,
    optimized_results: pd.DataFrame,
    number_of_centers: int,
) -> dict:
    """
    Interprets scheduling correctly using same-work analysis.
    
    If fewer centers are active, the same amount of work needs more time.
    This estimates energy and time for completing the same work.
    """
    baseline = baseline_results.copy()
    optimized = optimized_results.copy()

    baseline_duration_h = float(baseline["delta_seconds"].sum()) / 3600.0
    optimized_duration_h = float(optimized["delta_seconds"].sum()) / 3600.0

    baseline_energy = float((baseline.get("energy_mwh", baseline["total_power_mw"] * baseline["delta_seconds"] / 3600)).sum())
    optimized_energy = float((optimized.get("energy_mwh", optimized["total_power_mw"] * optimized["delta_seconds"] / 3600)).sum())

    if "active_centers" in optimized.columns:
        completed_center_seconds = float((optimized["active_centers"] * optimized["delta_seconds"]).sum())
    else:
        completed_center_seconds = float(number_of_centers * optimized["delta_seconds"].sum())

    required_center_seconds = float(number_of_centers * baseline["delta_seconds"].sum())
    work_completed_ratio = completed_center_seconds / required_center_seconds if required_center_seconds > 0 else 1.0
    work_completed_ratio = max(work_completed_ratio, 1e-9)

    same_work_duration_hours = optimized_duration_h / work_completed_ratio
    same_work_energy_mwh = optimized_energy / work_completed_ratio

    same_work_energy_saving_mwh = baseline_energy - same_work_energy_mwh
    same_work_energy_saving_percent = (
        same_work_energy_saving_mwh / baseline_energy * 100.0 if baseline_energy > 0 else 0.0
    )

    return {
        "baseline_duration_hours": baseline_duration_h,
        "optimized_window_duration_hours": optimized_duration_h,
        "work_completed_ratio": work_completed_ratio,
        "same_work_duration_hours": same_work_duration_hours,
        "same_work_energy_mwh": same_work_energy_mwh,
        "same_work_energy_saving_mwh": same_work_energy_saving_mwh,
        "same_work_energy_saving_percent": same_work_energy_saving_percent,
    }
