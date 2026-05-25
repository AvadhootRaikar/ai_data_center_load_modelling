import pandas as pd
import numpy as np


def _add_default_optimization_columns(
    df: pd.DataFrame,
    scenario: str,
    gpu_power_factor: float = 1.0,
    gpu_performance_factor: float = 1.0,
    pue_factor: float = 1.0,
    runtime_multiplier: float = 1.0,
    delay_steps: int = 0,
    performance_model: str = "none",
) -> pd.DataFrame:
    """Attach transparent scenario metadata to every timestep."""
    df = df.copy()
    df["scenario"] = scenario
    df["gpu_power_factor"] = float(gpu_power_factor)
    df["gpu_performance_factor"] = float(gpu_performance_factor)
    df["pue_factor"] = float(pue_factor)
    df["runtime_multiplier"] = float(runtime_multiplier)
    df["delay_steps"] = int(delay_steps)
    df["performance_model"] = performance_model
    return df


def _get_utilization_fraction(df: pd.DataFrame) -> pd.Series:
    """
    Returns GPU utilization in the interval [0, 1].

    Preferred source:
    - measured gpu_util_percent from the CSV, averaged by profile_builder.

    Fallback:
    - estimate utilization from gpu_power_w / max(gpu_power_w).
    """
    if "gpu_util_percent" in df.columns:
        util = pd.to_numeric(df["gpu_util_percent"], errors="coerce") / 100.0
    elif "gpu_utilization_percent" in df.columns:
        util = pd.to_numeric(df["gpu_utilization_percent"], errors="coerce") / 100.0
    elif "gpu_power_w" in df.columns and float(df["gpu_power_w"].max()) > 0:
        util = pd.to_numeric(df["gpu_power_w"], errors="coerce") / float(df["gpu_power_w"].max())
    else:
        util = pd.Series(1.0, index=df.index)

    util = util.fillna(util.median() if not util.dropna().empty else 1.0)
    return util.clip(lower=0.0, upper=1.0)


def calculate_gpu_performance_factor(
    gpu_power_factor: float,
    slowdown_sensitivity: float = 0.7,
    min_performance_factor: float = 0.50,
) -> float:
    """
    Constant fallback model for GPU power capping.

    performance_factor = 1 - slowdown_sensitivity * (1 - gpu_power_factor)
    runtime_multiplier = 1 / performance_factor
    """
    gpu_power_factor = float(gpu_power_factor)
    slowdown_sensitivity = float(slowdown_sensitivity)
    min_performance_factor = float(min_performance_factor)

    performance_factor = 1.0 - slowdown_sensitivity * (1.0 - gpu_power_factor)
    performance_factor = max(min_performance_factor, min(1.0, performance_factor))
    return performance_factor


def apply_gpu_power_cap_to_profile(
    df: pd.DataFrame,
    gpu_power_factor: float,
) -> pd.DataFrame:
    """
    Applies a GPU power cap to the measured profile.

    Important: this does NOT simply multiply the whole facility by the GPU factor.
    CPU/RAM/storage/network power are treated as non-GPU overhead and remain constant
    when the required component columns are available.

    Used formula when component columns exist:
        fixed_node_power = node_power_w - gpu_power_w
        capped_node_power = gpu_power_w * gpu_power_factor + fixed_node_power
        scaling_factor = center_total_power_w / node_power_w
        capped_center_power_w = capped_node_power * scaling_factor

    Fallback formula:
        center_total_power_mw *= gpu_power_factor
    """
    df = df.copy()
    gpu_power_factor = float(gpu_power_factor)

    required = {"gpu_power_w", "node_power_w", "center_total_power_w"}
    if required.issubset(df.columns):
        fixed_node_power_w = (df["node_power_w"] - df["gpu_power_w"]).clip(lower=0.0)
        capped_node_power_w = df["gpu_power_w"] * gpu_power_factor + fixed_node_power_w

        node_scale = df["center_total_power_w"] / df["node_power_w"].replace(0, np.nan)
        node_scale = node_scale.fillna(node_scale.median() if not node_scale.dropna().empty else 1.0)

        it_scale = None
        if "center_it_power_w" in df.columns:
            it_scale = df["center_it_power_w"] / df["node_power_w"].replace(0, np.nan)
            it_scale = it_scale.fillna(it_scale.median() if not it_scale.dropna().empty else 1.0)

        df["gpu_power_w_after_cap"] = df["gpu_power_w"] * gpu_power_factor
        df["node_power_w_after_cap"] = capped_node_power_w
        if it_scale is not None:
            df["center_it_power_w"] = capped_node_power_w * it_scale
        df["center_total_power_w_after_cap"] = capped_node_power_w * node_scale
        df["center_total_power_w"] = df["center_total_power_w_after_cap"]
        df["center_overhead_power_w"] = (df["center_total_power_w"] - df.get("center_it_power_w", 0)).clip(lower=0.0) if "center_it_power_w" in df.columns else np.nan
        df["center_total_power_mw"] = df["center_total_power_w_after_cap"] / 1_000_000.0
        df["gpu_cap_power_model"] = "component_based_gpu_only"
    else:
        df["center_total_power_mw"] *= gpu_power_factor
        if "center_total_power_w" in df.columns:
            df["center_total_power_w"] = df["center_total_power_mw"] * 1_000_000.0
        df["gpu_cap_power_model"] = "fallback_total_facility_multiplier"

    return df


def apply_utilization_based_runtime_model(
    df: pd.DataFrame,
    gpu_power_factor: float,
    slowdown_sensitivity: float = 0.7,
    min_performance_factor: float = 0.50,
) -> tuple[pd.DataFrame, dict]:
    """
    Utilization-dependent GPU power-cap runtime model.

    Data source:
    - gpu_util_percent from CSV if available.
    - otherwise approximated from the measured GPU power curve.

    Formula per timestep:
        u(t) = gpu_util_percent(t) / 100
        p(t) = 1 - alpha * u(t) * (1 - f)

    where:
        p(t)  = modeled performance factor at timestep t
        alpha = slowdown_sensitivity
        u(t)  = utilization fraction, 0..1
        f     = GPU power factor, e.g. 0.90

    Runtime effect:
        delta_seconds_new(t) = delta_seconds_old(t) / p(t)

    Effective performance over the whole trace:
        effective_performance = old_duration / new_duration
        runtime_multiplier = new_duration / old_duration
    """
    df = df.copy()
    gpu_power_factor = float(gpu_power_factor)
    alpha = float(slowdown_sensitivity)
    min_perf = float(min_performance_factor)

    util = _get_utilization_fraction(df)
    perf = 1.0 - alpha * util * (1.0 - gpu_power_factor)
    perf = perf.clip(lower=min_perf, upper=1.0)

    old_delta = pd.to_numeric(df["delta_seconds"], errors="coerce").fillna(5.0)
    new_delta = old_delta / perf

    old_duration = float(old_delta.sum())
    new_duration = float(new_delta.sum())
    runtime_multiplier = new_duration / old_duration if old_duration > 0 else 1.0
    effective_performance = 1.0 / runtime_multiplier if runtime_multiplier > 0 else 1.0

    df["gpu_utilization_fraction"] = util
    df["gpu_performance_factor_t"] = perf
    df["gpu_runtime_multiplier_t"] = 1.0 / perf
    df["delta_seconds"] = new_delta
    df["delta_hours"] = df["delta_seconds"] / 3600.0
    df["elapsed_seconds"] = df["delta_seconds"].cumsum()
    df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0

    meta = {
        "performance_model": "utilization_based",
        "average_utilization_fraction": float(util.mean()),
        "weighted_average_utilization_fraction": float((util * old_delta).sum() / old_delta.sum()) if old_delta.sum() > 0 else float(util.mean()),
        "min_utilization_fraction": float(util.min()),
        "max_utilization_fraction": float(util.max()),
        "average_timestep_performance_factor": float(perf.mean()),
        "effective_performance_factor": float(effective_performance),
        "runtime_multiplier": float(runtime_multiplier),
        "formula": "p(t)=1-alpha*u(t)*(1-f); delta_seconds_new=delta_seconds/p(t)",
    }
    return df, meta


def apply_constant_runtime_model(
    df: pd.DataFrame,
    gpu_power_factor: float,
    slowdown_sensitivity: float = 0.7,
    min_performance_factor: float = 0.50,
) -> tuple[pd.DataFrame, dict]:
    """Legacy constant runtime model used only as fallback/manual comparison."""
    df = df.copy()
    perf = calculate_gpu_performance_factor(
        gpu_power_factor=gpu_power_factor,
        slowdown_sensitivity=slowdown_sensitivity,
        min_performance_factor=min_performance_factor,
    )
    runtime_multiplier = 1.0 / perf
    df["gpu_utilization_fraction"] = _get_utilization_fraction(df)
    df["gpu_performance_factor_t"] = perf
    df["gpu_runtime_multiplier_t"] = runtime_multiplier
    df["delta_seconds"] *= runtime_multiplier
    df["delta_hours"] = df["delta_seconds"] / 3600.0
    df["elapsed_seconds"] = df["delta_seconds"].cumsum()
    df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0
    return df, {
        "performance_model": "constant",
        "average_utilization_fraction": float(df["gpu_utilization_fraction"].mean()),
        "weighted_average_utilization_fraction": float(df["gpu_utilization_fraction"].mean()),
        "effective_performance_factor": float(perf),
        "runtime_multiplier": float(runtime_multiplier),
        "formula": "p=1-alpha*(1-f); delta_seconds_new=delta_seconds/p",
    }



def apply_cooling_improvement_to_profile(
    df: pd.DataFrame,
    cooling_overhead_factor: float,
) -> pd.DataFrame:
    """
    Applies Improved Cooling/PUE in a physically interpretable way.

    Correct interpretation:
    - IT power is the ML workload power and does not change.
    - Cooling/PUE improvement reduces only overhead power.

    Baseline:
        total_power = IT_power + overhead_power
        overhead_power = total_power - IT_power

    Scenario:
        new_overhead = overhead_power * cooling_overhead_factor
        new_total = IT_power + new_overhead
        new_PUE = 1 + (baseline_PUE - 1) * cooling_overhead_factor

    Example:
        baseline PUE = 1.30, cooling factor = 0.85
        new_PUE = 1 + 0.30 * 0.85 = 1.255
        effective facility multiplier = 1.255 / 1.30 = 0.965
        total energy saving ≈ 3.5%, not 15%.
    """
    df = df.copy()
    factor = float(cooling_overhead_factor)

    required = {"center_it_power_w", "center_total_power_w"}
    if required.issubset(df.columns):
        old_total_w = pd.to_numeric(df["center_total_power_w"], errors="coerce")
        it_power_w = pd.to_numeric(df["center_it_power_w"], errors="coerce")
        overhead_w = (old_total_w - it_power_w).clip(lower=0.0)
        new_overhead_w = overhead_w * factor
        new_total_w = it_power_w + new_overhead_w

        old_pue = old_total_w / it_power_w.replace(0, np.nan)
        new_pue = new_total_w / it_power_w.replace(0, np.nan)
        effective_factor = new_total_w / old_total_w.replace(0, np.nan)

        df["center_overhead_power_w_before_cooling"] = overhead_w
        df["center_overhead_power_w_after_cooling"] = new_overhead_w
        df["center_total_power_w"] = new_total_w
        df["center_total_power_mw"] = new_total_w / 1_000_000.0
        df["cooling_overhead_factor"] = factor
        df["effective_facility_power_factor"] = effective_factor.fillna(1.0)
        df["baseline_effective_pue"] = old_pue.fillna(1.0)
        df["scenario_effective_pue"] = new_pue.fillna(1.0)
        df["cooling_model"] = "overhead_only_pue_model"
    else:
        df["center_total_power_mw"] *= factor
        if "center_total_power_w" in df.columns:
            df["center_total_power_w"] = df["center_total_power_mw"] * 1_000_000.0
        df["cooling_overhead_factor"] = factor
        df["effective_facility_power_factor"] = factor
        df["baseline_effective_pue"] = np.nan
        df["scenario_effective_pue"] = np.nan
        df["cooling_model"] = "fallback_total_facility_multiplier"

    return df
def apply_optimization_scenario(
    df: pd.DataFrame,
    scenario: str,
    gpu_power_factor: float = 1.0,
    pue_factor: float = 1.0,
    delay_steps: int = 0,
    gpu_slowdown_sensitivity: float = 0.7,
    account_for_runtime_slowdown: bool = True,
    gpu_runtime_model: str = "utilization_based",
) -> pd.DataFrame:
    """
    Applies the selected scenario to the center-level power profile.

    Rules:
    - GPU Power Limit changes measured GPU power, not necessarily CPU/RAM overhead.
    - If runtime slowdown is enabled, delta_seconds changes before energy integration.
    - Energy is calculated later as Σ P(t) × Δt.
    """
    df = df.copy()

    gpu_performance_factor = 1.0
    runtime_multiplier = 1.0
    performance_model = "none"

    if scenario == "Baseline":
        return _add_default_optimization_columns(df, scenario)

    if scenario == "GPU Power Limit":
        df = apply_gpu_power_cap_to_profile(df, gpu_power_factor)

        if account_for_runtime_slowdown:
            if gpu_runtime_model == "utilization_based":
                df, meta = apply_utilization_based_runtime_model(
                    df,
                    gpu_power_factor=gpu_power_factor,
                    slowdown_sensitivity=gpu_slowdown_sensitivity,
                )
            else:
                df, meta = apply_constant_runtime_model(
                    df,
                    gpu_power_factor=gpu_power_factor,
                    slowdown_sensitivity=gpu_slowdown_sensitivity,
                )
            gpu_performance_factor = meta["effective_performance_factor"]
            runtime_multiplier = meta["runtime_multiplier"]
            performance_model = meta["performance_model"]

    elif scenario == "Improved Cooling":
        df = apply_cooling_improvement_to_profile(df, pue_factor)

    elif scenario == "Delayed Training":
        if delay_steps > 0:
            delay_df = df.iloc[:delay_steps].copy()
            delay_df["center_total_power_mw"] = 0.0
            if "center_total_power_w" in delay_df.columns:
                delay_df["center_total_power_w"] = 0.0
            df = pd.concat([delay_df, df], ignore_index=True)
            df["timestep"] = range(len(df))
            df["elapsed_seconds"] = df["delta_seconds"].cumsum()
            df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0

    elif scenario == "Combined Optimization":
        df = apply_gpu_power_cap_to_profile(df, gpu_power_factor)
        df = apply_cooling_improvement_to_profile(df, pue_factor)

        if account_for_runtime_slowdown:
            if gpu_runtime_model == "utilization_based":
                df, meta = apply_utilization_based_runtime_model(
                    df,
                    gpu_power_factor=gpu_power_factor,
                    slowdown_sensitivity=gpu_slowdown_sensitivity,
                )
            else:
                df, meta = apply_constant_runtime_model(
                    df,
                    gpu_power_factor=gpu_power_factor,
                    slowdown_sensitivity=gpu_slowdown_sensitivity,
                )
            gpu_performance_factor = meta["effective_performance_factor"]
            runtime_multiplier = meta["runtime_multiplier"]
            performance_model = meta["performance_model"]

        if delay_steps > 0:
            delay_df = df.iloc[:delay_steps].copy()
            delay_df["center_total_power_mw"] = 0.0
            if "center_total_power_w" in delay_df.columns:
                delay_df["center_total_power_w"] = 0.0
            df = pd.concat([delay_df, df], ignore_index=True)
            df["timestep"] = range(len(df))
            df["elapsed_seconds"] = df["delta_seconds"].cumsum()
            df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return _add_default_optimization_columns(
        df,
        scenario=scenario,
        gpu_power_factor=gpu_power_factor,
        gpu_performance_factor=gpu_performance_factor,
        pue_factor=pue_factor,
        runtime_multiplier=runtime_multiplier,
        delay_steps=delay_steps,
        performance_model=performance_model,
    )


def build_optimization_audit(
    baseline_energy_mwh: float,
    optimized_energy_mwh: float,
    baseline_projection: dict,
    optimized_projection: dict,
    scenario: str,
    optimized_profile: pd.DataFrame | None = None,
    gpu_power_factor: float = 1.0,
    gpu_slowdown_sensitivity: float = 0.7,
    account_for_runtime_slowdown: bool = True,
    pue_factor: float = 1.0,
    delay_steps: int = 0,
    enable_load_balancing: bool = False,
    number_of_centers: int = 1,
    max_active_centers: int = 1,
) -> tuple[pd.DataFrame, dict]:
    """Creates a readable comparison table explaining exactly what changed."""
    base_avg = float(baseline_projection["average_power_mw"])
    opt_avg = float(optimized_projection["average_power_mw"])
    base_peak = float(baseline_projection["peak_power_mw"])
    opt_peak = float(optimized_projection["peak_power_mw"])
    base_duration = float(baseline_projection["trace_duration_hours"])
    opt_duration = float(optimized_projection["trace_duration_hours"])

    energy_delta = float(optimized_energy_mwh) - float(baseline_energy_mwh)
    energy_delta_percent = (energy_delta / baseline_energy_mwh * 100.0) if baseline_energy_mwh > 0 else 0.0

    gpu_performance_factor = 1.0
    runtime_multiplier = 1.0
    modeled_energy_ratio_from_gpu = 1.0
    avg_util = None
    min_util = None
    max_util = None
    performance_model = "none"
    avg_timestep_perf = None

    if scenario in ["GPU Power Limit", "Combined Optimization"] and optimized_profile is not None:
        if "gpu_performance_factor" in optimized_profile.columns:
            gpu_performance_factor = float(optimized_profile["gpu_performance_factor"].iloc[0])
        if "runtime_multiplier" in optimized_profile.columns:
            runtime_multiplier = float(optimized_profile["runtime_multiplier"].iloc[0])
        if "performance_model" in optimized_profile.columns:
            performance_model = str(optimized_profile["performance_model"].iloc[0])
        if "gpu_utilization_fraction" in optimized_profile.columns:
            avg_util = float(optimized_profile["gpu_utilization_fraction"].mean())
            min_util = float(optimized_profile["gpu_utilization_fraction"].min())
            max_util = float(optimized_profile["gpu_utilization_fraction"].max())
        if "gpu_performance_factor_t" in optimized_profile.columns:
            avg_timestep_perf = float(optimized_profile["gpu_performance_factor_t"].mean())
        modeled_energy_ratio_from_gpu = gpu_power_factor * runtime_multiplier
    elif scenario in ["GPU Power Limit", "Combined Optimization"]:
        if account_for_runtime_slowdown:
            gpu_performance_factor = calculate_gpu_performance_factor(
                gpu_power_factor=gpu_power_factor,
                slowdown_sensitivity=gpu_slowdown_sensitivity,
            )
            runtime_multiplier = 1.0 / gpu_performance_factor
            performance_model = "constant_fallback"
        modeled_energy_ratio_from_gpu = gpu_power_factor * runtime_multiplier

    rows = [
        {
            "Metric": "Trace duration",
            "Baseline": f"{base_duration:.3f} h",
            "Scenario": f"{opt_duration:.3f} h",
            "Change": f"{opt_duration - base_duration:+.3f} h",
            "How it is calculated": "sum(delta_seconds) / 3600. For GPU cap, delta_seconds can increase because lower performance means longer runtime.",
        },
        {
            "Metric": "Weighted average power",
            "Baseline": f"{base_avg * 1000:.2f} kW" if base_avg >= 0.001 else f"{base_avg * 1_000_000:.2f} W",
            "Scenario": f"{opt_avg * 1000:.2f} kW" if opt_avg >= 0.001 else f"{opt_avg * 1_000_000:.2f} W",
            "Change": f"{((opt_avg / base_avg - 1.0) * 100.0):+.2f}%" if base_avg > 0 else "N/A",
            "How it is calculated": "integrated energy / trace duration. This is time-weighted, not a simple row average.",
        },
        {
            "Metric": "Peak power",
            "Baseline": f"{base_peak * 1000:.2f} kW" if base_peak >= 0.001 else f"{base_peak * 1_000_000:.2f} W",
            "Scenario": f"{opt_peak * 1000:.2f} kW" if opt_peak >= 0.001 else f"{opt_peak * 1_000_000:.2f} W",
            "Change": f"{((opt_peak / base_peak - 1.0) * 100.0):+.2f}%" if base_peak > 0 else "N/A",
            "How it is calculated": "maximum total_power_mw from the pandapower time-series results.",
        },
        {
            "Metric": "Integrated energy",
            "Baseline": f"{baseline_energy_mwh * 1000:.2f} kWh" if baseline_energy_mwh >= 0.001 else f"{baseline_energy_mwh * 1_000_000:.2f} Wh",
            "Scenario": f"{optimized_energy_mwh * 1000:.2f} kWh" if optimized_energy_mwh >= 0.001 else f"{optimized_energy_mwh * 1_000_000:.2f} Wh",
            "Change": f"{energy_delta_percent:+.2f}%",
            "How it is calculated": "Energy = Σ total_power_mw(t) × delta_seconds(t)/3600.",
        },
    ]

    if scenario in ["GPU Power Limit", "Combined Optimization"]:
        rows.extend(
            [
                {
                    "Metric": "GPU power factor",
                    "Baseline": "1.000",
                    "Scenario": f"{gpu_power_factor:.3f}",
                    "Change": f"{(gpu_power_factor - 1.0) * 100.0:+.1f}%",
                    "How it is calculated": "User-selected GPU cap factor. Applied to measured GPU power; fixed CPU/RAM/storage/network power stays constant when component columns exist.",
                },
                {
                    "Metric": "Measured GPU utilization",
                    "Baseline": "CSV column gpu_util_percent",
                    "Scenario": "N/A" if avg_util is None else f"avg {avg_util*100:.1f}% / min {min_util*100:.1f}% / max {max_util*100:.1f}%",
                    "Change": "used as input",
                    "How it is calculated": "u(t)=gpu_util_percent(t)/100. This comes from the measured CSV trace, averaged across runs by profile_builder.",
                },
                {
                    "Metric": "Performance model",
                    "Baseline": "1.000",
                    "Scenario": performance_model,
                    "Change": "utilization-dependent" if performance_model == "utilization_based" else performance_model,
                    "How it is calculated": "p(t)=1-alpha*u(t)*(1-f), where alpha is sensitivity, u(t) is measured GPU utilization, and f is the GPU power factor.",
                },
                {
                    "Metric": "Average timestep performance",
                    "Baseline": "1.000",
                    "Scenario": "N/A" if avg_timestep_perf is None else f"{avg_timestep_perf:.3f}",
                    "Change": "N/A" if avg_timestep_perf is None else f"{(avg_timestep_perf - 1.0) * 100.0:+.1f}%",
                    "How it is calculated": "Mean of p(t) over all timesteps. It shows the average local training-speed factor.",
                },
                {
                    "Metric": "Effective GPU performance factor",
                    "Baseline": "1.000",
                    "Scenario": f"{gpu_performance_factor:.3f}",
                    "Change": f"{(gpu_performance_factor - 1.0) * 100.0:+.1f}%",
                    "How it is calculated": "effective performance = baseline duration / scenario duration after applying p(t) to delta_seconds.",
                },
                {
                    "Metric": "Runtime multiplier from GPU limit",
                    "Baseline": "1.000",
                    "Scenario": f"{runtime_multiplier:.3f}",
                    "Change": f"{(runtime_multiplier - 1.0) * 100.0:+.1f}%",
                    "How it is calculated": "runtime multiplier = scenario duration / baseline duration = 1 / effective performance factor.",
                },
                {
                    "Metric": "GPU-cap same-work ratio before grid effects",
                    "Baseline": "1.000",
                    "Scenario": f"{modeled_energy_ratio_from_gpu:.3f}",
                    "Change": f"{(modeled_energy_ratio_from_gpu - 1.0) * 100.0:+.1f}%",
                    "How it is calculated": "Approx. ratio = GPU power factor × runtime multiplier. Final energy also includes fixed non-GPU components and PUE.",
                },
            ]
        )

    if scenario in ["Improved Cooling", "Combined Optimization"]:
        cooling_model = str(optimized_profile["cooling_model"].iloc[0]) if optimized_profile is not None and "cooling_model" in optimized_profile.columns else "unknown"
        eff_factor = float(optimized_profile["effective_facility_power_factor"].mean()) if optimized_profile is not None and "effective_facility_power_factor" in optimized_profile.columns else float(pue_factor)
        base_pue = float(optimized_profile["baseline_effective_pue"].mean()) if optimized_profile is not None and "baseline_effective_pue" in optimized_profile.columns else float("nan")
        scen_pue = float(optimized_profile["scenario_effective_pue"].mean()) if optimized_profile is not None and "scenario_effective_pue" in optimized_profile.columns else float("nan")
        overhead_before = float(optimized_profile["center_overhead_power_w_before_cooling"].mean()) if optimized_profile is not None and "center_overhead_power_w_before_cooling" in optimized_profile.columns else float("nan")
        overhead_after = float(optimized_profile["center_overhead_power_w_after_cooling"].mean()) if optimized_profile is not None and "center_overhead_power_w_after_cooling" in optimized_profile.columns else float("nan")
        rows.extend([
            {
                "Metric": "Cooling model",
                "Baseline": "baseline PUE",
                "Scenario": cooling_model,
                "Change": "overhead only",
                "How it is calculated": "Improved Cooling reduces only non-IT facility overhead. IT power is unchanged because the ML workload is unchanged.",
            },
            {
                "Metric": "Cooling overhead factor",
                "Baseline": "1.000",
                "Scenario": f"{pue_factor:.3f}",
                "Change": f"{(pue_factor - 1.0) * 100.0:+.1f}% overhead",
                "How it is calculated": "User-selected factor applied to overhead_power = total_facility_power - IT_power, not to the whole facility load.",
            },
            {
                "Metric": "Effective facility power factor",
                "Baseline": "1.000",
                "Scenario": f"{eff_factor:.3f}",
                "Change": f"{(eff_factor - 1.0) * 100.0:+.2f}% total facility",
                "How it is calculated": "effective_factor = (IT_power + overhead_power × cooling_factor) / (IT_power + overhead_power).",
            },
            {
                "Metric": "Effective PUE",
                "Baseline": "N/A" if np.isnan(base_pue) else f"{base_pue:.3f}",
                "Scenario": "N/A" if np.isnan(scen_pue) else f"{scen_pue:.3f}",
                "Change": "N/A" if np.isnan(base_pue) or base_pue == 0 else f"{((scen_pue / base_pue - 1.0) * 100.0):+.2f}%",
                "How it is calculated": "new_PUE = 1 + (baseline_PUE - 1) × cooling_factor.",
            },
            {
                "Metric": "Average cooling/infrastructure overhead per center",
                "Baseline": "N/A" if np.isnan(overhead_before) else f"{overhead_before / 1000:.2f} kW",
                "Scenario": "N/A" if np.isnan(overhead_after) else f"{overhead_after / 1000:.2f} kW",
                "Change": "N/A" if np.isnan(overhead_before) or overhead_before == 0 else f"{((overhead_after / overhead_before - 1.0) * 100.0):+.2f}%",
                "How it is calculated": "overhead_power = facility_power - IT_power. The cooling factor is applied to this overhead only.",
            },
        ])

    if scenario in ["Delayed Training", "Combined Optimization"] and delay_steps > 0:
        rows.append(
            {
                "Metric": "Delay steps",
                "Baseline": "0",
                "Scenario": str(delay_steps),
                "Change": f"+{delay_steps}",
                "How it is calculated": "Idle samples inserted before the workload. This shifts demand in time; it is not a real energy saving by itself.",
            }
        )

    if enable_load_balancing:
        active_ratio = max_active_centers / number_of_centers if number_of_centers > 0 else 1.0
        rows.append(
            {
                "Metric": "Maximum active centers",
                "Baseline": str(number_of_centers),
                "Scenario": str(max_active_centers),
                "Change": f"{(active_ratio - 1.0) * 100.0:+.1f}% simultaneous activity",
                "How it is calculated": "Scheduling controls center_i_active columns. It lowers simultaneous grid load but may extend same-work runtime.",
            }
        )

    notes = {
        "scenario": scenario,
        "baseline_energy_mwh": float(baseline_energy_mwh),
        "optimized_energy_mwh": float(optimized_energy_mwh),
        "energy_delta_mwh": energy_delta,
        "energy_delta_percent": energy_delta_percent,
        "gpu_performance_factor": gpu_performance_factor,
        "runtime_multiplier": runtime_multiplier,
        "modeled_energy_ratio_from_gpu": modeled_energy_ratio_from_gpu,
        "performance_model": performance_model,
        "average_utilization_fraction": avg_util,
        "formula": "Energy = Σ P(t) × Δt; GPU cap uses p(t)=1-alpha*u(t)*(1-f); Improved Cooling uses total_new = IT_power + overhead_power × cooling_factor",
    }

    return pd.DataFrame(rows), notes


def apply_center_level_load_balancing(
    df: pd.DataFrame,
    number_of_centers: int,
    max_active_centers: int,
    strategy: str = "same_centers_active",
) -> pd.DataFrame:
    """
    Creates center_X_active columns.

    This does not magically reduce the energy needed for the same total work.
    It reduces simultaneous activity in the simulated window.
    """

    df = df.copy()
    timesteps = len(df)

    max_active_centers = max(1, min(max_active_centers, number_of_centers))

    schedule = []

    for t in range(timesteps):
        active = [0] * number_of_centers

        if strategy == "same_centers_active":
            active_indices = list(range(max_active_centers))

        elif strategy == "rotating_centers":
            start = t % number_of_centers
            active_indices = [(start + i) % number_of_centers for i in range(max_active_centers)]

        elif strategy == "variable_activity":
            # Variable activity changes how many centers are active at each timestep.
            # The active subset also rotates, otherwise the first centers would be
            # permanently favored and later centers would never receive work.
            wave = 0.5 + 0.5 * np.sin(2 * np.pi * t / max(timesteps, 1))
            active_count = max(1, int(round(wave * max_active_centers)))
            start = t % number_of_centers
            active_indices = [(start + i) % number_of_centers for i in range(active_count)]

        else:
            raise ValueError(f"Unknown scheduling strategy: {strategy}")

        for idx in active_indices:
            active[idx] = 1

        row = {"timestep": t}

        for i in range(number_of_centers):
            row[f"center_{i + 1}_active"] = active[i]

        row["active_centers"] = sum(active)
        schedule.append(row)

    schedule_df = pd.DataFrame(schedule)
    df = df.merge(schedule_df, on="timestep", how="left")

    return df
