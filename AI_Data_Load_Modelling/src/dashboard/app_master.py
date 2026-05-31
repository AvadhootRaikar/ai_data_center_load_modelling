import sys
import copy
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import pandapower as pp
import networkx as nx
try:
    from pyvis.network import Network
except Exception:
    Network = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.profile_builder import build_training_profile, build_selected_workload_profile, build_measured_profile
from simulation.power_model import convert_training_profile_to_center
from simulation.run_simulation import run_hpc_simulation, calculate_energy
from simulation.grid_model import create_hpc_grid
from simulation.optimization_scenarios import (
    apply_optimization_scenario,
    apply_center_level_load_balancing,
    build_optimization_audit,
)
from simulation.capacity_analysis import run_capacity_analysis
from simulation.energy_projection import (
    calculate_energy_projections,
    calculate_same_work_metrics,
    calculate_energy_for_hours,
)
from simulation.cost_model import (
    calculate_cost_projection,
    calculate_costs,
    build_tou_price_table,
    calculate_time_of_day_costs,
)


# --- Streamlit rerun/state helpers ---
# Streamlit reruns the whole script whenever a radio/selectbox changes.
# These cached wrappers keep the already-computed simulation from disappearing or becoming painfully slow.
@st.cache_data(show_spinner=False)
def cached_build_training_profile(training_path: str, inference_path: str = "data/raw_runs/inference", workload_mode: str = "Training Run"):
    return build_selected_workload_profile(training_path, inference_path, workload_mode)




@st.cache_data(show_spinner=False)
def cached_build_workload_comparison(
    training_path: str,
    inference_path: str,
    nodes_per_center: int,
    cpu_power_per_node: float,
    pue: float,
    number_of_centers: int,
):
    """Builds training/inference/simultaneous comparison without running pandapower."""
    modes = ["Training Run", "Inference Run", "Simultaneous Training + Inference"]
    rows = []
    curves = []

    for mode in modes:
        profile = build_selected_workload_profile(training_path, inference_path, mode)
        center_profile = convert_training_profile_to_center(
            profile,
            nodes_per_center=nodes_per_center,
            cpu_power_per_node=cpu_power_per_node,
            pue=pue,
        )
        total_power_mw = center_profile["center_total_power_mw"] * number_of_centers
        energy_mwh = (total_power_mw * center_profile["delta_seconds"] / 3600.0).sum()
        duration_hours = center_profile["delta_seconds"].sum() / 3600.0
        avg_power_mw = energy_mwh / duration_hours if duration_hours > 0 else 0.0
        peak_power_mw = total_power_mw.max() if len(total_power_mw) else 0.0

        rows.append({
            "Workload": mode,
            "Samples": len(center_profile),
            "Trace duration (h)": duration_hours,
            "Avg GPU power (W)": center_profile["total_gpu_power_w"].mean(),
            "Peak GPU power (W)": center_profile["total_gpu_power_w"].max(),
            "Avg GPU util (%)": center_profile["gpu_util_percent"].mean() if "gpu_util_percent" in center_profile else None,
            "Avg total grid load (MW)": avg_power_mw,
            "Peak total grid load (MW)": peak_power_mw,
            "Integrated trace energy (MWh)": energy_mwh,
        })

        curve = pd.DataFrame({
            "elapsed_hours": center_profile["elapsed_hours"],
            "total_power_mw": total_power_mw,
            "gpu_util_percent": center_profile["gpu_util_percent"] if "gpu_util_percent" in center_profile else 0,
            "Workload": mode,
        })
        curves.append(curve)

    return pd.DataFrame(rows), pd.concat(curves, ignore_index=True)


@st.cache_data(show_spinner=False)
def cached_run_hpc_simulation(
    workload_df: pd.DataFrame,
    number_of_centers: int,
    clusters_per_center: int,
    racks_per_cluster: int,
    fast_mode: bool,
    grid_backend: str,
    simbench_code: str,
    include_existing_simbench_loads: bool,
):
    return run_hpc_simulation(
        workload_df=workload_df,
        number_of_centers=number_of_centers,
        clusters_per_center=clusters_per_center,
        racks_per_cluster=racks_per_cluster,
        fast_mode=fast_mode,
        grid_backend=grid_backend,
        simbench_code=simbench_code,
        include_existing_simbench_loads=include_existing_simbench_loads,
    )


st.set_page_config(
    page_title="HPC Training Energy Simulation",
    page_icon="⚡",
    layout="wide",
)


st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetricLabel"] p {font-size: 0.88rem; color: #475569;}
    div[data-testid="stMetricValue"] {font-size: 1.6rem; color: #0f172a;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding: 8px 14px;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
    }
    .stTabs [aria-selected="true"] {background: #dbeafe !important; border-color: #93c5fd !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def format_power(value_mw: float) -> str:
    if pd.isna(value_mw):
        return "N/A"
    if abs(value_mw) < 0.001:
        return f"{value_mw * 1_000_000:.2f} W"
    if abs(value_mw) < 1:
        return f"{value_mw * 1000:.2f} kW"
    return f"{value_mw:.2f} MW"


def format_energy(value_mwh: float) -> str:
    if pd.isna(value_mwh):
        return "N/A"
    if abs(value_mwh) < 0.001:
        return f"{value_mwh * 1_000_000:.2f} Wh"
    if abs(value_mwh) < 1:
        return f"{value_mwh * 1000:.2f} kWh"
    return f"{value_mwh:.2f} MWh"


def build_comparison_df(baseline_results, optimized_results, column_name):
    base_cols = ["timestep", column_name]
    if "elapsed_hours" in baseline_results.columns:
        base_cols.append("elapsed_hours")

    opt_cols = ["timestep", column_name]
    if "elapsed_hours" in optimized_results.columns:
        opt_cols.append("elapsed_hours")

    left = baseline_results[base_cols].copy()
    left["case"] = "Baseline"

    right = optimized_results[opt_cols].copy()
    right["case"] = "Optimized / Balanced"

    return pd.concat([left, right], ignore_index=True)



def format_clock_hour(hour_value: float) -> str:
    """Formats decimal clock hours as HH:MM on a 24-hour clock."""
    hour_value = float(hour_value) % 24.0
    total_minutes = int(round(hour_value * 60)) % (24 * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def describe_workload_timing(start_hour: float, duration_hours: float) -> dict:
    end_hour = (float(start_hour) + float(duration_hours)) % 24.0
    crosses_midnight = (float(start_hour) + float(duration_hours)) >= 24.0
    return {
        "start_hour": float(start_hour) % 24.0,
        "end_hour": end_hour,
        "duration_hours": float(duration_hours),
        "start_label": format_clock_hour(start_hour),
        "end_label": format_clock_hour(end_hour),
        "crosses_midnight": crosses_midnight,
    }


def add_clock_labels(cost_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure every cost dataframe has the columns required by the overlay chart.

    Time-of-day pricing creates clock_hour / price_period / price_eur_per_kwh.
    Flat-price calculations do not need clock time mathematically, but the chart
    still needs labels. Missing columns are filled safely instead of crashing.
    """
    df = cost_df.copy()

    if "elapsed_hours" not in df.columns:
        if "elapsed_seconds" in df.columns:
            df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0
        elif "delta_seconds" in df.columns:
            df["elapsed_hours"] = df["delta_seconds"].cumsum() / 3600.0
        else:
            df["elapsed_hours"] = range(len(df))

    if "clock_hour" not in df.columns:
        df["clock_hour"] = df["elapsed_hours"] % 24.0

    df["clock_time"] = df["clock_hour"].apply(format_clock_hour)

    if "price_period" not in df.columns:
        df["price_period"] = "Flat price"

    if "price_eur_per_kwh" not in df.columns:
        df["price_eur_per_kwh"] = 0.0

    if "energy_kwh" not in df.columns:
        if "energy_mwh" in df.columns:
            df["energy_kwh"] = df["energy_mwh"] * 1000.0
        elif "total_power_mw" in df.columns and "delta_seconds" in df.columns:
            df["energy_kwh"] = df["total_power_mw"] * df["delta_seconds"] / 3600.0 * 1000.0
        else:
            df["energy_kwh"] = 0.0

    if "cost_eur" not in df.columns:
        df["cost_eur"] = df["energy_kwh"] * df["price_eur_per_kwh"]

    return df


def build_tariff_coverage(cost_df: pd.DataFrame) -> pd.DataFrame:
    df = cost_df.copy()
    if len(df) == 0 or "price_period" not in df.columns:
        return pd.DataFrame()
    grouped = (
        df.groupby("price_period", as_index=False)
        .agg(
            runtime_minutes=("delta_seconds", lambda x: float(x.sum()) / 60.0),
            energy_kwh=("energy_kwh", "sum"),
            cost_eur=("cost_eur", "sum"),
            avg_price_eur_per_kwh=("price_eur_per_kwh", "mean"),
        )
    )
    total_runtime = grouped["runtime_minutes"].sum()
    total_energy = grouped["energy_kwh"].sum()
    total_cost = grouped["cost_eur"].sum()
    grouped["runtime_share_percent"] = grouped["runtime_minutes"] / total_runtime * 100.0 if total_runtime > 0 else 0.0
    grouped["energy_share_percent"] = grouped["energy_kwh"] / total_energy * 100.0 if total_energy > 0 else 0.0
    grouped["cost_share_percent"] = grouped["cost_eur"] / total_cost * 100.0 if total_cost > 0 else 0.0
    order = {"Night / off-peak": 1, "Morning peak": 2, "Midday / renewable window": 3, "Evening peak": 4, "Late evening": 5, "Flat price": 99}
    grouped["_order"] = grouped["price_period"].map(order).fillna(50)
    return grouped.sort_values("_order").drop(columns=["_order"])



def build_mlperf_input_summary(folder_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inspect the raw MLPerf CSV files used to build the representative trace.

    This is intentionally separate from the simulation. It documents the measured
    workload data before scaling it to node / center / grid level.
    """
    folder = Path(folder_path)
    rows = []
    required = {"timestamp", "total_gpu_power_w"}
    strongly_recommended = {"gpu_util_percent", "gpu_power_w", "cpu_util_percent", "num_gpus"}

    if not folder.exists():
        return pd.DataFrame(), pd.DataFrame()

    files = sorted(folder.glob("*.csv"))
    for file in files:
        df = pd.read_csv(file)
        missing_required = sorted(required - set(df.columns))
        missing_recommended = sorted(strongly_recommended - set(df.columns))

        timestamp_ok = "timestamp" in df.columns
        if timestamp_ok:
            ts = pd.to_datetime(df["timestamp"], format="%H:%M:%S", errors="coerce")
            valid_ts = ts.notna().all()
            delta = ts.sort_values().diff().dt.total_seconds()
            median_delta = float(delta.dropna().median()) if len(delta.dropna()) else 0.0
            duration_seconds = float(delta.dropna()[delta.dropna() > 0].sum()) if len(delta.dropna()) else 0.0
        else:
            valid_ts = False
            median_delta = 0.0
            duration_seconds = 0.0

        power_col = "total_gpu_power_w" if "total_gpu_power_w" in df.columns else None
        util_col = "gpu_util_percent" if "gpu_util_percent" in df.columns else None

        rows.append(
            {
                "file": file.name,
                "rows": len(df),
                "timestamp_valid": valid_ts,
                "duration_minutes_raw": duration_seconds / 60.0,
                "median_sample_interval_s": median_delta,
                "avg_total_gpu_power_w": float(pd.to_numeric(df[power_col], errors="coerce").mean()) if power_col else None,
                "peak_total_gpu_power_w": float(pd.to_numeric(df[power_col], errors="coerce").max()) if power_col else None,
                "avg_gpu_util_percent": float(pd.to_numeric(df[util_col], errors="coerce").mean()) if util_col else None,
                "max_gpu_util_percent": float(pd.to_numeric(df[util_col], errors="coerce").max()) if util_col else None,
                "missing_required": ", ".join(missing_required) if missing_required else "None",
                "missing_recommended": ", ".join(missing_recommended) if missing_recommended else "None",
            }
        )

    summary = pd.DataFrame(rows)

    checklist_rows = [
        {
            "Check": "Required columns",
            "Result": "OK" if len(summary) > 0 and (summary["missing_required"] == "None").all() else "Needs attention",
            "Why it matters": "timestamp and total_gpu_power_w are required for energy integration.",
        },
        {
            "Check": "GPU utilization available",
            "Result": "OK" if len(summary) > 0 and summary["avg_gpu_util_percent"].notna().all() else "Missing",
            "Why it matters": "gpu_util_percent is used by the utilization-based GPU power-cap model.",
        },
        {
            "Check": "Multiple repeated runs",
            "Result": "OK" if len(summary) >= 2 else "Needs more runs",
            "Why it matters": "Multiple runs allow a representative averaged MLPerf profile and power variability estimate.",
        },
        {
            "Check": "Real timestamp intervals",
            "Result": "OK" if len(summary) > 0 and summary["median_sample_interval_s"].gt(0).all() else "Needs attention",
            "Why it matters": "The app uses measured delta_seconds instead of assuming a fixed interval.",
        },
    ]
    checklist = pd.DataFrame(checklist_rows)

    return summary, checklist

def create_power_price_overlay(cost_df: pd.DataFrame, title: str) -> go.Figure:
    df = add_clock_labels(cost_df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["elapsed_hours"],
        y=df["total_power_mw"],
        mode="lines",
        name="Power demand (MW)",
        line=dict(width=2.5),
        customdata=df[["clock_time", "price_period", "price_eur_per_kwh", "energy_kwh", "cost_eur"]],
        hovertemplate=(
            "Elapsed: %{x:.3f} h<br>"
            "Clock: %{customdata[0]}<br>"
            "Power: %{y:.3f} MW<br>"
            "Tariff: %{customdata[1]}<br>"
            "Price: %{customdata[2]:.3f} €/kWh<br>"
            "Energy step: %{customdata[3]:.3f} kWh<br>"
            "Cost step: %{customdata[4]:.2f} €<extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=df["elapsed_hours"],
        y=df["price_eur_per_kwh"],
        mode="lines",
        name="Electricity price (€/kWh)",
        yaxis="y2",
        line=dict(width=2, dash="dash"),
        customdata=df[["clock_time", "price_period"]],
        hovertemplate=(
            "Elapsed: %{x:.3f} h<br>"
            "Clock: %{customdata[0]}<br>"
            "Tariff: %{customdata[1]}<br>"
            "Price: %{y:.3f} €/kWh<extra></extra>"
        ),
    ))
    if "price_period" in df.columns:
        changes = df[df["price_period"].ne(df["price_period"].shift())]
        for _, row in changes.iloc[1:].iterrows():
            fig.add_vline(x=float(row["elapsed_hours"]), line_width=1, line_dash="dot", opacity=0.45)
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=70, t=80, b=55),
        xaxis=dict(title="Elapsed workload time (hours)", showgrid=True, zeroline=False),
        yaxis=dict(title="Power demand (MW)", rangemode="tozero", showgrid=True),
        yaxis2=dict(title="Electricity price (€/kWh)", overlaying="y", side="right", rangemode="tozero", showgrid=False),
    )
    return fig


def get_center_activity_columns(df: pd.DataFrame) -> list[str]:
    """Return center_X_active columns in numeric order."""
    cols = [c for c in df.columns if c.startswith("center_") and c.endswith("_active")]
    def center_no(col: str) -> int:
        try:
            return int(col.split("_")[1])
        except Exception:
            return 10**9
    return sorted(cols, key=center_no)


def build_scheduling_summary(schedule_df: pd.DataFrame, number_of_centers: int) -> pd.DataFrame:
    """
    Summarize a center scheduling matrix.

    This is a diagnostic table used to test whether the scheduling strategy behaves as intended:
    - active center count per timestep
    - per-center activation fairness
    - total center-time work units
    """
    df = schedule_df.copy()
    cols = get_center_activity_columns(df)
    if not cols:
        return pd.DataFrame()

    if "active_centers" not in df.columns:
        df["active_centers"] = df[cols].sum(axis=1)

    timesteps = max(len(df), 1)
    active_counts = df["active_centers"]
    center_runtime = df[cols].sum(axis=0)

    return pd.DataFrame(
        [
            {
                "Metric": "Timesteps in schedule",
                "Value": f"{timesteps}",
                "How to read it": "Number of measured workload samples for which a center schedule exists.",
            },
            {
                "Metric": "Average active centers",
                "Value": f"{active_counts.mean():.2f} of {number_of_centers}",
                "How to read it": "Mean number of centers receiving load at one timestep.",
            },
            {
                "Metric": "Minimum active centers",
                "Value": f"{int(active_counts.min())}",
                "How to read it": "Lowest simultaneous center count. Should never be below 1.",
            },
            {
                "Metric": "Maximum active centers",
                "Value": f"{int(active_counts.max())}",
                "How to read it": "Highest simultaneous center count. Should not exceed the sidebar maximum.",
            },
            {
                "Metric": "Total center-time work units",
                "Value": f"{float(active_counts.sum()):.0f}",
                "How to read it": "Sum of active centers over all timesteps. Useful for checking whether a strategy reduces or redistributes work in the simulated window.",
            },
            {
                "Metric": "Per-center active share range",
                "Value": f"{center_runtime.min() / timesteps * 100:.1f}% – {center_runtime.max() / timesteps * 100:.1f}%",
                "How to read it": "Fairness indicator. Rotating centers should be more balanced than same_centers_active.",
            },
        ]
    )


def build_center_runtime_table(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per center with active timestep count and share."""
    cols = get_center_activity_columns(schedule_df)
    if not cols:
        return pd.DataFrame()
    timesteps = max(len(schedule_df), 1)
    rows = []
    for col in cols:
        center_id = int(col.split("_")[1])
        active_steps = int(schedule_df[col].sum())
        rows.append(
            {
                "Center": f"Center {center_id}",
                "Active timesteps": active_steps,
                "Active share (%)": active_steps / timesteps * 100.0,
            }
        )
    return pd.DataFrame(rows)


def create_center_activity_heatmap(schedule_df: pd.DataFrame, max_timesteps: int = 200) -> go.Figure:
    """Create a paper-style heatmap: x=timestep, y=center, color=active/inactive."""
    cols = get_center_activity_columns(schedule_df)
    df = schedule_df.head(max_timesteps).copy()
    z = df[cols].T.values if cols else []
    y = [f"C{c.split('_')[1]}" for c in cols]
    x = df["timestep"].tolist() if "timestep" in df.columns else list(range(len(df)))

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            zmin=0,
            zmax=1,
            colorscale=[[0, "#e5e7eb"], [1, "#16a34a"]],
            colorbar=dict(title="Active", tickvals=[0, 1], ticktext=["No", "Yes"]),
            hovertemplate="Timestep %{x}<br>Center %{y}<br>Active: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Center activity schedule heatmap (first {min(max_timesteps, len(df))} timesteps)",
        template="plotly_white",
        height=max(420, min(900, 120 + 18 * max(len(cols), 1))),
        margin=dict(l=70, r=30, t=70, b=55),
        xaxis=dict(title="Timestep"),
        yaxis=dict(title="HPC center"),
    )
    return fig


def create_active_centers_figure(results_df: pd.DataFrame) -> go.Figure:
    """Line chart for simultaneous active center count."""
    x_col = "elapsed_hours" if "elapsed_hours" in results_df.columns else "timestep"
    fig = px.line(
        results_df,
        x=x_col,
        y="active_centers",
        title="Simultaneously active HPC centers over time",
        hover_data=["active_centers", "total_power_mw"],
    )
    fig.update_layout(
        template="plotly_white",
        height=430,
        xaxis_title="Elapsed workload time (hours)" if x_col == "elapsed_hours" else "Timestep",
        yaxis_title="Active centers",
    )
    return fig


def create_power_scheduling_comparison(baseline_results: pd.DataFrame, optimized_results: pd.DataFrame) -> go.Figure:
    """Paper-style power comparison for baseline vs scheduled scenario."""
    power_df = build_comparison_df(baseline_results, optimized_results, "total_power_mw")
    x_col = "elapsed_hours" if "elapsed_hours" in power_df.columns else "timestep"
    fig = px.line(
        power_df,
        x=x_col,
        y="total_power_mw",
        color="case",
        title="Grid power demand before and after workload scheduling",
        hover_data=["case", "total_power_mw"],
    )
    fig.update_layout(
        template="plotly_white",
        height=470,
        xaxis_title="Elapsed workload time (hours)" if x_col == "elapsed_hours" else "Timestep",
        yaxis_title="Total facility load on grid (MW)",
        legend_title="Case",
    )
    return fig

def create_grid_topology_figure(
    number_of_centers: int,
    max_active_centers: int,
    enable_load_balancing: bool,
):
    fig = go.Figure()

    centers_to_draw = min(number_of_centers, 50)

    edge_x = []
    edge_y = []

    node_x = [0]
    node_y = [0]
    node_text = ["External Grid<br>110 kV reference bus"]
    node_color = ["#2563eb"]
    node_size = [32]

    for center in range(1, centers_to_draw + 1):
        y = center - (centers_to_draw + 1) / 2

        is_active = True
        if enable_load_balancing:
            is_active = center <= max_active_centers

        color = "#16a34a" if is_active else "#9ca3af"

        edge_x.extend([0, 2, None])
        edge_y.extend([0, y, None])

        node_x.append(2)
        node_y.append(y)
        node_text.append(
            f"HPC Center {center}<br>"
            f"Connection: 110/20 kV<br>"
            f"Initial scheduling status: {'Active' if is_active else 'Inactive'}"
        )
        node_color.append(color)
        node_size.append(18)

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1.2, color="#6b7280"),
            hoverinfo="none",
            name="Connections",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            marker=dict(
                size=node_size,
                color=node_color,
                line=dict(width=1, color="#111827"),
            ),
            text=node_text,
            hoverinfo="text",
            name="Grid nodes",
        )
    )

    fig.update_layout(
        title="Assumption-Based HPC Grid Topology",
        height=620,
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=20, r=20, t=70, b=20),
    )

    return fig



def _set_loads_for_snapshot(net, center_load_map, workload_row: pd.Series) -> dict:
    """Apply one workload row to a pandapower network without changing the main simulation logic."""
    center_power_mw = float(workload_row.get("center_total_power_mw", 0.0))
    active_centers = 0
    total_p_mw = 0.0
    total_q_mvar = 0.0

    for center_id, load_indices in center_load_map.items():
        active_column = f"center_{center_id}_active"
        is_active = int(workload_row[active_column]) if active_column in workload_row else 1
        if is_active:
            active_centers += 1

        center_load_mw = center_power_mw if is_active else 0.0
        power_per_rack = center_load_mw / max(len(load_indices), 1)
        q_per_rack = power_per_rack * 0.33

        for load_idx in load_indices:
            net.load.at[load_idx, "p_mw"] = power_per_rack
            net.load.at[load_idx, "q_mvar"] = q_per_rack

        total_p_mw += center_load_mw
        total_q_mvar += center_load_mw * 0.33

    return {
        "active_centers": active_centers,
        "total_p_mw": total_p_mw,
        "total_q_mvar": total_q_mvar,
    }


def _select_peak_snapshot_row(workload_df: pd.DataFrame, number_of_centers: int) -> pd.Series:
    """Select the row with the highest scheduled total active power."""
    df = workload_df.copy()
    center_cols = get_center_activity_columns(df)
    if center_cols:
        df["_snapshot_active_centers"] = df[center_cols].sum(axis=1)
    else:
        df["_snapshot_active_centers"] = number_of_centers
    df["_snapshot_total_power_mw"] = df["center_total_power_mw"] * df["_snapshot_active_centers"]
    return df.loc[df["_snapshot_total_power_mw"].idxmax()]


def build_pandapower_snapshot(
    workload_df: pd.DataFrame,
    number_of_centers: int,
    clusters_per_center: int,
    racks_per_cluster: int,
    grid_backend: str = "Synthetic HPC grid",
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_simbench_loads: bool = True,
) -> dict:
    """Create a separate peak-load pandapower snapshot for dashboard inspection.

    It does not modify the existing time-series simulation. It rebuilds the same grid,
    applies the peak scheduled load, runs one AC power flow, and exposes net.res_* tables.
    """
    snapshot_row = _select_peak_snapshot_row(workload_df, number_of_centers)
    net, center_load_map = create_hpc_grid(
        number_of_centers=number_of_centers,
        clusters_per_center=clusters_per_center,
        racks_per_cluster=racks_per_cluster,
        grid_backend=grid_backend,
        simbench_code=simbench_code,
        include_existing_simbench_loads=include_existing_simbench_loads,
    )
    applied = _set_loads_for_snapshot(net, center_load_map, snapshot_row)
    try:
        pp.runpp(net, algorithm="nr", max_iteration=30)
        converged = bool(net.converged)
        error_message = ""
    except Exception as exc:
        converged = False
        error_message = str(exc)
    return {"net": net, "snapshot_row": snapshot_row, "applied": applied, "converged": converged, "error_message": error_message, "grid_backend": grid_backend, "simbench_code": simbench_code if grid_backend == "SimBench German benchmark grid" else ""}


def _join_result_table(element_df: pd.DataFrame, result_df: pd.DataFrame, keep_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Combine pandapower input element data with solved result data.

    Important: pandapower sometimes uses the same column names in the input table and
    result table, for example net.load["p_mw"] and net.res_load["p_mw"].
    Therefore every result column is prefixed with `res_` before joining.

    Example:
    - p_mw = configured/input active power
    - res_p_mw = solved/result active power after the power-flow calculation
    """
    if result_df is None or len(result_df) == 0:
        return pd.DataFrame()

    base = element_df.copy()
    if keep_cols is not None:
        base = base[[c for c in keep_cols if c in base.columns]]

    result_prefixed = result_df.copy().add_prefix("res_")
    df = base.join(result_prefixed, how="left")
    df.insert(0, "element_index", df.index)
    return df.reset_index(drop=True)


def build_pandapower_result_tables(snapshot: dict) -> dict[str, pd.DataFrame]:
    net = snapshot["net"]
    return {
        "bus": _join_result_table(net.bus, net.res_bus, ["name", "vn_kv", "type", "zone"]),
        "line": _join_result_table(net.line, net.res_line, ["name", "from_bus", "to_bus", "length_km", "max_i_ka"]),
        "trafo": _join_result_table(net.trafo, net.res_trafo, ["name", "hv_bus", "lv_bus", "sn_mva", "vn_hv_kv", "vn_lv_kv"]),
        "load": _join_result_table(net.load, net.res_load, ["name", "bus", "p_mw", "q_mvar"]),
        "ext_grid": _join_result_table(net.ext_grid, net.res_ext_grid, ["name", "bus", "vm_pu"]),
    }


def summarize_pandapower_snapshot(snapshot: dict) -> dict:
    net = snapshot["net"]
    applied = snapshot["applied"]

    bus_vm = pd.to_numeric(net.res_bus["vm_pu"], errors="coerce") if hasattr(net, "res_bus") and "vm_pu" in net.res_bus.columns else pd.Series(dtype=float)
    line_loading = pd.to_numeric(net.res_line["loading_percent"], errors="coerce") if hasattr(net, "res_line") and "loading_percent" in net.res_line.columns else pd.Series(dtype=float)
    trafo_loading = pd.to_numeric(net.res_trafo["loading_percent"], errors="coerce") if hasattr(net, "res_trafo") and "loading_percent" in net.res_trafo.columns else pd.Series(dtype=float)

    line_loss_mw = float(pd.to_numeric(net.res_line["pl_mw"], errors="coerce").sum()) if hasattr(net, "res_line") and "pl_mw" in net.res_line.columns else 0.0
    line_loss_mvar = float(pd.to_numeric(net.res_line["ql_mvar"], errors="coerce").sum()) if hasattr(net, "res_line") and "ql_mvar" in net.res_line.columns else 0.0
    trafo_loss_mw = float(pd.to_numeric(net.res_trafo["pl_mw"], errors="coerce").sum()) if hasattr(net, "res_trafo") and "pl_mw" in net.res_trafo.columns else 0.0
    trafo_loss_mvar = float(pd.to_numeric(net.res_trafo["ql_mvar"], errors="coerce").sum()) if hasattr(net, "res_trafo") and "ql_mvar" in net.res_trafo.columns else 0.0
    ext_p_mw = float(pd.to_numeric(net.res_ext_grid["p_mw"], errors="coerce").sum()) if hasattr(net, "res_ext_grid") and "p_mw" in net.res_ext_grid.columns else 0.0
    ext_q_mvar = float(pd.to_numeric(net.res_ext_grid["q_mvar"], errors="coerce").sum()) if hasattr(net, "res_ext_grid") and "q_mvar" in net.res_ext_grid.columns else 0.0
    apparent_mva = (ext_p_mw ** 2 + ext_q_mvar ** 2) ** 0.5
    power_factor = ext_p_mw / apparent_mva if apparent_mva > 0 else float("nan")

    min_bus_idx = int(bus_vm.idxmin()) if len(bus_vm) and bus_vm.notna().any() else -1
    max_line_idx = int(line_loading.idxmax()) if len(line_loading) and line_loading.notna().any() else -1
    max_trafo_idx = int(trafo_loading.idxmax()) if len(trafo_loading) and trafo_loading.notna().any() else -1

    total_losses_mw = line_loss_mw + trafo_loss_mw
    loss_pct = (total_losses_mw / ext_p_mw * 100.0) if ext_p_mw > 0 else 0.0

    return {
        "converged": snapshot["converged"],
        "active_centers": applied["active_centers"],
        "applied_load_p_mw": applied["total_p_mw"],
        "applied_load_q_mvar": applied["total_q_mvar"],
        "external_grid_p_mw": ext_p_mw,
        "external_grid_q_mvar": ext_q_mvar,
        "apparent_power_mva": apparent_mva,
        "power_factor": power_factor,
        "line_losses_mw": line_loss_mw,
        "transformer_losses_mw": trafo_loss_mw,
        "total_losses_mw": total_losses_mw,
        "loss_percent_of_supply": loss_pct,
        "line_losses_mvar": line_loss_mvar,
        "transformer_losses_mvar": trafo_loss_mvar,
        "min_voltage_pu": float(bus_vm.min()) if len(bus_vm) else float("nan"),
        "max_voltage_pu": float(bus_vm.max()) if len(bus_vm) else float("nan"),
        "mean_voltage_pu": float(bus_vm.mean()) if len(bus_vm) else float("nan"),
        "std_voltage_pu": float(bus_vm.std()) if len(bus_vm) else float("nan"),
        "voltage_violations": int(((bus_vm < 0.95) | (bus_vm > 1.05)).sum()) if len(bus_vm) else 0,
        "worst_voltage_bus": net.bus.at[min_bus_idx, "name"] if min_bus_idx in net.bus.index else "N/A",
        "max_line_loading_percent": float(line_loading.max()) if len(line_loading) else float("nan"),
        "p95_line_loading_percent": float(line_loading.quantile(0.95)) if len(line_loading) else float("nan"),
        "line_overloads": int((line_loading > 100.0).sum()) if len(line_loading) else 0,
        "worst_line": net.line.at[max_line_idx, "name"] if max_line_idx in net.line.index else "N/A",
        "max_trafo_loading_percent": float(trafo_loading.max()) if len(trafo_loading) else float("nan"),
        "p95_trafo_loading_percent": float(trafo_loading.quantile(0.95)) if len(trafo_loading) else float("nan"),
        "trafo_overloads": int((trafo_loading > 100.0).sum()) if len(trafo_loading) else 0,
        "worst_trafo": net.trafo.at[max_trafo_idx, "name"] if max_trafo_idx in net.trafo.index else "N/A",
    }



def diagnose_invalid_powerflow_snapshot(summary: dict, snapshot: dict) -> list[str]:
    """Return human-readable reasons when a pandapower snapshot is not usable."""
    reasons: list[str] = []

    if not bool(summary.get("converged", False)):
        msg = snapshot.get("error_message", "")
        if msg:
            reasons.append(f"AC power flow did not converge: {msg}")
        else:
            reasons.append("AC power flow did not converge for this grid-load combination.")

    numeric_checks = {
        "minimum voltage": summary.get("min_voltage_pu"),
        "maximum line loading": summary.get("max_line_loading_percent"),
        "maximum transformer loading": summary.get("max_trafo_loading_percent"),
        "power factor": summary.get("power_factor"),
    }
    for label, value in numeric_checks.items():
        if value is None or pd.isna(value):
            reasons.append(f"Pandapower returned no valid {label} value.")

    applied_p = float(summary.get("applied_load_p_mw", 0.0) or 0.0)
    ext_p = float(summary.get("external_grid_p_mw", 0.0) or 0.0)
    if applied_p > 0.001 and abs(ext_p) < 1e-9:
        reasons.append(
            "The snapshot applies HPC load, but the external-grid active-power result is 0 MW. "
            "This usually means the power-flow result is invalid or no slack result was produced."
        )

    return reasons


def build_invalid_snapshot_recommendations(snapshot: dict, summary: dict) -> pd.DataFrame:
    grid_backend = snapshot.get("grid_backend", "")
    simbench_code = snapshot.get("simbench_code", "")
    applied_p = float(summary.get("applied_load_p_mw", 0.0) or 0.0)

    rows = [
        {
            "Issue": "Grid-load combination is not physically solvable",
            "Meaning": "The selected grid cannot supply the injected HPC load with a valid AC power-flow solution.",
            "Recommended action": "Reduce centers/nodes or choose a stronger grid backend.",
        },
        {
            "Issue": "Applied HPC load",
            "Meaning": f"The snapshot tried to inject about {applied_p:.2f} MW of HPC load.",
            "Recommended action": "Compare this load with the grid level: LV grids are for small local loads; MV/HV grids are more suitable for MW-scale studies.",
        },
    ]

    if grid_backend == "SimBench German benchmark grid":
        rows.append(
            {
                "Issue": "SimBench interpretation",
                "Meaning": f"Selected SimBench code: {simbench_code}. SimBench networks are German benchmark grids, not dedicated HPC connection studies.",
                "Recommended action": "Use LV for small-load tests, MV for larger distribution-grid stress tests, and the synthetic HPC grid for controlled 110/20/0.4 kV HPC scenarios.",
            }
        )
        if "-LV-" in simbench_code or simbench_code.startswith("1-LV"):
            rows.append(
                {
                    "Issue": "LV grid selected",
                    "Meaning": "A low-voltage rural grid is normally not sized for multi-MW HPC loads.",
                    "Recommended action": "Try an MV SimBench model first, or reduce to 1 center with very few nodes for LV tests.",
                }
            )

    return pd.DataFrame(rows)


def create_layered_grid_figure(number_of_centers: int, clusters_per_center: int, racks_per_cluster: int, snapshot_summary: dict | None = None) -> go.Figure:
    """Layered electrical abstraction of the pandapower network: 110 kV → 20 kV → 0.4 kV loads."""
    fig = go.Figure()
    centers_to_draw = min(number_of_centers, 12)
    title_note = f"showing {centers_to_draw} of {number_of_centers} centers" if centers_to_draw < number_of_centers else f"showing all {number_of_centers} centers"
    layer_x = {"External grid<br>110 kV": 0, "Center connection<br>110 kV": 1.8, "Campus bus<br>20 kV": 3.6, "Cluster feeders<br>20 kV": 5.4, "Rack loads<br>0.4 kV": 7.2}
    for label, x in layer_x.items():
        fig.add_annotation(x=x, y=centers_to_draw / 2 + 1.4, text=label, showarrow=False, align="center", font=dict(size=12))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["External Grid"], textposition="bottom center", marker=dict(size=34, line=dict(width=1)), name="External grid", hovertemplate="External grid / slack bus<br>Voltage setpoint: 1.0 pu<extra></extra>"))
    edge_x, edge_y, node_x, node_y, node_text, node_size = [], [], [], [], [], []
    for center in range(1, centers_to_draw + 1):
        y = center - (centers_to_draw + 1) / 2
        xs = [1.8, 3.6, 5.4, 7.2]
        labels = [
            f"Center {center}<br>110 kV connection bus",
            f"Center {center}<br>110/20 kV transformer + 20 kV campus bus",
            f"Center {center}<br>{clusters_per_center} cluster feeders and 20/0.4 kV transformers",
            f"Center {center}<br>{clusters_per_center * racks_per_cluster} rack loads",
        ]
        points = [(0, 0), (1.8, y), (3.6, y), (5.4, y), (7.2, y)]
        for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
            edge_x.extend([x1, x2, None]); edge_y.extend([y1, y2, None])
        node_x.extend(xs); node_y.extend([y] * 4); node_text.extend(labels); node_size.extend([16, 18, 18, 15])
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1.2), hoverinfo="skip", name="Electrical connections"))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers", marker=dict(size=node_size, line=dict(width=1)), text=node_text, hoverinfo="text", name="Network elements"))
    if snapshot_summary:
        fig.add_annotation(x=7.2, y=-(centers_to_draw / 2 + 1.2), showarrow=False, align="left", text=(f"Peak snapshot: {snapshot_summary['active_centers']} active centers, {snapshot_summary['applied_load_p_mw']:.2f} MW load<br>Min voltage: {snapshot_summary['min_voltage_pu']:.3f} pu · Max trafo: {snapshot_summary['max_trafo_loading_percent']:.1f}% · Max line: {snapshot_summary['max_line_loading_percent']:.1f}%"))
    fig.update_layout(title=f"Layered pandapower grid abstraction ({title_note})", template="plotly_white", height=650, showlegend=False, margin=dict(l=30, r=30, t=80, b=40), xaxis=dict(showgrid=False, zeroline=False, visible=False), yaxis=dict(showgrid=False, zeroline=False, visible=False))
    return fig





def _extract_hpc_center_summary(net) -> pd.DataFrame:
    """Return one row per modeled HPC center using actual pandapower load/bus data."""
    if not hasattr(net, "load") or len(net.load) == 0:
        return pd.DataFrame()

    loads = net.load.copy()
    name_series = loads.get("name", pd.Series(index=loads.index, dtype=object)).astype(str)
    type_series = loads.get("type", pd.Series(index=loads.index, dtype=object)).astype(str).str.upper()
    hpc_mask = type_series.eq("HPC") | name_series.str.upper().str.contains("HPC CENTER", na=False)
    hpc_loads = loads[hpc_mask].copy()
    if hpc_loads.empty:
        return pd.DataFrame()

    # Extract center id from names like "HPC Center 3 / Rack 4 (...)".
    extracted = name_series.loc[hpc_loads.index].str.extract(r"HPC\s*Center\s*(\d+)", expand=False)
    hpc_loads["center_id"] = pd.to_numeric(extracted, errors="coerce").fillna(0).astype(int)
    if (hpc_loads["center_id"] == 0).any():
        hpc_loads.loc[hpc_loads["center_id"] == 0, "center_id"] = range(1, int((hpc_loads["center_id"] == 0).sum()) + 1)

    rows = []
    conn_map = net.get("hpc_center_connection_map", {}) if isinstance(net, dict) or hasattr(net, "get") else {}

    for center_id, group in hpc_loads.groupby("center_id"):
        hpc_bus = int(group["bus"].iloc[0]) if "bus" in group.columns and len(group) else None
        conn = conn_map.get(int(center_id), {}) if isinstance(conn_map, dict) else {}
        grid_bus = conn.get("grid_bus", None)
        service_line = conn.get("service_line", None)
        vn_kv = float(net.bus.at[hpc_bus, "vn_kv"]) if hpc_bus in net.bus.index and "vn_kv" in net.bus.columns else float("nan")
        vm_pu = float(net.res_bus.at[hpc_bus, "vm_pu"]) if hasattr(net, "res_bus") and hpc_bus in net.res_bus.index and "vm_pu" in net.res_bus.columns else float("nan")
        p_mw = float(group.get("p_mw", pd.Series(dtype=float)).sum()) if "p_mw" in group.columns else 0.0
        q_mvar = float(group.get("q_mvar", pd.Series(dtype=float)).sum()) if "q_mvar" in group.columns else 0.0
        line_loading = float("nan")
        if service_line is not None and hasattr(net, "res_line") and service_line in net.res_line.index and "loading_percent" in net.res_line.columns:
            line_loading = float(net.res_line.at[service_line, "loading_percent"])
        rows.append({
            "center_id": int(center_id),
            "hpc_bus": hpc_bus,
            "grid_bus": grid_bus,
            "service_line": service_line,
            "vn_kv": vn_kv,
            "vm_pu": vm_pu,
            "p_mw": p_mw,
            "q_mvar": q_mvar,
            "rack_load_elements": int(len(group)),
            "service_line_loading_percent": line_loading,
        })

    return pd.DataFrame(rows).sort_values("center_id")


def create_hpc_engineering_diagram(
    net,
    number_of_centers: int,
    clusters_per_center: int,
    racks_per_cluster: int,
    snapshot_summary: dict | None = None,
    max_centers_to_draw: int = 12,
) -> go.Figure:
    """Clear engineering-style diagram: Grid → connection → HPC Center → racks.

    This is not a force-directed graph. It is a readable facility-connection diagram
    based on the actual pandapower HPC loads/buses where available.
    """
    fig = go.Figure()
    hpc_df = _extract_hpc_center_summary(net)
    if hpc_df.empty:
        # Fallback for synthetic/older networks if the HPC load names are unavailable.
        centers = list(range(1, min(number_of_centers, max_centers_to_draw) + 1))
        hpc_df = pd.DataFrame({
            "center_id": centers,
            "hpc_bus": [None] * len(centers),
            "grid_bus": [None] * len(centers),
            "service_line": [None] * len(centers),
            "vn_kv": [float("nan")] * len(centers),
            "vm_pu": [float("nan")] * len(centers),
            "p_mw": [float(snapshot_summary.get("applied_load_p_mw", 0.0) / max(number_of_centers, 1)) if snapshot_summary else 0.0] * len(centers),
            "q_mvar": [0.0] * len(centers),
            "rack_load_elements": [clusters_per_center * racks_per_cluster] * len(centers),
            "service_line_loading_percent": [float("nan")] * len(centers),
        })

    hpc_df = hpc_df.head(max_centers_to_draw).copy()
    shown = len(hpc_df)
    title_note = f"showing {shown} of {len(_extract_hpc_center_summary(net)) or number_of_centers} HPC centers"

    # Fixed readable columns
    x_grid, x_connection, x_line, x_center, x_racks = 0.0, 2.0, 3.2, 4.7, 6.2
    header_y = shown + 1.0
    headers = [
        (x_grid, "External / upstream grid"),
        (x_connection, "Grid connection bus"),
        (x_line, "Service cable / line"),
        (x_center, "HPC Center"),
        (x_racks, "Aggregated racks / loads"),
    ]
    for x, label in headers:
        fig.add_annotation(x=x, y=header_y, text=f"<b>{label}</b>", showarrow=False, align="center", font=dict(size=12))

    # Upstream source node
    fig.add_trace(go.Scatter(
        x=[x_grid], y=[shown / 2], mode="markers+text", name="External grid",
        marker=dict(symbol="star", size=28, color="#2563eb", line=dict(width=1, color="#111827")),
        text=["Grid<br>source"], textposition="bottom center",
        hovertemplate="External grid / slack source<extra></extra>",
    ))

    edge_x, edge_y = [], []
    service_x, service_y = [], []
    center_x, center_y, center_text, center_hover, center_size, center_color = [], [], [], [], [], []
    conn_x, conn_y, conn_hover = [], [], []
    rack_x, rack_y, rack_text, rack_hover = [], [], [], []

    total_hpc_mw = hpc_df["p_mw"].sum() if "p_mw" in hpc_df.columns else 0.0
    for pos_idx, row in enumerate(hpc_df.itertuples(index=False), start=1):
        y = shown - pos_idx + 1
        center_id = int(getattr(row, "center_id"))
        p_mw = float(getattr(row, "p_mw", 0.0) or 0.0)
        q_mvar = float(getattr(row, "q_mvar", 0.0) or 0.0)
        racks = int(getattr(row, "rack_load_elements", 0) or 0)
        vm_pu = float(getattr(row, "vm_pu", float("nan")))
        vn_kv = float(getattr(row, "vn_kv", float("nan")))
        hpc_bus = getattr(row, "hpc_bus", None)
        grid_bus = getattr(row, "grid_bus", None)
        service_line = getattr(row, "service_line", None)
        line_loading = float(getattr(row, "service_line_loading_percent", float("nan")))

        # main backbone edges
        edge_x.extend([x_grid, x_connection, None])
        edge_y.extend([shown / 2, y, None])
        service_x.extend([x_connection, x_center, None])
        service_y.extend([y, y, None])
        edge_x.extend([x_center, x_racks, None])
        edge_y.extend([y, y, None])

        conn_x.append(x_connection)
        conn_y.append(y)
        conn_hover.append(
            f"<b>Grid connection point for HPC Center {center_id}</b>"
            f"<br>SimBench / grid bus: {grid_bus}"
            f"<br>HPC center bus: {hpc_bus}"
            f"<br>Voltage level: {vn_kv:.3g} kV"
            f"<br>Bus voltage: {vm_pu:.4f} pu"
        )

        center_x.append(x_center)
        center_y.append(y)
        center_text.append(f"HPC {center_id}<br>{p_mw:.2f} MW")
        center_hover.append(
            f"<b>HPC Center {center_id}</b>"
            f"<br>Modeled as aggregated pandapower loads"
            f"<br>Active power: {p_mw:.4f} MW"
            f"<br>Reactive power: {q_mvar:.4f} MVAr"
            f"<br>HPC bus: {hpc_bus}"
            f"<br>Voltage: {vm_pu:.4f} pu"
            f"<br>Service line: {service_line}"
            f"<br>Service line loading: {line_loading:.2f}%"
        )
        center_size.append(max(24, min(54, 24 + 8 * (p_mw ** 0.5))))
        center_color.append(get_voltage_band_color(vm_pu))

        rack_x.append(x_racks)
        rack_y.append(y)
        rack_text.append(f"{racks}<br>rack loads")
        rack_hover.append(
            f"<b>Aggregated rack/load elements</b>"
            f"<br>HPC Center: {center_id}"
            f"<br>Rack/load elements in net.load: {racks}"
            f"<br>Clusters × racks setting: {clusters_per_center} × {racks_per_cluster}"
        )

    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", name="Electrical connection path",
        line=dict(color="#94a3b8", width=2.0), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=service_x, y=service_y, mode="lines", name="HPC service cable / line",
        line=dict(color="#f97316", width=4, dash="dash"), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=conn_x, y=conn_y, mode="markers", name="Grid connection buses",
        marker=dict(symbol="circle", size=13, color="#64748b", line=dict(width=1.0, color="#111827")),
        text=conn_hover, hoverinfo="text",
    ))
    fig.add_trace(go.Scatter(
        x=center_x, y=center_y, mode="markers+text", name="HPC Centers",
        marker=dict(symbol="square", size=center_size, color=center_color, line=dict(width=2, color="#7c2d12")),
        text=center_text, textposition="middle center", textfont=dict(color="white", size=11),
        hovertext=center_hover, hoverinfo="text",
    ))
    fig.add_trace(go.Scatter(
        x=rack_x, y=rack_y, mode="markers+text", name="Rack/load aggregation",
        marker=dict(symbol="square-open", size=24, color="#0f172a", line=dict(width=2, color="#0f172a")),
        text=rack_text, textposition="middle right", hovertext=rack_hover, hoverinfo="text",
    ))

    # Summary annotation
    if snapshot_summary:
        fig.add_annotation(
            x=x_center,
            y=-0.6,
            showarrow=False,
            align="center",
            text=(
                f"<b>Peak snapshot summary</b><br>"
                f"Applied HPC load: {snapshot_summary.get('applied_load_p_mw', total_hpc_mw):.2f} MW · "
                f"External grid: {snapshot_summary.get('external_grid_p_mw', 0.0):.2f} MW · "
                f"Worst voltage: {snapshot_summary.get('min_voltage_pu', float('nan')):.4f} pu · "
                f"Max line/trafo: {snapshot_summary.get('max_line_loading_percent', float('nan')):.1f}% / {snapshot_summary.get('max_trafo_loading_percent', float('nan')):.1f}%"
            ),
        )

    fig.update_layout(
        title=f"HPC engineering diagram — Grid connection to modeled HPC centers ({title_note})",
        template="plotly_white",
        height=max(560, 90 * shown + 220),
        margin=dict(l=35, r=35, t=90, b=80),
        xaxis=dict(visible=False, showgrid=False, zeroline=False, range=[-0.4, 7.0]),
        yaxis=dict(visible=False, showgrid=False, zeroline=False, range=[-1.0, shown + 1.4]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig

def get_voltage_band_color(vm_pu):
    if pd.isna(vm_pu):
        return "#9ca3af"
    if vm_pu < 0.95 or vm_pu > 1.05:
        return "#dc2626"
    if vm_pu < 0.97 or vm_pu > 1.03:
        return "#f59e0b"
    return "#16a34a"



def _bus_position_map(net, graph_nodes):
    """Return stable x/y positions for pandapower buses."""
    if hasattr(net, "bus_geodata") and isinstance(net.bus_geodata, pd.DataFrame) and not net.bus_geodata.empty:
        if {"x", "y"}.issubset(set(net.bus_geodata.columns)):
            geo = net.bus_geodata.dropna(subset=["x", "y"])
            pos = {int(idx): (float(row["x"]), float(row["y"])) for idx, row in geo.iterrows() if int(idx) in graph_nodes}
            if len(pos) >= max(3, int(0.5 * len(graph_nodes))):
                missing = [n for n in graph_nodes if n not in pos]
                if missing:
                    xs = [p[0] for p in pos.values()]
                    ys = [p[1] for p in pos.values()]
                    cx = sum(xs) / len(xs)
                    cy = sum(ys) / len(ys)
                    for i, n in enumerate(missing):
                        pos[n] = (cx + 0.01 * (i % 10), cy + 0.01 * (i // 10))
                return pos

    G = nx.Graph()
    G.add_nodes_from(graph_nodes)
    if hasattr(net, "line"):
        for _, row in net.line.iterrows():
            try:
                if bool(row.get("in_service", True)):
                    G.add_edge(int(row["from_bus"]), int(row["to_bus"]))
            except Exception:
                continue
    if hasattr(net, "trafo"):
        for _, row in net.trafo.iterrows():
            try:
                if bool(row.get("in_service", True)):
                    G.add_edge(int(row["hv_bus"]), int(row["lv_bus"]))
            except Exception:
                continue
    return nx.spring_layout(G, seed=42, k=1 / max(len(graph_nodes), 1) ** 0.5)


def _edge_bucket(loading_percent):
    if pd.isna(loading_percent):
        return "unknown", "#9ca3af", 1.4
    if loading_percent >= 100:
        return ">=100% overload", "#dc2626", 5.2
    if loading_percent >= 80:
        return "80–100% high", "#f97316", 4.0
    if loading_percent >= 50:
        return "50–80% medium", "#f59e0b", 3.0
    return "0–50% low", "#94a3b8", 1.6


def create_actual_pandapower_network_figure(net, max_buses: int = 260, focus_worst_area: bool = False, hops: int = 2) -> go.Figure:
    """Safe actual pandapower topology view.

    Draws real buses, lines/cables and transformers. Load elements are not drawn
    as separate nodes because SimBench can contain thousands of loads; they are
    attached to buses and visible in hover/count tables.
    """
    fig = go.Figure()

    if not hasattr(net, "bus") or net.bus.empty:
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, text="No pandapower bus table available.")
        fig.update_layout(template="plotly_white", height=420, xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    G = nx.Graph()
    all_buses = [int(i) for i in net.bus.index]
    G.add_nodes_from(all_buses)

    line_loading = pd.Series(dtype=float)
    if hasattr(net, "res_line") and "loading_percent" in net.res_line.columns:
        line_loading = pd.to_numeric(net.res_line["loading_percent"], errors="coerce")

    trafo_loading = pd.Series(dtype=float)
    if hasattr(net, "res_trafo") and "loading_percent" in net.res_trafo.columns:
        trafo_loading = pd.to_numeric(net.res_trafo["loading_percent"], errors="coerce")

    if hasattr(net, "line"):
        for idx, row in net.line.iterrows():
            if not bool(row.get("in_service", True)):
                continue
            fb, tb = int(row["from_bus"]), int(row["to_bus"])
            G.add_edge(fb, tb, kind="line", element_index=int(idx), loading=float(line_loading.get(idx, float("nan"))))

    if hasattr(net, "trafo"):
        for idx, row in net.trafo.iterrows():
            if not bool(row.get("in_service", True)):
                continue
            hv, lv = int(row["hv_bus"]), int(row["lv_bus"])
            G.add_edge(hv, lv, kind="trafo", element_index=int(idx), loading=float(trafo_loading.get(idx, float("nan"))))

    graph_nodes = all_buses
    subtitle = "full bus/line/transformer topology"
    bus_vm_full = pd.Series(index=net.bus.index, dtype=float)
    if hasattr(net, "res_bus") and "vm_pu" in net.res_bus.columns:
        bus_vm_full = pd.to_numeric(net.res_bus["vm_pu"], errors="coerce")

    if focus_worst_area and bus_vm_full.notna().any():
        center = int(bus_vm_full.idxmin())
        try:
            lengths = nx.single_source_shortest_path_length(G, center, cutoff=max(1, int(hops)))
            graph_nodes = sorted(list(lengths.keys()))
            subtitle = f"local topology around worst-voltage bus {center} ({hops} hops)"
        except Exception:
            graph_nodes = all_buses

    if len(graph_nodes) > max_buses:
        if bus_vm_full.notna().any():
            center = int(bus_vm_full.idxmin())
            lengths = nx.single_source_shortest_path_length(G, center, cutoff=4)
            graph_nodes = sorted(list(lengths.keys()))[:max_buses]
            subtitle = f"limited topology around worst-voltage bus {center} (max {max_buses} buses)"
        else:
            graph_nodes = all_buses[:max_buses]
            subtitle = f"limited topology (first {max_buses} buses)"

    H = G.subgraph(graph_nodes).copy()
    pos = _bus_position_map(net, list(H.nodes()))

    edge_groups = {}
    for u, v, data in H.edges(data=True):
        kind = data.get("kind", "line")
        loading = data.get("loading", float("nan"))
        element_index = data.get("element_index")
        edge_name = ""
        if kind == "line" and element_index is not None and hasattr(net, "line") and element_index in net.line.index:
            edge_name = str(net.line.at[element_index, "name"]) if "name" in net.line.columns else ""
        if kind == "trafo":
            key = ("Transformer", "#7c3aed", 3.4, "dot")
        elif "HPC CENTER" in edge_name.upper() or "SERVICE CONNECTION" in edge_name.upper():
            key = ("HPC service connection", "#f97316", 4.6, "dash")
        else:
            label, color, width = _edge_bucket(loading)
            key = (f"Line/cable {label}", color, width, "solid")
        edge_groups.setdefault(key, {"x": [], "y": []})
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_groups[key]["x"].extend([x0, x1, None])
        edge_groups[key]["y"].extend([y0, y1, None])

    for (name, color, width, dash), data in edge_groups.items():
        fig.add_trace(go.Scattergl(
            x=data["x"], y=data["y"], mode="lines", name=name,
            line=dict(color=color, width=width, dash=dash), hoverinfo="skip"
        ))

    bus_df = net.bus.loc[list(H.nodes())].copy()
    bus_df["bus_index"] = bus_df.index.astype(int)
    bus_df["vm_pu"] = bus_vm_full.reindex(bus_df.index)
    bus_df["voltage_color"] = bus_df["vm_pu"].apply(get_voltage_band_color)
    bus_df["x"] = bus_df["bus_index"].map(lambda n: pos[int(n)][0])
    bus_df["y"] = bus_df["bus_index"].map(lambda n: pos[int(n)][1])
    load_counts = net.load.groupby("bus").size() if hasattr(net, "load") and len(net.load) else pd.Series(dtype=int)
    bus_df["load_elements"] = bus_df["bus_index"].map(load_counts).fillna(0).astype(int)
    bus_df["name"] = bus_df.get("name", pd.Series(index=bus_df.index, dtype=str)).fillna("")
    bus_df["vn_kv"] = pd.to_numeric(bus_df.get("vn_kv"), errors="coerce")

    hpc_loads = pd.DataFrame()
    if hasattr(net, "load") and len(net.load):
        load_type = net.load.get("type", pd.Series(index=net.load.index, dtype=object)).astype(str).str.upper()
        load_name = net.load.get("name", pd.Series(index=net.load.index, dtype=object)).astype(str).str.upper()
        hpc_loads = net.load[(load_type == "HPC") | load_name.str.contains("HPC", na=False)].copy()

    if len(hpc_loads):
        hpc_counts = hpc_loads.groupby("bus").size()
        hpc_p = hpc_loads.groupby("bus")["p_mw"].sum() if "p_mw" in hpc_loads.columns else pd.Series(dtype=float)
        hpc_q = hpc_loads.groupby("bus")["q_mvar"].sum() if "q_mvar" in hpc_loads.columns else pd.Series(dtype=float)
    else:
        hpc_counts = pd.Series(dtype=int)
        hpc_p = pd.Series(dtype=float)
        hpc_q = pd.Series(dtype=float)

    bus_df["is_hpc_bus"] = bus_df["bus_index"].map(hpc_counts).fillna(0).astype(int) > 0
    bus_df["hpc_load_elements"] = bus_df["bus_index"].map(hpc_counts).fillna(0).astype(int)
    bus_df["hpc_p_mw"] = bus_df["bus_index"].map(hpc_p).fillna(0.0)
    bus_df["hpc_q_mvar"] = bus_df["bus_index"].map(hpc_q).fillna(0.0)

    bus_hover = (
        "Bus " + bus_df["bus_index"].astype(str) +
        "<br>Name: " + bus_df["name"].astype(str) +
        "<br>Voltage level: " + bus_df["vn_kv"].round(3).astype(str) + " kV" +
        "<br>Voltage: " + bus_df["vm_pu"].round(4).astype(str) + " pu" +
        "<br>All load elements attached: " + bus_df["load_elements"].astype(str) +
        "<br>HPC rack/load elements: " + bus_df["hpc_load_elements"].astype(str) +
        "<br>HPC load: " + bus_df["hpc_p_mw"].round(4).astype(str) + " MW / " + bus_df["hpc_q_mvar"].round(4).astype(str) + " MVAr"
    )

    normal_bus_df = bus_df[~bus_df["is_hpc_bus"]].copy()
    hpc_bus_df = bus_df[bus_df["is_hpc_bus"]].copy()

    if len(normal_bus_df):
        fig.add_trace(go.Scattergl(
            x=normal_bus_df["x"], y=normal_bus_df["y"], mode="markers", name="Grid buses",
            marker=dict(size=8, color=normal_bus_df["voltage_color"], line=dict(width=0.8, color="#111827")),
            text=bus_hover.loc[normal_bus_df.index], hoverinfo="text"
        ))

    if len(hpc_bus_df):
        hpc_sizes = (18 + 4 * hpc_bus_df["hpc_p_mw"].clip(lower=0).pow(0.5)).clip(18, 36)
        fig.add_trace(go.Scattergl(
            x=hpc_bus_df["x"], y=hpc_bus_df["y"], mode="markers+text", name="HPC center connection buses",
            marker=dict(symbol="square", size=hpc_sizes, color="#f97316", line=dict(width=2.0, color="#7c2d12")),
            text=[f"HPC<br>{i+1}" for i in range(len(hpc_bus_df))],
            textposition="top center",
            customdata=hpc_bus_df[["bus_index", "hpc_load_elements", "hpc_p_mw", "hpc_q_mvar", "vm_pu"]].to_numpy(),
            hovertemplate=(
                "<b>HPC connection bus %{customdata[0]}</b>"
                "<br>HPC rack/load elements: %{customdata[1]}"
                "<br>Assigned HPC load: %{customdata[2]:.4f} MW / %{customdata[3]:.4f} MVAr"
                "<br>Voltage: %{customdata[4]:.4f} pu"
                "<extra></extra>"
            ),
        ))

    if hasattr(net, "ext_grid") and len(net.ext_grid):
        ext_buses = [int(b) for b in net.ext_grid["bus"].tolist() if int(b) in H.nodes]
        if ext_buses:
            fig.add_trace(go.Scattergl(
                x=[pos[b][0] for b in ext_buses], y=[pos[b][1] for b in ext_buses],
                mode="markers", name="External grid", marker=dict(symbol="star", size=20, color="#2563eb", line=dict(width=1, color="#111827")),
                text=[f"External grid / slack bus {b}" for b in ext_buses], hoverinfo="text"
            ))

    trafo_mid_x, trafo_mid_y, trafo_text = [], [], []
    if hasattr(net, "trafo"):
        for idx, row in net.trafo.iterrows():
            hv, lv = int(row["hv_bus"]), int(row["lv_bus"])
            if hv in H.nodes and lv in H.nodes:
                x0, y0 = pos[hv]
                x1, y1 = pos[lv]
                loading = float(trafo_loading.get(idx, float("nan")))
                trafo_mid_x.append((x0 + x1) / 2)
                trafo_mid_y.append((y0 + y1) / 2)
                trafo_text.append(f"Transformer {idx}<br>{hv} → {lv}<br>loading={loading:.1f}%<br>sn_mva={row.get('sn_mva', '')}")
    if trafo_mid_x:
        fig.add_trace(go.Scattergl(
            x=trafo_mid_x, y=trafo_mid_y, mode="markers", name="Transformer markers",
            marker=dict(symbol="diamond", size=14, color="#7c3aed", line=dict(width=1, color="#111827")),
            text=trafo_text, hoverinfo="text"
        ))

    fig.update_layout(
        title=f"Actual pandapower topology — {subtitle}<br><sup>Loads are attached to buses; they are not drawn as separate nodes.</sup>",
        template="plotly_white",
        height=720,
        margin=dict(l=20, r=20, t=90, b=20),
        xaxis=dict(visible=False, showgrid=False, zeroline=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def create_pyvis_pandapower_topology_html(
    net,
    max_buses: int = 240,
    focus_worst_area: bool = False,
    hops: int = 2,
) -> str:
    """Interactive PyVis topology view for pandapower networks.

    Visualization only: buses, lines/cables, transformers, external grids and
    explicit visual HPC facility nodes linked to the actual HPC load buses.
    """
    if Network is None:
        return """
        <div style='font-family:Arial;padding:18px;border:1px solid #fecaca;border-radius:12px;background:#fff1f2;color:#7f1d1d;'>
        <b>PyVis is not installed.</b><br>
        Run <code>pip install pyvis</code> or install from <code>requirements.txt</code>.
        </div>
        """

    if not hasattr(net, "bus") or len(net.bus) == 0:
        return "<div>No pandapower bus table available.</div>"

    G = nx.Graph()
    all_buses = [int(i) for i in net.bus.index]
    G.add_nodes_from(all_buses)

    if hasattr(net, "line") and len(net.line):
        for idx, row in net.line.iterrows():
            if bool(row.get("in_service", True)):
                G.add_edge(int(row["from_bus"]), int(row["to_bus"]), kind="line", element_index=int(idx))

    if hasattr(net, "trafo") and len(net.trafo):
        for idx, row in net.trafo.iterrows():
            if bool(row.get("in_service", True)):
                G.add_edge(int(row["hv_bus"]), int(row["lv_bus"]), kind="trafo", element_index=int(idx))

    bus_vm = pd.Series(index=net.bus.index, dtype=float)
    if hasattr(net, "res_bus") and "vm_pu" in net.res_bus.columns:
        bus_vm = pd.to_numeric(net.res_bus["vm_pu"], errors="coerce")

    nodes_to_show = all_buses
    subtitle = "full topology"
    if focus_worst_area and bus_vm.notna().any():
        center = int(bus_vm.idxmin())
        try:
            lengths = nx.single_source_shortest_path_length(G, center, cutoff=max(1, int(hops)))
            nodes_to_show = sorted(int(n) for n in lengths.keys())
            subtitle = f"local neighborhood around worst-voltage bus {center}"
        except Exception:
            nodes_to_show = all_buses

    if len(nodes_to_show) > max_buses:
        keep = set()
        if bus_vm.notna().any():
            center = int(bus_vm.idxmin())
            try:
                keep.update(nx.single_source_shortest_path_length(G, center, cutoff=3).keys())
            except Exception:
                pass
        if hasattr(net, "ext_grid") and len(net.ext_grid):
            keep.update(int(b) for b in net.ext_grid["bus"].tolist())
        hpc_summary = _extract_hpc_center_summary(net)
        if len(hpc_summary):
            keep.update(int(b) for b in hpc_summary["hpc_bus"].dropna().astype(int).tolist())
            keep.update(int(b) for b in hpc_summary["grid_bus"].dropna().astype(int).tolist())
        if len(keep) < max_buses:
            keep.update(all_buses[: max_buses - len(keep)])
        nodes_to_show = sorted(list(keep))[:max_buses]
        subtitle = f"limited topology ({len(nodes_to_show)} buses shown)"

    H = G.subgraph(nodes_to_show).copy()
    net_vis = Network(height="760px", width="100%", bgcolor="#ffffff", font_color="#0f172a", directed=False)
    net_vis.barnes_hut(gravity=-2200, central_gravity=0.18, spring_length=115, spring_strength=0.04, damping=0.22)

    load_counts = net.load.groupby("bus").size() if hasattr(net, "load") and len(net.load) else pd.Series(dtype=int)
    load_p = net.load.groupby("bus")["p_mw"].sum() if hasattr(net, "load") and len(net.load) and "p_mw" in net.load.columns else pd.Series(dtype=float)
    load_q = net.load.groupby("bus")["q_mvar"].sum() if hasattr(net, "load") and len(net.load) and "q_mvar" in net.load.columns else pd.Series(dtype=float)

    hpc_summary = _extract_hpc_center_summary(net)
    hpc_bus_set = set()
    if len(hpc_summary):
        hpc_bus_set = set(int(b) for b in hpc_summary["hpc_bus"].dropna().astype(int).tolist())

    ext_bus_set = set()
    if hasattr(net, "ext_grid") and len(net.ext_grid):
        ext_bus_set = set(int(b) for b in net.ext_grid["bus"].tolist())

    def voltage_color(vm):
        if pd.isna(vm):
            return "#94a3b8"
        if vm < 0.95 or vm > 1.05:
            return "#dc2626"
        if vm < 0.97 or vm > 1.03:
            return "#f59e0b"
        return "#16a34a"

    for bus in H.nodes():
        bus = int(bus)
        row = net.bus.loc[bus]
        vm = float(bus_vm.get(bus, float("nan")))
        vn = float(row.get("vn_kv", float("nan")))
        name = str(row.get("name", ""))
        p_load = float(load_p.get(bus, 0.0))
        q_load = float(load_q.get(bus, 0.0))
        n_loads = int(load_counts.get(bus, 0))
        is_ext = bus in ext_bus_set
        is_hpc_bus = bus in hpc_bus_set
        color = "#2563eb" if is_ext else ("#f97316" if is_hpc_bus else voltage_color(vm))
        shape = "star" if is_ext else ("square" if is_hpc_bus else "dot")
        size = 28 if is_ext else (22 if is_hpc_bus else 10)
        label = f"Grid {bus}" if is_ext else (f"HPC bus {bus}" if is_hpc_bus else str(bus))
        title = (
            f"<b>Bus {bus}</b><br>"
            f"Name: {name}<br>Voltage level: {vn:.3g} kV<br>"
            f"Voltage result: {vm:.4f} pu<br>Attached load elements: {n_loads}<br>"
            f"Attached load: {p_load:.4f} MW / {q_load:.4f} MVAr"
        )
        net_vis.add_node(f"bus_{bus}", label=label, title=title, color=color, shape=shape, size=size)

    line_loading = pd.Series(dtype=float)
    if hasattr(net, "res_line") and "loading_percent" in net.res_line.columns:
        line_loading = pd.to_numeric(net.res_line["loading_percent"], errors="coerce")
    if hasattr(net, "line") and len(net.line):
        for idx, row in net.line.iterrows():
            fb, tb = int(row["from_bus"]), int(row["to_bus"])
            if fb not in H.nodes or tb not in H.nodes or not bool(row.get("in_service", True)):
                continue
            loading = float(line_loading.get(idx, float("nan")))
            name = str(row.get("name", ""))
            if "HPC" in name.upper() or "SERVICE" in name.upper():
                color, width, dashes = "#f97316", 4, True
            elif not pd.isna(loading) and loading >= 100:
                color, width, dashes = "#dc2626", 5, False
            elif not pd.isna(loading) and loading >= 70:
                color, width, dashes = "#f59e0b", 4, False
            else:
                color, width, dashes = "#64748b", 2, False
            p_from = i_ka = pl_mw = None
            if hasattr(net, "res_line") and idx in net.res_line.index:
                p_from = net.res_line.at[idx, "p_from_mw"] if "p_from_mw" in net.res_line.columns else None
                i_ka = net.res_line.at[idx, "i_ka"] if "i_ka" in net.res_line.columns else None
                pl_mw = net.res_line.at[idx, "pl_mw"] if "pl_mw" in net.res_line.columns else None
            title = (
                f"<b>Line/Cable {idx}</b><br>Name: {name}<br>"
                f"{fb} → {tb}<br>Loading: {loading:.2f}%<br>"
                f"p_from: {p_from if p_from is not None else 'N/A'} MW<br>"
                f"Current: {i_ka if i_ka is not None else 'N/A'} kA<br>"
                f"Loss: {pl_mw if pl_mw is not None else 'N/A'} MW"
            )
            net_vis.add_edge(f"bus_{fb}", f"bus_{tb}", title=title, color=color, width=width, dashes=dashes)

    trafo_loading = pd.Series(dtype=float)
    if hasattr(net, "res_trafo") and "loading_percent" in net.res_trafo.columns:
        trafo_loading = pd.to_numeric(net.res_trafo["loading_percent"], errors="coerce")
    if hasattr(net, "trafo") and len(net.trafo):
        for idx, row in net.trafo.iterrows():
            hv, lv = int(row["hv_bus"]), int(row["lv_bus"])
            if hv not in H.nodes or lv not in H.nodes or not bool(row.get("in_service", True)):
                continue
            loading = float(trafo_loading.get(idx, float("nan")))
            title = (
                f"<b>Transformer {idx}</b><br>{hv} → {lv}<br>"
                f"Loading: {loading:.2f}%<br>Rated power: {row.get('sn_mva', 'N/A')} MVA<br>"
                f"HV/LV: {row.get('vn_hv_kv', 'N/A')} / {row.get('vn_lv_kv', 'N/A')} kV"
            )
            net_vis.add_edge(f"bus_{hv}", f"bus_{lv}", title=title, color="#7c3aed", width=4, dashes=True)

    if len(hpc_summary):
        for r in hpc_summary.itertuples(index=False):
            center_id = int(getattr(r, "center_id"))
            raw_hpc_bus = getattr(r, "hpc_bus")
            if pd.isna(raw_hpc_bus):
                continue
            hpc_bus = int(raw_hpc_bus)
            if hpc_bus not in H.nodes:
                continue
            p_mw = float(getattr(r, "p_mw", 0.0) or 0.0)
            q_mvar = float(getattr(r, "q_mvar", 0.0) or 0.0)
            racks = int(getattr(r, "rack_load_elements", 0) or 0)
            node_id = f"hpc_{center_id}"
            label = f"HPC Center {center_id}\n{p_mw:.2f} MW"
            title = (
                f"<b>HPC Center {center_id}</b><br>"
                f"Modeled load: {p_mw:.4f} MW / {q_mvar:.4f} MVAr<br>"
                f"Rack/load elements: {racks}<br>Actual pandapower connection bus: {hpc_bus}"
            )
            net_vis.add_node(node_id, label=label, title=title, color="#fb923c", shape="box", size=32, mass=3)
            net_vis.add_edge(f"bus_{hpc_bus}", node_id, title="HPC center load attached to this bus", color="#ea580c", width=5, dashes=True)

    net_vis.set_options('''
    var options = {
      "nodes": {"borderWidth": 1, "font": {"size": 14}},
      "edges": {"smooth": {"type": "dynamic"}, "font": {"size": 10}},
      "physics": {"enabled": true, "stabilization": {"enabled": true, "iterations": 300}},
      "interaction": {"hover": true, "tooltipDelay": 120, "navigationButtons": true, "keyboard": true}
    }
    ''')
    html = net_vis.generate_html(notebook=False)
    legend = f"""
    <div style='font-family:Arial;margin-bottom:8px;padding:10px;border:1px solid #e5e7eb;border-radius:12px;background:#f8fafc;'>
      <b>Interactive pandapower topology ({subtitle})</b><br>
      Drag nodes, zoom with the mouse wheel, hover elements for pandapower results. 
      <span style='color:#2563eb'>★ External grid</span> · 
      <span style='color:#16a34a'>● normal voltage bus</span> · 
      <span style='color:#f97316'>■ HPC connection/facility</span> · 
      <span style='color:#7c3aed'>purple dashed = transformer</span> · 
      <span style='color:#ea580c'>orange dashed = HPC attachment/service line</span>
    </div>
    """
    return legend + html
def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")



def style_plotly_figure(fig: go.Figure, title: str | None = None, height: int = 440) -> go.Figure:
    """Apply a consistent dashboard look to Plotly figures."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        title=dict(text=title or fig.layout.title.text, x=0.02, xanchor="left"),
        font=dict(size=13),
        margin=dict(l=55, r=35, t=70, b=55),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    return fig


def add_threshold_lines(fig: go.Figure, y_values: list[tuple[float, str]]) -> go.Figure:
    for y, label in y_values:
        fig.add_hline(
            y=y,
            line_dash="dash",
            line_width=1.2,
            line_color="#64748b",
            annotation_text=label,
            annotation_position="top left",
        )
    return fig


def get_status_label(value: float, warning: float, danger: float, lower_is_better: bool = False) -> tuple[str, str]:
    if pd.isna(value):
        return "Unknown", "#64748b"
    if lower_is_better:
        if value >= danger:
            return "Critical", "#dc2626"
        if value >= warning:
            return "Warning", "#f59e0b"
        return "OK", "#16a34a"
    if value <= danger and value >= warning:
        return "OK", "#16a34a"
    return "Warning", "#f59e0b"


def voltage_status(vm: float) -> tuple[str, str]:
    if pd.isna(vm):
        return "Unknown", "#64748b"
    if vm < 0.95 or vm > 1.05:
        return "Violation", "#dc2626"
    if vm < 0.97 or vm > 1.03:
        return "Near limit", "#f59e0b"
    return "OK", "#16a34a"


def loading_status(loading_percent: float) -> tuple[str, str]:
    if pd.isna(loading_percent):
        return "Unknown", "#64748b"
    if loading_percent >= 100:
        return "Overloaded", "#dc2626"
    if loading_percent >= 70:
        return "High", "#f59e0b"
    return "OK", "#16a34a"


def build_grid_health_cards(summary: dict) -> pd.DataFrame:
    min_v_status, _ = voltage_status(summary.get("min_voltage_pu", float("nan")))
    max_v_status, _ = voltage_status(summary.get("max_voltage_pu", float("nan")))
    line_status, _ = loading_status(summary.get("max_line_loading_percent", float("nan")))
    trafo_status, _ = loading_status(summary.get("max_trafo_loading_percent", float("nan")))
    return pd.DataFrame([
        {
            "Area": "Voltage quality",
            "Status": min_v_status if min_v_status != "OK" else max_v_status,
            "Key value": f"{summary.get('min_voltage_pu', float('nan')):.4f}–{summary.get('max_voltage_pu', float('nan')):.4f} pu",
            "How to read it": "German/European distribution-grid studies often use 0.95–1.05 pu as an operational voltage band.",
            "Pandapower source": "net.res_bus.vm_pu",
        },
        {
            "Area": "Line/cable loading",
            "Status": line_status,
            "Key value": f"{summary.get('max_line_loading_percent', float('nan')):.2f}%",
            "How to read it": "Values above 100% indicate thermal overload in the selected model.",
            "Pandapower source": "net.res_line.loading_percent",
        },
        {
            "Area": "Transformer loading",
            "Status": trafo_status,
            "Key value": f"{summary.get('max_trafo_loading_percent', float('nan')):.2f}%",
            "How to read it": "Values above 100% indicate transformer overload in the selected model.",
            "Pandapower source": "net.res_trafo.loading_percent",
        },
        {
            "Area": "Losses",
            "Status": "Calculated",
            "Key value": format_power(summary.get("total_losses_mw", 0.0)),
            "How to read it": "Active losses are the difference between supplied grid power and useful load demand.",
            "Pandapower source": "sum(net.res_line.pl_mw) + sum(net.res_trafo.pl_mw)",
        },
    ])


def build_worst_elements_table(grid_result_tables: dict[str, pd.DataFrame], n: int = 5) -> pd.DataFrame:
    rows = []
    bus_df = grid_result_tables.get("bus", pd.DataFrame()).copy()
    if len(bus_df) and "res_vm_pu" in bus_df.columns:
        for _, row in bus_df.sort_values("res_vm_pu", ascending=True).head(n).iterrows():
            rows.append({
                "Type": "Bus voltage",
                "Element": row.get("name", row.get("element_index", "N/A")),
                "Value": f"{row.get('res_vm_pu', float('nan')):.4f} pu",
                "Limit / meaning": "Lower values are more critical; 0.95 pu is common lower bound.",
                "Source": "net.res_bus.vm_pu",
            })
    line_df = grid_result_tables.get("line", pd.DataFrame()).copy()
    if len(line_df) and "res_loading_percent" in line_df.columns:
        for _, row in line_df.sort_values("res_loading_percent", ascending=False).head(n).iterrows():
            rows.append({
                "Type": "Line loading",
                "Element": row.get("name", row.get("element_index", "N/A")),
                "Value": f"{row.get('res_loading_percent', float('nan')):.2f}%",
                "Limit / meaning": "100% means line thermal rating reached.",
                "Source": "net.res_line.loading_percent",
            })
    trafo_df = grid_result_tables.get("trafo", pd.DataFrame()).copy()
    if len(trafo_df) and "res_loading_percent" in trafo_df.columns:
        for _, row in trafo_df.sort_values("res_loading_percent", ascending=False).head(n).iterrows():
            rows.append({
                "Type": "Transformer loading",
                "Element": row.get("name", row.get("element_index", "N/A")),
                "Value": f"{row.get('res_loading_percent', float('nan')):.2f}%",
                "Limit / meaning": "100% means transformer rating reached.",
                "Source": "net.res_trafo.loading_percent",
            })
    return pd.DataFrame(rows)


def create_voltage_distribution_figure(bus_df: pd.DataFrame) -> go.Figure:
    """Readable voltage profile instead of a histogram that collapses at 1.0 pu."""
    fig = go.Figure()
    if len(bus_df) and "res_vm_pu" in bus_df.columns:
        plot_df = bus_df.copy()
        plot_df = plot_df.dropna(subset=["res_vm_pu"]).sort_values("res_vm_pu").reset_index(drop=True)
        plot_df["bus_rank"] = range(1, len(plot_df) + 1)
        plot_df["bus_name"] = plot_df.get("name", plot_df.get("element_index", plot_df["bus_rank"])).astype(str)

        fig.add_hrect(y0=0.95, y1=1.05, fillcolor="#dcfce7", opacity=0.35, line_width=0)
        fig.add_hrect(y0=0.97, y1=1.03, fillcolor="#bbf7d0", opacity=0.30, line_width=0)
        fig.add_trace(go.Scatter(
            x=plot_df["bus_rank"],
            y=plot_df["res_vm_pu"],
            mode="markers+lines",
            marker=dict(
                size=7,
                color=plot_df["res_vm_pu"],
                colorscale=[[0, "#dc2626"], [0.45, "#f59e0b"], [0.5, "#16a34a"], [0.55, "#f59e0b"], [1, "#dc2626"]],
                cmin=0.94,
                cmax=1.06,
                colorbar=dict(title="vm_pu"),
                line=dict(width=0.6, color="white"),
            ),
            customdata=plot_df[[c for c in ["element_index", "bus_name", "vn_kv"] if c in plot_df.columns]],
            hovertemplate="Bus rank: %{x}<br>Voltage: %{y:.5f} pu<extra></extra>",
            name="Bus voltage",
        ))
        fig.add_hline(y=0.95, line_dash="dash", line_color="#dc2626", annotation_text="lower limit 0.95 pu")
        fig.add_hline(y=1.05, line_dash="dash", line_color="#dc2626", annotation_text="upper limit 1.05 pu")
        fig.add_hline(y=1.00, line_dash="dot", line_color="#16a34a", annotation_text="nominal 1.00 pu")
    fig.update_xaxes(title="Buses sorted from lowest to highest voltage")
    fig.update_yaxes(title="Voltage magnitude vm_pu", range=[0.94, 1.06])
    return style_plotly_figure(fig, "Bus voltage profile", 430)


def create_voltage_box_figure(bus_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(bus_df) and "res_vm_pu" in bus_df.columns:
        fig.add_hrect(y0=0.95, y1=1.05, fillcolor="#dcfce7", opacity=0.35, line_width=0)
        fig.add_trace(go.Box(
            y=bus_df["res_vm_pu"],
            boxpoints="all",
            jitter=0.35,
            pointpos=0,
            marker=dict(size=5, color="#2563eb", opacity=0.55),
            line=dict(color="#0f172a"),
            name="Buses",
            hovertemplate="Voltage: %{y:.5f} pu<extra></extra>",
        ))
        fig.add_hline(y=0.95, line_dash="dash", line_color="#dc2626")
        fig.add_hline(y=1.05, line_dash="dash", line_color="#dc2626")
        fig.add_hline(y=1.00, line_dash="dot", line_color="#16a34a")
    fig.update_xaxes(title="All buses")
    fig.update_yaxes(title="Voltage magnitude vm_pu", range=[0.94, 1.06])
    return style_plotly_figure(fig, "Voltage spread and outliers", 430)


def create_losses_bar_figure(summary: dict) -> go.Figure:
    line = max(float(summary.get("line_losses_mw", 0.0) or 0.0), 0.0)
    trafo = max(float(summary.get("transformer_losses_mw", 0.0) or 0.0), 0.0)
    df = pd.DataFrame({
        "Loss type": ["Line losses", "Transformer losses"],
        "MW": [line, trafo],
    })
    total = df["MW"].sum()
    df["Share"] = 0 if total == 0 else df["MW"] / total * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["MW"],
        y=df["Loss type"],
        orientation="h",
        marker=dict(color=["#2563eb", "#f59e0b"]),
        text=[f"{mw:.5f} MW ({share:.1f}%)" for mw, share in zip(df["MW"], df["Share"])],
        textposition="outside",
        hovertemplate="%{y}<br>%{x:.6f} MW<extra></extra>",
    ))
    fig.update_xaxes(title="Active loss (MW)")
    fig.update_yaxes(title="", autorange="reversed")
    return style_plotly_figure(fig, "Active-loss breakdown", 390)

def create_top_loading_figure(df: pd.DataFrame, y_col: str, title: str, element_label: str, top_n: int = 15) -> go.Figure:
    fig = go.Figure()
    if len(df) and y_col in df.columns:
        plot_df = df.copy().sort_values(y_col, ascending=False).head(top_n)
        plot_df["display_name"] = plot_df.get("name", plot_df.get("element_index", "Element")).astype(str).str.slice(0, 45)
        colors = ["#dc2626" if v >= 100 else "#f59e0b" if v >= 70 else "#2563eb" for v in plot_df[y_col].fillna(0)]
        fig.add_trace(go.Bar(
            x=plot_df[y_col],
            y=plot_df["display_name"],
            orientation="h",
            marker=dict(color=colors),
            customdata=plot_df[[c for c in ["element_index", "name"] if c in plot_df.columns]],
            hovertemplate=f"{element_label}: %{{y}}<br>Loading: %{{x:.2f}}%<extra></extra>",
        ))
        fig.add_vline(x=70, line_dash="dot", line_color="#f59e0b", annotation_text="70% high")
        fig.add_vline(x=100, line_dash="dash", line_color="#dc2626", annotation_text="100% limit")
        fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Loading (%)")
    fig.update_yaxes(title=element_label)
    return style_plotly_figure(fig, title, 470)


def create_loss_breakdown_figure(summary: dict) -> go.Figure:
    """Loss breakdown without misleading 100% donut graphics.

    A donut chart can make a tiny absolute loss source look dominant. This
    horizontal bar view shows absolute MW first and annotates the percentage
    share only as secondary information.
    """
    line_loss = max(float(summary.get("line_losses_mw", 0.0) or 0.0), 0.0)
    trafo_loss = max(float(summary.get("transformer_losses_mw", 0.0) or 0.0), 0.0)
    total = line_loss + trafo_loss
    rows = pd.DataFrame([
        {"Loss type": "Line/cable losses", "Loss MW": line_loss},
        {"Loss type": "Transformer losses", "Loss MW": trafo_loss},
    ])
    rows["Share %"] = rows["Loss MW"].apply(lambda v: (v / total * 100.0) if total > 0 else 0.0)
    rows["Label"] = rows.apply(lambda r: f"{r['Loss MW']:.5f} MW ({r['Share %']:.1f}%)", axis=1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=rows["Loss MW"],
        y=rows["Loss type"],
        orientation="h",
        text=rows["Label"],
        textposition="outside",
        marker=dict(color=["#2563eb", "#f59e0b"]),
        customdata=rows[["Share %"]].to_numpy(),
        hovertemplate="%{y}<br>Loss: %{x:.6f} MW<br>Share of active losses: %{customdata[0]:.2f}%<extra></extra>",
    ))
    fig.update_xaxes(title="Active losses (MW)")
    fig.update_yaxes(title="", autorange="reversed")
    if total <= 0:
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="No active losses reported for this snapshot", showarrow=False)
    else:
        fig.add_annotation(
            x=1.0,
            y=1.15,
            xref="paper",
            yref="paper",
            text=f"Total active losses: {total:.5f} MW",
            showarrow=False,
            align="right",
            font=dict(size=12),
        )
    return style_plotly_figure(fig, "Active-loss breakdown", 390)

def create_power_balance_figure(summary: dict) -> go.Figure:
    values = [
        float(summary.get("applied_load_p_mw", 0.0)),
        float(summary.get("total_losses_mw", 0.0)),
        float(summary.get("external_grid_p_mw", 0.0)),
    ]
    labels = ["Useful HPC load", "Grid losses", "External grid supply"]
    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker=dict(color=["#16a34a", "#f59e0b", "#2563eb"]),
        hovertemplate="%{x}<br>%{y:.4f} MW<extra></extra>",
    ))
    fig.update_yaxes(title="Active power (MW)")
    return style_plotly_figure(fig, "Snapshot active-power balance", 390)


def create_grid_timeseries_figure(results_df: pd.DataFrame, title: str) -> go.Figure:
    df = results_df.copy()
    x_col = "elapsed_hours" if "elapsed_hours" in df.columns else "timestep"
    fig = go.Figure()
    if "min_voltage_pu" in df.columns and df["min_voltage_pu"].notna().any():
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["min_voltage_pu"], mode="lines", name="Minimum voltage (pu)",
            line=dict(color="#16a34a", width=2.3),
            hovertemplate="Time: %{x:.3f}<br>Min voltage: %{y:.4f} pu<extra></extra>",
        ))
        fig.add_hline(y=0.95, line_dash="dash", line_color="#dc2626", annotation_text="0.95 pu")
    if "max_transformer_loading_percent" in df.columns:
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["max_transformer_loading_percent"], mode="lines", name="Max transformer loading (%)",
            yaxis="y2", line=dict(color="#f59e0b", width=2.0),
            hovertemplate="Time: %{x:.3f}<br>Transformer loading: %{y:.2f}%<extra></extra>",
        ))
    if "max_line_loading_percent" in df.columns:
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["max_line_loading_percent"], mode="lines", name="Max line loading (%)",
            yaxis="y2", line=dict(color="#dc2626", width=2.0),
            hovertemplate="Time: %{x:.3f}<br>Line loading: %{y:.2f}%<extra></extra>",
        ))
    fig.update_layout(
        yaxis=dict(title="Voltage (pu)", rangemode="normal"),
        yaxis2=dict(title="Loading (%)", overlaying="y", side="right", rangemode="tozero"),
        xaxis=dict(title="Elapsed hours" if x_col == "elapsed_hours" else "Timestep"),
    )
    return style_plotly_figure(fig, title, 500)


def build_grid_violation_summary(results_df: pd.DataFrame) -> pd.DataFrame:
    df = results_df.copy()
    rows = []
    if "min_voltage_pu" in df.columns and df["min_voltage_pu"].notna().any():
        rows.append({
            "Check": "Voltage below 0.95 pu",
            "Violating timesteps": int((df["min_voltage_pu"] < 0.95).sum()),
            "Worst value": f"{df['min_voltage_pu'].min():.4f} pu",
            "Meaning": "Low-voltage quality problem in the AC power-flow result.",
        })
    if "max_line_loading_percent" in df.columns:
        rows.append({
            "Check": "Line loading above 100%",
            "Violating timesteps": int((df["max_line_loading_percent"] > 100).sum()),
            "Worst value": f"{df['max_line_loading_percent'].max():.2f}%",
            "Meaning": "Thermal overload of at least one line/cable.",
        })
    if "max_transformer_loading_percent" in df.columns:
        rows.append({
            "Check": "Transformer loading above 100%",
            "Violating timesteps": int((df["max_transformer_loading_percent"] > 100).sum()),
            "Worst value": f"{df['max_transformer_loading_percent'].max():.2f}%",
            "Meaning": "Transformer apparent-power rating exceeded.",
        })
    if "converged" in df.columns:
        rows.append({
            "Check": "Power-flow convergence failure",
            "Violating timesteps": int((~df["converged"].astype(bool)).sum()),
            "Worst value": "not applicable",
            "Meaning": "pandapower AC solver did not converge for that timestep.",
        })
    return pd.DataFrame(rows)


def build_snapshot_violation_table(summary: dict) -> pd.DataFrame:
    """Snapshot-level security checks from solved pandapower result tables."""
    rows = [
        {
            "Check": "Voltage violations",
            "Count": int(summary.get("voltage_violations", 0)),
            "Worst / max value": f"{summary.get('min_voltage_pu', float('nan')):.4f} pu min / {summary.get('max_voltage_pu', float('nan')):.4f} pu max",
            "Limit used": "0.95 ≤ vm_pu ≤ 1.05",
            "Source": "net.res_bus.vm_pu",
        },
        {
            "Check": "Line overloads",
            "Count": int(summary.get("line_overloads", 0)),
            "Worst / max value": f"{summary.get('max_line_loading_percent', float('nan')):.2f}%",
            "Limit used": "loading_percent ≤ 100%",
            "Source": "net.res_line.loading_percent",
        },
        {
            "Check": "Transformer overloads",
            "Count": int(summary.get("trafo_overloads", 0)),
            "Worst / max value": f"{summary.get('max_trafo_loading_percent', float('nan')):.2f}%",
            "Limit used": "loading_percent ≤ 100%",
            "Source": "net.res_trafo.loading_percent",
        },
        {
            "Check": "Power-flow convergence",
            "Count": 0 if summary.get("converged", False) else 1,
            "Worst / max value": "converged" if summary.get("converged", False) else "failed",
            "Limit used": "pp.runpp must converge",
            "Source": "net.converged",
        },
    ]
    return pd.DataFrame(rows)


def build_worst_timestep_table(results_df: pd.DataFrame) -> pd.DataFrame:
    """Find the time samples where each grid metric is most critical."""
    df = results_df.copy()
    x_col = "elapsed_hours" if "elapsed_hours" in df.columns else "timestep"
    rows = []

    checks = [
        ("Worst low voltage", "min_voltage_pu", "min", "pu", "net.res_bus.vm_pu"),
        ("Worst line loading", "max_line_loading_percent", "max", "%", "net.res_line.loading_percent"),
        ("Worst transformer loading", "max_transformer_loading_percent", "max", "%", "net.res_trafo.loading_percent"),
        ("Peak external grid supply", "external_grid_p_mw", "max", "MW", "net.res_ext_grid.p_mw"),
        ("Maximum losses", "total_losses_mw", "max", "MW", "net.res_line.pl_mw + net.res_trafo.pl_mw"),
        ("Lowest power factor", "power_factor", "min", "", "P / sqrt(P² + Q²) from net.res_ext_grid"),
    ]

    for label, col, mode, unit, source in checks:
        if col not in df.columns or not df[col].notna().any():
            continue
        idx = df[col].idxmin() if mode == "min" else df[col].idxmax()
        row = df.loc[idx]
        val = row[col]
        rows.append({
            "Stress metric": label,
            "Timestep": row.get("timestep", idx),
            "Elapsed hours": f"{row.get(x_col, 0.0):.3f}" if x_col in row else "N/A",
            "Value": f"{val:.4f} {unit}".strip() if pd.notna(val) else "N/A",
            "Total power": format_power(row.get("total_power_mw", float("nan"))),
            "Active centers": int(row.get("active_centers", 0)) if pd.notna(row.get("active_centers", float("nan"))) else "N/A",
            "Source": source,
        })
    return pd.DataFrame(rows)


def create_losses_timeseries_figure(results_df: pd.DataFrame) -> go.Figure:
    df = results_df.copy()
    x_col = "elapsed_hours" if "elapsed_hours" in df.columns else "timestep"
    fig = go.Figure()
    if "line_losses_mw" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["line_losses_mw"], mode="lines", name="Line losses MW", line=dict(width=2.2, color="#2563eb")))
    if "transformer_losses_mw" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["transformer_losses_mw"], mode="lines", name="Transformer losses MW", line=dict(width=2.2, color="#f59e0b")))
    if "total_losses_mw" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["total_losses_mw"], mode="lines", name="Total losses MW", line=dict(width=2.8, color="#0f172a")))
    if "loss_percent_of_supply" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["loss_percent_of_supply"], mode="lines", name="Loss % of supply", yaxis="y2", line=dict(width=2, dash="dot", color="#dc2626")))
    fig.update_layout(
        yaxis=dict(title="Losses (MW)", rangemode="tozero"),
        yaxis2=dict(title="Loss % of external supply", overlaying="y", side="right", rangemode="tozero"),
        xaxis=dict(title="Elapsed hours" if x_col == "elapsed_hours" else "Timestep"),
    )
    return style_plotly_figure(fig, "Losses over time", 480)


def create_reactive_power_figure(results_df: pd.DataFrame) -> go.Figure:
    df = results_df.copy()
    x_col = "elapsed_hours" if "elapsed_hours" in df.columns else "timestep"
    fig = go.Figure()
    if "external_grid_p_mw" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["external_grid_p_mw"], mode="lines", name="External grid P (MW)", line=dict(width=2.2, color="#2563eb")))
    if "external_grid_q_mvar" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["external_grid_q_mvar"], mode="lines", name="External grid Q (MVAr)", line=dict(width=2.2, color="#f59e0b")))
    if "power_factor" in df.columns:
        fig.add_trace(go.Scatter(x=df[x_col], y=df["power_factor"], mode="lines", name="Power factor", yaxis="y2", line=dict(width=2.4, color="#16a34a")))
    fig.update_layout(
        yaxis=dict(title="P / Q at external grid", rangemode="normal"),
        yaxis2=dict(title="Power factor", overlaying="y", side="right", range=[0, 1.05]),
        xaxis=dict(title="Elapsed hours" if x_col == "elapsed_hours" else "Timestep"),
    )
    return style_plotly_figure(fig, "External-grid P/Q and power factor over time", 480)


def create_violation_timeseries_figure(results_df: pd.DataFrame) -> go.Figure:
    df = results_df.copy()
    x_col = "elapsed_hours" if "elapsed_hours" in df.columns else "timestep"
    fig = go.Figure()
    cols = [
        ("voltage_violation_count", "Voltage violations", "#dc2626"),
        ("line_overload_count", "Line overloads", "#f59e0b"),
        ("transformer_overload_count", "Transformer overloads", "#7c3aed"),
    ]
    for col, name, color in cols:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df[x_col], y=df[col], mode="lines", name=name, line=dict(width=2.2, color=color), stackgroup=None))
    fig.update_xaxes(title="Elapsed hours" if x_col == "elapsed_hours" else "Timestep")
    fig.update_yaxes(title="Number of violating elements", rangemode="tozero")
    return style_plotly_figure(fig, "Constraint violations over time", 430)


def create_loading_distribution_figure(line_df: pd.DataFrame, trafo_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(line_df) and "res_loading_percent" in line_df.columns:
        fig.add_trace(go.Box(
            y=pd.to_numeric(line_df["res_loading_percent"], errors="coerce"),
            name="Lines",
            boxpoints="outliers",
            marker=dict(color="#2563eb"),
            hovertemplate="Line loading: %{y:.2f}%<extra></extra>",
        ))
    if len(trafo_df) and "res_loading_percent" in trafo_df.columns:
        fig.add_trace(go.Box(
            y=pd.to_numeric(trafo_df["res_loading_percent"], errors="coerce"),
            name="Transformers",
            boxpoints="outliers",
            marker=dict(color="#f59e0b"),
            hovertemplate="Transformer loading: %{y:.2f}%<extra></extra>",
        ))
    fig.add_hline(y=70, line_dash="dot", line_color="#f59e0b", annotation_text="70% high")
    fig.add_hline(y=100, line_dash="dash", line_color="#dc2626", annotation_text="100% limit")
    fig.update_yaxes(title="Loading (%)", rangemode="tozero")
    return style_plotly_figure(fig, "Loading distribution at peak snapshot", 430)


def build_line_flow_direction_table(line_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if line_df is None or len(line_df) == 0:
        return pd.DataFrame()
    df = line_df.copy()
    needed = ["res_p_from_mw", "res_p_to_mw"]
    if not all(c in df.columns for c in needed):
        return pd.DataFrame()
    df["abs_flow_mw"] = pd.to_numeric(df["res_p_from_mw"], errors="coerce").abs()
    df = df.sort_values("abs_flow_mw", ascending=False).head(n)
    rows = []
    for _, row in df.iterrows():
        p_from = row.get("res_p_from_mw", float("nan"))
        if pd.isna(p_from):
            direction = "unknown"
        elif p_from >= 0:
            direction = f"{row.get('from_bus', '?')} → {row.get('to_bus', '?')}"
        else:
            direction = f"{row.get('to_bus', '?')} → {row.get('from_bus', '?')}"
        rows.append({
            "Line": row.get("name", row.get("element_index", "N/A")),
            "Direction": direction,
            "P from MW": f"{row.get('res_p_from_mw', float('nan')):.4f}",
            "P to MW": f"{row.get('res_p_to_mw', float('nan')):.4f}",
            "Loading": f"{row.get('res_loading_percent', float('nan')):.2f}%",
            "Loss MW": f"{row.get('res_pl_mw', float('nan')):.5f}" if "res_pl_mw" in row else "N/A",
            "Source": "net.res_line.p_from_mw / p_to_mw",
        })
    return pd.DataFrame(rows)


def run_n_minus_one_contingency(snapshot: dict, top_n: int = 3) -> pd.DataFrame:
    """Simple N-1 check: remove the most loaded lines/transformers from the peak snapshot one at a time."""
    net = snapshot.get("net")
    if net is None or not snapshot.get("converged", False):
        return pd.DataFrame()

    candidates = []
    if hasattr(net, "res_line") and len(net.res_line) and "loading_percent" in net.res_line.columns:
        for idx, val in pd.to_numeric(net.res_line["loading_percent"], errors="coerce").sort_values(ascending=False).head(top_n).items():
            candidates.append(("line", idx, val, net.line.at[idx, "name"] if idx in net.line.index and "name" in net.line.columns else f"line {idx}"))
    if hasattr(net, "res_trafo") and len(net.res_trafo) and "loading_percent" in net.res_trafo.columns:
        for idx, val in pd.to_numeric(net.res_trafo["loading_percent"], errors="coerce").sort_values(ascending=False).head(top_n).items():
            candidates.append(("trafo", idx, val, net.trafo.at[idx, "name"] if idx in net.trafo.index and "name" in net.trafo.columns else f"trafo {idx}"))

    rows = []
    for element_type, idx, base_loading, name in candidates:
        test_net = copy.deepcopy(net)
        try:
            if element_type == "line":
                test_net.line.at[idx, "in_service"] = False
            else:
                test_net.trafo.at[idx, "in_service"] = False
            pp.runpp(test_net, algorithm="nr", max_iteration=30)
            converged = bool(test_net.converged)
            min_v = float(test_net.res_bus["vm_pu"].min()) if len(test_net.res_bus) else float("nan")
            max_l = float(test_net.res_line["loading_percent"].max()) if len(test_net.res_line) else 0.0
            max_t = float(test_net.res_trafo["loading_percent"].max()) if len(test_net.res_trafo) else 0.0
            v_viol = int(((test_net.res_bus["vm_pu"] < 0.95) | (test_net.res_bus["vm_pu"] > 1.05)).sum()) if len(test_net.res_bus) else 0
            l_viol = int((test_net.res_line["loading_percent"] > 100).sum()) if len(test_net.res_line) else 0
            t_viol = int((test_net.res_trafo["loading_percent"] > 100).sum()) if len(test_net.res_trafo) else 0
            status = "OK" if converged and v_viol == 0 and l_viol == 0 and t_viol == 0 else "Constraint issue"
        except Exception as exc:
            converged = False
            min_v = float("nan")
            max_l = float("nan")
            max_t = float("nan")
            v_viol = l_viol = t_viol = "N/A"
            status = f"Failed: {str(exc)[:120]}"

        rows.append({
            "Outaged element": f"{element_type} {idx}",
            "Name": name,
            "Base loading": f"{base_loading:.2f}%",
            "Converged": "Yes" if converged else "No",
            "Min voltage": f"{min_v:.4f} pu" if pd.notna(min_v) else "N/A",
            "Max line loading": f"{max_l:.2f}%" if pd.notna(max_l) else "N/A",
            "Max trafo loading": f"{max_t:.2f}%" if pd.notna(max_t) else "N/A",
            "Voltage violations": v_viol,
            "Line overloads": l_viol,
            "Trafo overloads": t_viol,
            "Status": status,
        })
    return pd.DataFrame(rows)
st.title("⚡ HPC Training Energy Simulation with Pandapower")

st.markdown(
    """
    Interactive simulation platform for estimating the grid impact of HPC training workloads.
    Real GPU power traces are scaled to HPC-center loads and evaluated with pandapower AC time-series power flow.

    **Lastmodellierung:** measured MLPerf GPU power and utilization traces are converted into node, facility, and HPC-center electrical load profiles before they are injected into the pandapower grid model.
    """
)

show_explanations = st.sidebar.toggle(
    "Show explanations / hints",
    value=True,
    help="Turn this on to see short engineering explanations for dashboard options.",
)

capacity_only_mode = st.sidebar.toggle(
    "Hosting Capacity mode",
    value=False,
    help=(
        "Use this when you only want to test the grid allowance: how many HPC centers can be added "
        "before voltage, line loading, transformer loading, or power-flow convergence fails. "
        "Energy/cost optimization and workload scheduling controls are not used in this mode."
    ),
)

if capacity_only_mode:
    st.sidebar.info(
        "Hosting Capacity mode is active. The app will sweep 1..N HPC centers using the selected workload, "
        "nodes per center, PUE, grid backend, and peak-load sample. Scenario optimization, delayed training, "
        "and center scheduling are intentionally ignored."
    )


with st.sidebar.expander("1. Workload Data", expanded=True):
    workload_mode = st.selectbox(
        "Workload Type",
        ["Training Run", "Inference Run", "Simultaneous Training + Inference"],
        index=0,
        help=(
            "Training uses the averaged MLPerf training trace. Inference uses the averaged inference trace. "
            "Simultaneous adds a repeated inference pattern on top of the training trace to model concurrent service traffic."
        ),
    )
    training_path = st.text_input(
        "Training CSV Folder",
        value="data/raw_runs/training",
        help="Folder containing MLPerf training CSV files. Can be a relative path from project root or an absolute Windows path.",
    )
    inference_path = st.text_input(
        "Inference CSV Folder",
        value="data/raw_runs/inference",
        help="Folder containing MLPerf inference CSV files. Used when Workload Type is Inference or Simultaneous.",
    )
    if show_explanations:
        st.caption(
            "Input CSVs should contain timestamp, total_gpu_power_w and preferably gpu_util_percent. "
            "The app averages all runs and calculates real sample durations from timestamps. "
            "For simultaneous mode, the inference pattern is repeated to match the training timeline."
        )

with st.sidebar.expander("2. HPC Facility Assumptions", expanded=True):
    number_of_centers = st.slider(
        "Number of HPC Centers / Systems",
        min_value=1,
        max_value=50,
        value=20,
        help="Scenario parameter. Max 50 avoids claiming an exact real German HPC count.",
    )

    nodes_per_center = st.slider(
        "Nodes per HPC Center",
        min_value=1,
        max_value=1000,
        value=500,
        step=1,
        help="Number of compute nodes per HPC center.",
    )

    clusters_per_center = st.slider(
        "Clusters per HPC Center",
        min_value=1,
        max_value=20,
        value=4,
        help="Electrical grouping inside one HPC center.",
    )

    racks_per_cluster = st.slider(
        "Racks per Cluster",
        min_value=1,
        max_value=50,
        value=10,
        help="Rack-level load elements per cluster.",
    )

    pue = st.slider(
        "Power Usage Effectiveness (PUE)",
        min_value=1.0,
        max_value=2.0,
        value=1.3,
        step=0.05,
        help="PUE = total facility power / IT power.",
    )

    cpu_power_per_node = st.slider(
        "CPU Power per Node (W)",
        min_value=0,
        max_value=400,
        value=150,
        step=10,
        help="Estimated CPU power added to measured GPU power.",
    )
    if show_explanations:
        st.caption("Facility model: node power = GPU trace + CPU + RAM/storage/network assumptions. Center power = node power × nodes × PUE.")

with st.sidebar.expander("3. Workload / Facility Scenario", expanded=False):
    scenario = st.selectbox(
        "Scenario",
        [
            "Baseline",
            "GPU Power Limit",
            "Improved Cooling",
            "Combined Optimization",
        ],
        help="Selects the energy/facility intervention compared with the baseline trace. Disabled in Hosting Capacity mode because capacity uses the baseline peak load only."
        , disabled=capacity_only_mode,
    )

    gpu_power_factor = 1.0
    pue_factor = 1.0
    delay_steps = 0
    gpu_slowdown_sensitivity = 0.7
    account_for_runtime_slowdown = True
    gpu_runtime_model = "utilization_based"

    if scenario == "GPU Power Limit":
        gpu_power_factor = st.slider(
            "GPU Power Factor",
            0.5,
            1.0,
            0.9,
            0.05,
            help="Instantaneous GPU-related power multiplier. 0.90 means 10% lower GPU power demand.",
        )
        account_for_runtime_slowdown = st.checkbox(
            "Account for runtime slowdown",
            value=True,
            help="If enabled, a GPU power cap also reduces training speed and increases delta_seconds before energy is integrated.",
        )
        gpu_runtime_model = st.radio(
            "GPU Runtime Model",
            ["utilization_based", "constant"],
            index=0,
            help=(
                "utilization_based uses the measured CSV column gpu_util_percent: "
                "p(t)=1-alpha*u(t)*(1-f). constant uses the older single slowdown factor."
            ),
        )
        gpu_slowdown_sensitivity = st.slider(
            "Runtime Slowdown Sensitivity (alpha)",
            0.0,
            1.5,
            0.7,
            0.05,
            help="Alpha in p(t)=1-alpha*u(t)*(1-f). Higher alpha means power capping hurts performance more.",
        )
        st.success(
            f"Power factor: {gpu_power_factor:.3f}; runtime model: {gpu_runtime_model}; alpha: {gpu_slowdown_sensitivity:.2f}"
        )
        if show_explanations:
            st.caption(
                "GPU limit now uses measured GPU utilization from the CSV. "
                "Runtime is changed per timestep: delta_seconds_new = delta_seconds / performance(t). "
                "Energy is then integrated with Σ Power(t) × Δt."
            )

    elif scenario == "Improved Cooling":
        pue_factor = st.slider(
            "Cooling Overhead Factor",
            0.6,
            1.0,
            0.85,
            0.05,
            help=("Multiplier applied only to non-IT facility overhead: overhead = total facility power - IT power. It does not multiply the whole facility load."),
        )
        effective_facility_factor = (1.0 + (pue - 1.0) * pue_factor) / pue
        st.success(
            f"Cooling overhead factor: {pue_factor:.3f}; effective facility multiplier: {effective_facility_factor:.3f} ({effective_facility_factor * 100:.1f}% of original facility power)"
        )
        if show_explanations:
            st.caption(
                "Improved Cooling reduces only the cooling/infrastructure overhead part of PUE. "
                "IT workload power and runtime stay unchanged. Formula: new_PUE = 1 + (PUE - 1) × cooling_factor."
            )
    elif scenario == "Combined Optimization":
        gpu_power_factor = st.slider(
            "GPU Power Factor",
            0.5,
            1.0,
            0.9,
            0.05,
            help="Instantaneous GPU-related power multiplier.",
        )
        account_for_runtime_slowdown = st.checkbox(
            "Account for runtime slowdown",
            value=True,
            help="If enabled, GPU power limiting increases runtime before energy is integrated.",
        )
        gpu_runtime_model = st.radio(
            "GPU Runtime Model",
            ["utilization_based", "constant"],
            index=0,
            help="utilization_based uses measured gpu_util_percent from the CSV; constant uses one fixed slowdown factor.",
        )
        gpu_slowdown_sensitivity = st.slider(
            "Runtime Slowdown Sensitivity (alpha)",
            0.0,
            1.5,
            0.7,
            0.05,
            help="Alpha in p(t)=1-alpha*u(t)*(1-f). Higher means stronger training slowdown from GPU power capping.",
        )
        pue_factor = st.slider(
            "Cooling Overhead Factor",
            0.6,
            1.0,
            0.85,
            0.05,
            help="Multiplier applied only to non-IT facility overhead, not to the whole facility load.",
        )
        st.success(
            f"Power factor × PUE factor: {gpu_power_factor * pue_factor:.3f}; runtime model: {gpu_runtime_model}; alpha: {gpu_slowdown_sensitivity:.2f}"
        )
        if show_explanations:
            st.caption(
                "Combined Optimization applies GPU power capping, cooling/PUE improvement, and optional delay. "
                "The GPU runtime effect is utilization-based when selected, using gpu_util_percent from the CSV."
            )

    else:
        if show_explanations:
            st.caption("Baseline uses the measured profile without optimization. This is the reference case.")

with st.sidebar.expander("4. Workload Scheduling Across Centers", expanded=False):
    enable_load_balancing = st.checkbox(
        "Enable Workload Scheduling",
        value=False,
        disabled=capacity_only_mode,
        help="Controls how many HPC centers are active simultaneously.",
    )

    if number_of_centers == 1:
        max_active_centers = 1
        st.info("Only one HPC center is selected, so scheduling is fixed to 1 active center.")
    else:
        max_active_centers = st.slider(
            "Maximum Simultaneously Active Centers",
            min_value=1,
            max_value=number_of_centers,
            value=max(1, number_of_centers // 2),
        )

    load_balancing_strategy = st.selectbox(
        "Scheduling Strategy",
        [
            "same_centers_active",
            "rotating_centers",
            "variable_activity",
        ],
        help=(
            "same_centers_active = same centers stay active. "
            "rotating_centers = active centers rotate over time. "
            "variable_activity = active center count rises and falls."
        ),
    )
    if show_explanations:
        st.caption("Scheduling changes how many centers run simultaneously. It can lower peak grid demand, but the same work may require longer runtime.")

with st.sidebar.expander("5. Pandapower Simulation", expanded=False):
    simulation_mode = st.radio(
        "Simulation Mode",
        ["Normal AC", "Fast DC"],
        index=0,
        help="Normal AC uses pp.runpp and gives voltage results. Fast DC uses pp.rundcpp and is faster but does not provide voltage magnitudes.",
    )
    fast_mode = simulation_mode == "Fast DC"

    grid_backend = st.selectbox(
        "Grid backend",
        ["Synthetic HPC grid", "SimBench German benchmark grid"],
        index=0,
        help="Synthetic keeps the original custom HPC grid. SimBench uses a public German benchmark grid and injects the HPC centers as additional controllable loads.",
    )

    simbench_code = "1-MV-rural--0-sw"
    include_existing_simbench_loads = True
    if grid_backend == "SimBench German benchmark grid":
        simbench_code = st.selectbox(
            "SimBench code",
            ["1-MV-rural--0-sw", "1-MV-urban--0-sw", "1-LV-rural1--0-sw", "1-LV-semiurb4--0-sw"],
            index=0,
            help="SimBench code loaded with simbench.get_simbench_net(). MV grids are usually more suitable for large HPC load stress tests than LV grids.",
        )
        include_existing_simbench_loads = st.checkbox(
            "Keep original SimBench loads/generation",
            value=True,
            help="If enabled, the benchmark grid contains its original loads/generation plus the added HPC loads. Disable to isolate only the HPC impact on the SimBench topology.",
        )
        if show_explanations:
            st.caption("SimBench is a public German benchmark-grid dataset integrated with pandapower. Here it gives realistic line, transformer, voltage-level and topology data; the HPC workload is added as extra industrial load.")

    st.info(
        """
        Normal AC mode uses pp.runpp(net).
        Fast DC mode uses pp.rundcpp(net).

        Energy calculation uses the timestamp intervals from the CSV.
        """
    )

with st.sidebar.expander("6. Capacity Analysis", expanded=False):
    enable_capacity_analysis = st.checkbox(
        "Run Hosting Capacity Analysis",
        value=capacity_only_mode,
        disabled=capacity_only_mode,
        help=(
            "Sweeps from 1 to the selected maximum number of HPC centers and runs pandapower at the workload peak. "
            "A center count is unsafe if voltage leaves 0.95–1.05 pu, a line/transformer exceeds 100%, or pp.runpp does not converge."
        ),
    )

    capacity_max_centers = st.slider(
        "Maximum HPC centers to test",
        min_value=1,
        max_value=50,
        value=10,
    )

with st.sidebar.expander("7. Projection Window", expanded=True):
    use_projection_time_window = st.checkbox(
        "Use start/end hours for projection duration",
        value=True,
        help=(
            "If enabled, the projection duration is calculated from a clock window. "
            "Example: 00 to 06 gives 6 hours. This is only an extrapolation window; "
            "the measured trace itself is still integrated with its real CSV timestamps."
        ),
    )

    if use_projection_time_window:
        projection_window_start_hour = st.slider(
            "Projection Window Start Hour",
            min_value=0,
            max_value=23,
            value=0,
            step=1,
            help="Start hour of the selected projection window. Example: 0 means 00:00.",
        )
        projection_window_end_hour = st.slider(
            "Projection Window End Hour",
            min_value=0,
            max_value=24,
            value=1,
            step=1,
            help="End hour of the selected projection window. Example: 6 means 06:00.",
        )
        selected_projection_hours = (projection_window_end_hour - projection_window_start_hour) % 24
        if selected_projection_hours == 0:
            selected_projection_hours = 24
        st.info(
            f"Projection duration = {selected_projection_hours:.2f} h "
            f"from {projection_window_start_hour:02d}:00 to {projection_window_end_hour % 24:02d}:00."
        )
    else:
        selected_projection_hours = st.number_input(
            "Projection Duration (hours)",
            min_value=0.01,
            max_value=24 * 365.0,
            value=1.0,
            step=0.25,
            help="This does not rerun pandapower. It multiplies average simulated power by the selected hours.",
        )

with st.sidebar.expander("8. Delayed Training + Electricity Pricing", expanded=True):
    st.caption(
        "Delayed Training is now a start-time / cost scenario. It does not insert fake idle energy into the trace. "
        "It compares the same workload at a different clock start time under time-of-day prices."
    )

    enable_delayed_training = st.checkbox(
        "Enable Delayed Training / Start-Time Shift",
        value=False,
        disabled=capacity_only_mode,
        help=(
            "Shifts the scenario workload to a later clock start for electricity-price calculation. "
            "Energy stays the same unless another energy scenario is also active."
        ),
    )

    pricing_mode = st.selectbox(
        "Electricity Pricing Method",
        ["Flat price", "German-style time-of-day price"],
        help=(
            "Flat price uses one €/kWh value for all samples, so delayed training cannot change cost. "
            "German-style time-of-day price assigns each sample to a clock-hour tariff period."
        ),
    )

    simulation_start_hour = st.slider(
        "Baseline Workload Start Hour",
        min_value=0,
        max_value=23,
        value=12,
        step=1,
        help="Clock hour when the baseline workload starts.",
    )

    scenario_start_hour = st.slider(
        "Scenario Workload Start Hour",
        min_value=0,
        max_value=23,
        value=0,
        step=1,
        disabled=not enable_delayed_training,
        help=(
            "Clock hour when the delayed/scenario workload starts. "
            "Example: baseline 18 and scenario 0 means the workload is shifted from evening peak to night."
        ),
    )

    delay_hours = (scenario_start_hour - simulation_start_hour) % 24 if enable_delayed_training else 0.0

    electricity_price_eur_per_kwh = st.number_input(
        "Flat Electricity Price (€/kWh)",
        min_value=0.01,
        max_value=2.00,
        value=0.40,
        step=0.01,
        disabled=(pricing_mode == "German-style time-of-day price"),
        help=(
            "Used only when Flat price is selected. Disabled for German-style time-of-day pricing because each hour has its own tariff."
        ),
    )

    if pricing_mode == "German-style time-of-day price":
        st.caption(
            "Editable German-style tariff assumptions. These are scenario inputs, not live market prices. "
            "Defaults use lower night/midday prices and higher morning/evening peak prices."
        )
        tou_night_price = st.number_input(
            "Night / off-peak 00–06 (€/kWh)", 0.01, 2.00, 0.27, 0.01,
            help="Cheaper low-demand night period. Delayed training can reduce cost if shifted here."
        )
        tou_morning_price = st.number_input(
            "Morning peak 06–10 (€/kWh)", 0.01, 2.00, 0.44, 0.01,
            help="Higher demand after the day starts; modeled as expensive."
        )
        tou_midday_price = st.number_input(
            "Midday / renewable window 10–16 (€/kWh)", 0.01, 2.00, 0.31, 0.01,
            help="Often cheaper when solar generation is high."
        )
        tou_evening_peak_price = st.number_input(
            "Evening peak 16–21 (€/kWh)", 0.01, 2.00, 0.50, 0.01,
            help="Highest modeled demand period; delayed training should avoid this if possible."
        )
        tou_late_price = st.number_input(
            "Late evening 21–24 (€/kWh)", 0.01, 2.00, 0.35, 0.01,
            help="After evening peak; usually lower than peak but higher than night."
        )
    else:
        tou_night_price = electricity_price_eur_per_kwh
        tou_morning_price = electricity_price_eur_per_kwh
        tou_midday_price = electricity_price_eur_per_kwh
        tou_evening_peak_price = electricity_price_eur_per_kwh
        tou_late_price = electricity_price_eur_per_kwh

    if show_explanations:
        if enable_delayed_training:
            st.info(
                f"Baseline starts at {simulation_start_hour:02d}:00. "
                f"Scenario starts at {scenario_start_hour:02d}:00. "
                f"Modeled start-time shift = {delay_hours:.2f} h. "
                "Energy is unchanged by this shift; cost changes only when the scenario enters different tariff periods."
            )
        else:
            st.caption("Delayed Training is off. Scenario and baseline use the same clock start time.")

if capacity_only_mode:
    # Hosting Capacity is a grid-limit sweep, not an optimization or scheduling scenario.
    scenario = "Baseline"
    gpu_power_factor = 1.0
    pue_factor = 1.0
    gpu_slowdown_sensitivity = 0.7
    account_for_runtime_slowdown = False
    gpu_runtime_model = "utilization_based"
    enable_load_balancing = False
    max_active_centers = number_of_centers
    load_balancing_strategy = "same_centers_active"
    enable_delayed_training = False
    delay_hours = 0.0

run_button_label = "🚀 Run Hosting Capacity" if capacity_only_mode else "🚀 Run Simulation"
run_button = st.sidebar.button(run_button_label, use_container_width=True)

# Keep the results page visible after widgets inside the dashboard are changed.
# Without this latch, Streamlit sets the button back to False on every rerun
# and the app returns to the intro screen.
if run_button:
    st.session_state["simulation_has_run"] = True

show_results_page = st.session_state.get("simulation_has_run", False)


if not show_results_page:
    tab_intro, tab_modes = st.tabs(["Overview", "Pandapower Modes"])

    with tab_intro:
        st.subheader("Simulation workflow")
        st.markdown(
            """
            1. Load real GPU training/inference power traces  
            2. Compute power sample intervals from CSV timestamps  
            3. Build an averaged training profile  
            4. Convert GPU power to HPC-center facility power  
            5. Inject centers as loads into pandapower  
            6. Run AC power flow for every measured sample  
            7. Calculate energy by integrating power over time  
            """
        )
        st.info("Set the workload, nodes per center, grid backend, and maximum centers in the sidebar. Then click **Run Hosting Capacity**." if capacity_only_mode else "Set the parameters in the sidebar and click **Run Simulation**.")

    with tab_modes:
        st.subheader("Pandapower modes")
        st.markdown(
            """
            | Mode | Status | Meaning |
            |---|---|---|
            | AC Power Flow | Implemented | Voltage, line loading, transformer loading, losses |
            | Time-Series Power Flow | Implemented manually | Repeats AC power flow for workload samples |
            | OPF | Future extension | Optimization under constraints |
            | Short-Circuit | Not used | Fault-current studies |
            | State Estimation | Not used | Measurement-based grid estimation |
            | Controllers | Future extension | Tap changers / voltage control |
            """
        )

else:
    try:
        with st.spinner("Running pandapower simulation..."):
            training_profile = cached_build_training_profile(training_path, inference_path, workload_mode)

            training_profile = convert_training_profile_to_center(
                training_profile,
                nodes_per_center=nodes_per_center,
                cpu_power_per_node=cpu_power_per_node,
                pue=pue,
            )

            baseline_profile = training_profile.copy()

            optimized_profile = apply_optimization_scenario(
                training_profile,
                scenario=scenario,
                gpu_power_factor=gpu_power_factor,
                pue_factor=pue_factor,
                delay_steps=0,
                gpu_slowdown_sensitivity=gpu_slowdown_sensitivity,
                account_for_runtime_slowdown=account_for_runtime_slowdown,
                gpu_runtime_model=gpu_runtime_model,
            )

            # Delayed Training is modeled as a clock start-time shift for pricing only.
            # We do NOT insert idle zero-power samples into the workload trace, because that would
            # distort average power and same-work metrics. The workload energy remains unchanged.

            if enable_load_balancing:
                optimized_profile = apply_center_level_load_balancing(
                    optimized_profile,
                    number_of_centers=number_of_centers,
                    max_active_centers=max_active_centers,
                    strategy=load_balancing_strategy,
                )

            baseline_results = cached_run_hpc_simulation(
                workload_df=baseline_profile,
                number_of_centers=number_of_centers,
                clusters_per_center=clusters_per_center,
                racks_per_cluster=racks_per_cluster,
                fast_mode=fast_mode,
                grid_backend=grid_backend,
                simbench_code=simbench_code,
                include_existing_simbench_loads=include_existing_simbench_loads,
            )

            optimized_results = cached_run_hpc_simulation(
                workload_df=optimized_profile,
                number_of_centers=number_of_centers,
                clusters_per_center=clusters_per_center,
                racks_per_cluster=racks_per_cluster,
                fast_mode=fast_mode,
                grid_backend=grid_backend,
                simbench_code=simbench_code,
                include_existing_simbench_loads=include_existing_simbench_loads,
            )

            baseline_results, baseline_energy_mwh = calculate_energy(baseline_results)
            optimized_results, optimized_energy_mwh = calculate_energy(optimized_results)

            baseline_projection = calculate_energy_projections(baseline_results)
            optimized_projection = calculate_energy_projections(optimized_results)

            price_table = build_tou_price_table(
                night_price=tou_night_price,
                morning_price=tou_morning_price,
                midday_price=tou_midday_price,
                evening_peak_price=tou_evening_peak_price,
                late_price=tou_late_price,
            )

            if pricing_mode == "German-style time-of-day price":
                baseline_cost_df, baseline_trace_cost_eur = calculate_time_of_day_costs(
                    baseline_results,
                    price_table=price_table,
                    simulation_start_hour=simulation_start_hour,
                )
                optimized_cost_df, optimized_trace_cost_eur = calculate_time_of_day_costs(
                    optimized_results,
                    price_table=price_table,
                    simulation_start_hour=(scenario_start_hour if enable_delayed_training else simulation_start_hour),
                )
            else:
                baseline_cost_df, baseline_trace_cost_eur = calculate_costs(
                    baseline_results,
                    price_per_kwh=electricity_price_eur_per_kwh,
                )
                optimized_cost_df, optimized_trace_cost_eur = calculate_costs(
                    optimized_results,
                    price_per_kwh=electricity_price_eur_per_kwh,
                )

            trace_cost_saving_eur = baseline_trace_cost_eur - optimized_trace_cost_eur
            trace_cost_saving_percent = (
                trace_cost_saving_eur / baseline_trace_cost_eur * 100.0
                if baseline_trace_cost_eur > 0 else 0.0
            )

            same_work_metrics = calculate_same_work_metrics(
                baseline_results=baseline_results,
                optimized_results=optimized_results,
                number_of_centers=number_of_centers,
            )

            if enable_delayed_training and delay_hours > 0 and not enable_load_balancing:
                same_work_metrics.update(
                    {
                        "work_completed_ratio": 1.0,
                        "same_work_duration_hours": optimized_projection["trace_duration_hours"],
                        "same_work_energy_mwh": optimized_energy_mwh,
                        "same_work_energy_saving_mwh": baseline_energy_mwh - optimized_energy_mwh,
                        "same_work_energy_saving_percent": (
                            (baseline_energy_mwh - optimized_energy_mwh) / baseline_energy_mwh * 100.0
                            if baseline_energy_mwh > 0 else 0.0
                        ),
                    }
                )

            # Pure center scheduling does not reduce the energy needed for the same work.
            # It lowers simultaneous load inside the visible window by deferring/distributing work.
            # For same-work interpretation, scheduling alone is not counted as an energy-saving mechanism
            # unless a real power-changing scenario (GPU cap / cooling) is also selected.
            if enable_load_balancing and scenario == "Baseline":
                work_ratio = float(same_work_metrics.get("work_completed_ratio", 1.0))
                same_work_metrics.update(
                    {
                        "same_work_duration_hours": baseline_projection["trace_duration_hours"] / max(work_ratio, 1e-9),
                        "same_work_energy_mwh": baseline_energy_mwh,
                        "same_work_energy_saving_mwh": 0.0,
                        "same_work_energy_saving_percent": 0.0,
                    }
                )

            audit_df, audit_notes = build_optimization_audit(
                baseline_energy_mwh=baseline_energy_mwh,
                optimized_energy_mwh=optimized_energy_mwh,
                baseline_projection=baseline_projection,
                optimized_projection=optimized_projection,
                scenario=scenario,
                optimized_profile=optimized_profile,
                gpu_power_factor=gpu_power_factor,
                gpu_slowdown_sensitivity=gpu_slowdown_sensitivity,
                account_for_runtime_slowdown=account_for_runtime_slowdown,
                pue_factor=pue_factor,
                delay_steps=0,
                enable_load_balancing=enable_load_balancing,
                number_of_centers=number_of_centers,
                max_active_centers=max_active_centers,
            )

            if enable_delayed_training and delay_hours > 0:
                delay_row = pd.DataFrame([
                    {
                        "Metric": "Delayed Training / start-time shift",
                        "Baseline": "0.00 h",
                        "Scenario": f"{delay_hours:.2f} h",
                        "Change": f"+{delay_hours:.2f} h before workload starts",
                        "How it is calculated": "No zero-power samples are inserted. The same power trace is priced with a different scenario_start_hour. Energy stays unchanged; cost can change because clock-hour price(t) changes.",
                    },
                    {
                        "Metric": "Scenario workload start clock hour",
                        "Baseline": f"{simulation_start_hour:02d}:00",
                        "Scenario": f"{(simulation_start_hour + delay_hours) % 24:.2f}:00",
                        "Change": "clock shift only",
                        "How it is calculated": "scenario_start_hour = (baseline_start_hour + delay_hours) mod 24.",
                    },
                ])
                audit_df = pd.concat([audit_df, delay_row], ignore_index=True)

            capacity_df = None
            if enable_capacity_analysis:
                capacity_df = run_capacity_analysis(
                    workload_df=training_profile,
                    max_centers=capacity_max_centers,
                    clusters_per_center=clusters_per_center,
                    racks_per_cluster=racks_per_cluster,
                    grid_backend=grid_backend,
                    simbench_code=simbench_code,
                    include_existing_simbench_loads=include_existing_simbench_loads,
                )

            mlperf_raw_summary_df, mlperf_checklist_df = build_mlperf_input_summary(training_path if workload_mode != "Inference Run" else inference_path)
            training_raw_summary_df, training_checklist_df = build_mlperf_input_summary(training_path)
            inference_raw_summary_df, inference_checklist_df = build_mlperf_input_summary(inference_path)
            workload_comparison_df, workload_curve_df = cached_build_workload_comparison(
                training_path=training_path,
                inference_path=inference_path,
                nodes_per_center=nodes_per_center,
                cpu_power_per_node=cpu_power_per_node,
                pue=pue,
                number_of_centers=number_of_centers,
            )

        active_scenario_label = scenario
        if enable_delayed_training and delay_hours > 0:
            active_scenario_label = f"{active_scenario_label} + Delayed Training"
        if enable_load_balancing:
            active_scenario_label = (
                f"{active_scenario_label} + Scheduling "
                f"({load_balancing_strategy}, max {max_active_centers}/{number_of_centers} active)"
            )

        trace_duration_seconds = optimized_projection["trace_duration_seconds"]
        trace_duration_minutes = optimized_projection["trace_duration_minutes"]
        trace_duration_hours = optimized_projection["trace_duration_hours"]

        baseline_timing = describe_workload_timing(simulation_start_hour, trace_duration_hours)
        scenario_pricing_start_hour = scenario_start_hour if enable_delayed_training else simulation_start_hour
        scenario_timing = describe_workload_timing(scenario_pricing_start_hour, trace_duration_hours)
        baseline_tariff_coverage = build_tariff_coverage(baseline_cost_df)
        scenario_tariff_coverage = build_tariff_coverage(optimized_cost_df)

        min_voltage = optimized_results["min_voltage_pu"].min()
        max_trafo = optimized_results["max_transformer_loading_percent"].max()
        max_line = optimized_results["max_line_loading_percent"].max()
        converged_all = optimized_results["converged"].all()

        grid_snapshot = build_pandapower_snapshot(
            workload_df=optimized_profile,
            number_of_centers=number_of_centers,
            clusters_per_center=clusters_per_center,
            racks_per_cluster=racks_per_cluster,
            grid_backend=grid_backend,
            simbench_code=simbench_code,
            include_existing_simbench_loads=include_existing_simbench_loads,
        )
        grid_snapshot_summary = summarize_pandapower_snapshot(grid_snapshot)
        grid_result_tables = build_pandapower_result_tables(grid_snapshot)

        tabs = st.tabs(
            [
                "Overview",
                "Grid / Power-Flow Analysis",
                "Optimization Audit",
                "Cost / Time Pricing",
                "Load Balancing",
                "Hosting Capacity",
                "MLPerf Trace",
                "Workload Comparison",
                "Model Explanation",
                "Calculation Trace",
            ]
        )

        with tabs[0]:
            st.subheader("Measured Trace Simulation")

            st.info(
                f"Trace duration from CSV timestamps: "
                f"{trace_duration_seconds:.0f} seconds "
                f"({trace_duration_minutes:.2f} minutes / {trace_duration_hours:.3f} hours)."
            )

            no_energy_or_scheduling_change = (
                scenario == "Baseline"
                and not enable_load_balancing
                and not (enable_delayed_training and delay_hours > 0)
            )
            metric_case_label = "Current" if no_energy_or_scheduling_change else "Scenario"
            metric_case_detail = "No optimization selected" if no_energy_or_scheduling_change else active_scenario_label

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Baseline Facility Energy",
                format_energy(baseline_energy_mwh),
                help=(
                    "Reference energy before any selected optimization or scheduling. "
                    "Formula: sum(total facility power in MW × sample duration in hours). "
                    "Facility power comes from GPU trace + node assumptions × nodes per center × number of centers × PUE."
                ),
            )
            col2.metric(
                f"{metric_case_label} Facility Energy ({metric_case_detail})",
                format_energy(optimized_energy_mwh),
                help=(
                    "Energy after the currently selected dashboard settings. "
                    "If Scenario = Baseline and scheduling is off, this must equal Baseline Facility Energy. "
                    "Formula: sum(current total facility power in MW × current sample duration in hours)."
                ),
            )
            col3.metric(
                f"{metric_case_label} Weighted Average Power",
                format_power(optimized_projection["average_power_mw"]),
                help=(
                    "Time-weighted average facility power. "
                    "Formula: total integrated energy divided by total trace duration. "
                    "This is better than a simple arithmetic average when CSV sample intervals are irregular."
                ),
            )
            col4.metric(
                f"{metric_case_label} Peak Power",
                format_power(optimized_projection["peak_power_mw"]),
                help=(
                    "Highest instantaneous total facility power in the simulated trace. "
                    "This is the value most relevant for grid stress and transformer/line peak loading."
                ),
            )

            if no_energy_or_scheduling_change:
                st.success(
                    "No optimization or scheduling is active. The Current values are intentionally identical to the Baseline values."
                )
            else:
                st.info(
                    f"Active comparison: Baseline vs {metric_case_detail}. See the Optimization Audit tab for every changed variable."
                )

            st.caption(
                "Baseline = measured GPU trace scaled to node / center / facility power. "
                "Current/Scenario = same workload after the selected sidebar settings. "
                "Energy is calculated as Σ Power(t) × Δt using CSV timestamp intervals."
            )

            st.subheader("Model Sanity Check")
            total_configured_nodes = number_of_centers * nodes_per_center
            avg_power_per_node_kw = (baseline_projection["average_power_mw"] * 1000) / max(total_configured_nodes, 1)
            avg_center_power_mw = baseline_projection["average_power_mw"] / max(number_of_centers, 1)
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric(
                "Total Configured Nodes",
                f"{total_configured_nodes:,}",
                help="Formula: number of HPC centers × nodes per HPC center. Clusters and racks only distribute the load electrically; they do not multiply total power.",
            )
            sc2.metric(
                "Baseline Avg Power per Node",
                f"{avg_power_per_node_kw:.2f} kW",
                help="Formula: baseline weighted average facility power / total configured nodes. Includes GPU trace, CPU/RAM/storage/network assumptions and PUE.",
            )
            sc3.metric(
                "Baseline Avg Power per Center",
                format_power(avg_center_power_mw),
                help="Formula: baseline weighted average facility power / number of centers.",
            )

            if number_of_centers == 20 and nodes_per_center == 50 and baseline_projection["average_power_mw"] > 2.0:
                st.warning(
                    "Sanity warning: for 20 centers × 50 nodes, an average above 2 MW is unusually high for this measured single-GPU trace. "
                    "Your displayed ~7–8 MW result matches 20 centers × 500 nodes much better than 20 centers × 50 nodes. "
                    "Check that the Nodes per HPC Center slider is really 50, not 500."
                )

            st.subheader("Trace Cost Result")

            cost1, cost2, cost3 = st.columns(3)
            cost1.metric(
                "Baseline Trace Cost",
                f"{baseline_trace_cost_eur:,.2f} €",
                help="Formula: Σ energy_kwh(t) × price(t). Uses the selected flat or time-of-day pricing method.",
            )
            cost2.metric(
                f"Scenario Trace Cost ({active_scenario_label})",
                f"{optimized_trace_cost_eur:,.2f} €",
                help="Scenario cost. For Delayed Training this can change because samples are shifted to later clock hours.",
            )
            cost3.metric(
                "Trace Cost Difference",
                f"{trace_cost_saving_eur:,.2f} €",
                f"{trace_cost_saving_percent:.2f} %",
                help="Positive means cheaper than baseline. This is cost saving, not necessarily energy saving.",
            )

            if enable_delayed_training and delay_hours > 0:
                st.warning(
                    "Delayed Training is not an energy optimization. It shifts demand in time. "
                    "Energy should remain approximately unchanged unless another energy scenario is active; cost may change only when time-of-day prices are enabled."
                )

            st.subheader("Estimated Energy and Cost Projection")

            selected_energy_mwh = calculate_energy_for_hours(
                optimized_projection["average_power_mw"],
                selected_projection_hours,
            )
            selected_cost_eur = selected_energy_mwh * 1000 * electricity_price_eur_per_kwh

            p1, p2, p3 = st.columns(3)
            p1.metric(
                "Selected Duration",
                f"{selected_projection_hours:.2f} h",
                help="User-selected projection horizon from the sidebar. This does not change the measured trace; it only extrapolates from average power.",
            )
            p2.metric(
                "Projected Energy",
                format_energy(selected_energy_mwh),
                help="Formula: current weighted average power × selected duration in hours.",
            )
            p3.metric(
                "Projected Cost (flat-price estimate)",
                f"{selected_cost_eur:,.2f} €",
                help="Projection uses selected energy × flat electricity price. Exact time-of-day trace cost is shown in the Cost / Time Pricing tab.",
            )

            projection_df = pd.DataFrame(
                [
                    {
                        "Duration": f"Selected: {selected_projection_hours:.2f} h",
                        "Formula": f"Average power × {selected_projection_hours:.2f} h",
                        "Estimated Energy": format_energy(selected_energy_mwh),
                        "Estimated Cost": f"{selected_cost_eur:,.2f} €",
                    },
                    {
                        "Duration": "1 Hour",
                        "Formula": "Average power × 1 h",
                        "Estimated Energy": format_energy(optimized_projection["energy_1h_mwh"]),
                        "Estimated Cost": f"{optimized_projection['energy_1h_mwh'] * 1000 * electricity_price_eur_per_kwh:,.2f} €",
                    },
                    {
                        "Duration": "6 Hours",
                        "Formula": "Average power × 6 h",
                        "Estimated Energy": format_energy(optimized_projection["energy_6h_mwh"]),
                        "Estimated Cost": f"{optimized_projection['energy_6h_mwh'] * 1000 * electricity_price_eur_per_kwh:,.2f} €",
                    },
                    {
                        "Duration": "24 Hours",
                        "Formula": "Average power × 24 h",
                        "Estimated Energy": format_energy(optimized_projection["energy_24h_mwh"]),
                        "Estimated Cost": f"{optimized_projection['energy_24h_mwh'] * 1000 * electricity_price_eur_per_kwh:,.2f} €",
                    },
                    {
                        "Duration": "30 Days",
                        "Formula": "Average power × 24 × 30 h",
                        "Estimated Energy": format_energy(optimized_projection["energy_30d_mwh"]),
                        "Estimated Cost": f"{optimized_projection['energy_30d_mwh'] * 1000 * electricity_price_eur_per_kwh:,.2f} €",
                    },
                ]
            )

            st.dataframe(projection_df, use_container_width=True, hide_index=True)

            st.caption(
                "Projection values do not rerun pandapower. "
                "They use weighted average power from the simulated trace and multiply by the selected duration."
            )

            st.subheader("Same-Work Interpretation")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric(
                "Work Completed in Window",
                f"{same_work_metrics['work_completed_ratio'] * 100:.1f} %",
                help="Compares how much work is completed inside the simulated time window. Scheduling fewer centers may reduce this percentage.",
            )
            s2.metric(
                "Same-Work Runtime",
                f"{same_work_metrics['same_work_duration_hours']:.2f} h",
                help="Estimated runtime required to complete the same amount of work as the baseline.",
            )
            s3.metric(
                "Same-Work Energy",
                format_energy(same_work_metrics["same_work_energy_mwh"]),
                help="Energy needed for the same total work, not just the energy inside the visible simulation window.",
            )
            s4.metric(
                "Same-Work Energy Saving",
                format_energy(same_work_metrics["same_work_energy_saving_mwh"]),
                f"{same_work_metrics['same_work_energy_saving_percent']:.1f} %",
                help="Baseline same-work energy minus scenario same-work energy. This is the same-work saving metric; it avoids counting deferred work as energy efficiency.",
            )

            st.caption(
                "If fewer centers are active, the same job may take longer. "
                "Window energy can drop, but same-work energy only drops if power per unit of work is actually reduced."
            )

            if enable_load_balancing and scenario == "Baseline":
                st.warning(
                    "Scheduling-only result: the lower scenario trace energy is NOT an energy saving. "
                    "It means only part of the center-time work is executed inside the simulated window. "
                    "The same-work energy saving is therefore 0%."
                )

            st.subheader("Grid Health Status")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Minimum Voltage", "N/A" if pd.isna(min_voltage) else f"{min_voltage:.3f} pu")
            c2.metric("Max Transformer Loading", "N/A" if pd.isna(max_trafo) else f"{max_trafo:.1f}%")
            c3.metric("Max Line Loading", "N/A" if pd.isna(max_line) else f"{max_line:.1f}%")
            c4.metric("Power Flow Converged", "Yes" if converged_all else "No")

        with tabs[1]:
            st.subheader("⚡ Pandapower Grid Dashboard")
            st.caption(
                "This tab is the electrical-engineering view of the project. It uses the same solved pandapower network as the simulation, "
                "then exposes voltage, loading, losses, external-grid supply and element-level result tables in a cleaner order."
            )

            net = grid_snapshot["net"]
            bus_df = grid_result_tables.get("bus", pd.DataFrame())
            line_df = grid_result_tables.get("line", pd.DataFrame())
            trafo_df = grid_result_tables.get("trafo", pd.DataFrame())
            load_df = grid_result_tables.get("load", pd.DataFrame())
            ext_df = grid_result_tables.get("ext_grid", pd.DataFrame())

            backend_label = grid_backend
            if grid_backend == "SimBench German benchmark grid":
                backend_label = f"SimBench benchmark grid ({simbench_code})"

            st.info(
                f"Grid backend: **{backend_label}**. "
                "The detailed values below come from pandapower result tables after `pp.runpp()`: "
                "`net.res_bus`, `net.res_line`, `net.res_trafo`, `net.res_load`, and `net.res_ext_grid`. "
                "For readability, the full element-level time-series result is summarized over time; the peak-load snapshot tables can be downloaded."
            )

            invalid_reasons = diagnose_invalid_powerflow_snapshot(grid_snapshot_summary, grid_snapshot)
            if invalid_reasons:
                st.error("No valid pandapower AC power-flow result for this grid-load combination.")
                st.warning(
                    "The selected grid is probably too weak for the injected HPC load, or pandapower could not produce valid "
                    "`net.res_*` result tables. The dashboard will not show misleading NaN/0 W grid KPIs for this case."
                )
                st.markdown("#### Why the result is invalid")
                st.write("\n".join([f"- {reason}" for reason in invalid_reasons]))
                st.markdown("#### What to try")
                st.dataframe(
                    build_invalid_snapshot_recommendations(grid_snapshot, grid_snapshot_summary),
                    use_container_width=True,
                    hide_index=True,
                )
                st.info(
                    "Recommended quick test: switch from an LV SimBench grid to an MV SimBench grid, or reduce centers/nodes. "
                    "For the full 20-center HPC scenario, use the Synthetic HPC grid or an MV/HV-level benchmark scenario."
                )
                st.stop()

            # Main grid health KPIs
            st.markdown("### 1. Grid health at peak-load snapshot")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(
                "External grid supply",
                format_power(grid_snapshot_summary["external_grid_p_mw"]),
                help="Active power supplied by the slack/external grid. Source: sum(net.res_ext_grid.p_mw). It can be higher than the applied HPC load because it also covers existing grid loads and network losses.",
            )
            k2.metric(
                "Applied HPC load",
                format_power(grid_snapshot_summary["applied_load_p_mw"]),
                help="Scheduled HPC active load applied to the pandapower network at the selected peak snapshot.",
            )
            k3.metric(
                "Total active losses",
                format_power(grid_snapshot_summary["total_losses_mw"]),
                help="Line losses + transformer losses. Source: sum(net.res_line.pl_mw) + sum(net.res_trafo.pl_mw).",
            )
            k4.metric(
                "Worst voltage",
                f"{grid_snapshot_summary['min_voltage_pu']:.4f} pu",
                help="Minimum bus voltage from net.res_bus.vm_pu. 0.95–1.05 pu is used as a practical operating band here.",
            )
            k5.metric(
                "Worst loading",
                f"L {grid_snapshot_summary['max_line_loading_percent']:.1f}% / T {grid_snapshot_summary['max_trafo_loading_percent']:.1f}%",
                help="Maximum line and transformer loading from net.res_line.loading_percent and net.res_trafo.loading_percent.",
            )

            health_df = build_grid_health_cards(grid_snapshot_summary)
            st.dataframe(health_df, use_container_width=True, hide_index=True)

            extra_k1, extra_k2, extra_k3, extra_k4 = st.columns(4)
            extra_k1.metric(
                "External grid reactive power",
                f"{grid_snapshot_summary.get('external_grid_q_mvar', 0.0):.2f} MVAr",
                help="Reactive power supplied or absorbed by the external grid. Source: sum(net.res_ext_grid.q_mvar).",
            )
            extra_k2.metric(
                "Power factor",
                f"{grid_snapshot_summary.get('power_factor', float('nan')):.4f}",
                help="Calculated from external-grid active/reactive power: P / sqrt(P² + Q²).",
            )
            extra_k3.metric(
                "Loss share",
                f"{grid_snapshot_summary.get('loss_percent_of_supply', 0.0):.3f}%",
                help="Total active network losses divided by external-grid active power supply.",
            )
            extra_k4.metric(
                "Voltage violations",
                f"{int(grid_snapshot_summary.get('voltage_violations', 0))}",
                help="Number of buses outside the 0.95–1.05 pu voltage band at the peak snapshot.",
            )

            st.markdown("### 2. Security checks at peak-load snapshot")
            st.caption("These checks turn the raw pandapower result tables into clear grid-limit indicators.")
            st.dataframe(build_snapshot_violation_table(grid_snapshot_summary), use_container_width=True, hide_index=True)

            st.markdown("### 3. Time-series power-flow behavior")
            st.caption(
                "These plots are part of the grid analysis. They use the per-timestep values extracted from pandapower after every `pp.runpp()` call."
            )

            ts_col1, ts_col2 = st.columns(2)
            with ts_col1:
                power_df = build_comparison_df(baseline_results, optimized_results, "total_power_mw")
                fig_power = px.area(
                    power_df,
                    x="elapsed_hours" if "elapsed_hours" in power_df.columns else "timestep",
                    y="total_power_mw",
                    color="case",
                    title="Grid demand over time",
                    labels={"total_power_mw": "Power demand (MW)", "elapsed_hours": "Elapsed time (h)", "case": "Case"},
                )
                fig_power.update_layout(template="plotly_white", height=380, hovermode="x unified")
                st.plotly_chart(fig_power, use_container_width=True)
            with ts_col2:
                voltage_df = build_comparison_df(baseline_results, optimized_results, "min_voltage_pu")
                fig_voltage = px.line(
                    voltage_df,
                    x="elapsed_hours" if "elapsed_hours" in voltage_df.columns else "timestep",
                    y="min_voltage_pu",
                    color="case",
                    title="Minimum bus voltage over time",
                    labels={"min_voltage_pu": "Minimum voltage (pu)", "elapsed_hours": "Elapsed time (h)", "case": "Case"},
                )
                fig_voltage.add_hline(y=0.95, line_dash="dash", annotation_text="0.95 pu limit")
                fig_voltage.update_layout(template="plotly_white", height=380, hovermode="x unified")
                st.plotly_chart(fig_voltage, use_container_width=True)

            ts_col3, ts_col4 = st.columns(2)
            with ts_col3:
                loading_baseline = baseline_results[["elapsed_hours", "max_line_loading_percent", "max_transformer_loading_percent"]].copy()
                loading_baseline["case"] = "Baseline"
                loading_scenario = optimized_results[["elapsed_hours", "max_line_loading_percent", "max_transformer_loading_percent"]].copy()
                loading_scenario["case"] = "Scenario"
                loading_df = pd.concat([loading_baseline, loading_scenario], ignore_index=True)
                loading_long = loading_df.melt(
                    id_vars=["elapsed_hours", "case"],
                    value_vars=["max_line_loading_percent", "max_transformer_loading_percent"],
                    var_name="Metric",
                    value_name="Loading percent",
                )
                loading_long["Metric"] = loading_long["Metric"].replace({
                    "max_line_loading_percent": "Worst line/cable loading",
                    "max_transformer_loading_percent": "Worst transformer loading",
                })
                fig_loading = px.line(
                    loading_long,
                    x="elapsed_hours",
                    y="Loading percent",
                    color="Metric",
                    line_dash="case",
                    title="Worst loading over time",
                    labels={"elapsed_hours": "Elapsed time (h)"},
                )
                fig_loading.add_hline(y=100, line_dash="dash", annotation_text="100% limit")
                fig_loading.update_layout(template="plotly_white", height=400, hovermode="x unified")
                st.plotly_chart(fig_loading, use_container_width=True)
            with ts_col4:
                loss_cols = [c for c in ["line_losses_mw", "transformer_losses_mw", "total_losses_mw"] if c in optimized_results.columns]
                if loss_cols:
                    losses_df = optimized_results[["elapsed_hours"] + loss_cols].copy()
                    losses_long = losses_df.melt(id_vars="elapsed_hours", value_vars=loss_cols, var_name="Loss type", value_name="Losses MW")
                    losses_long["Loss type"] = losses_long["Loss type"].replace({
                        "line_losses_mw": "Line losses",
                        "transformer_losses_mw": "Transformer losses",
                        "total_losses_mw": "Total losses",
                    })
                    fig_losses_time = px.line(
                        losses_long,
                        x="elapsed_hours",
                        y="Losses MW",
                        color="Loss type",
                        title="Active losses over time (scenario)",
                        labels={"elapsed_hours": "Elapsed time (h)"},
                    )
                    fig_losses_time.update_layout(template="plotly_white", height=400, hovermode="x unified")
                    st.plotly_chart(fig_losses_time, use_container_width=True)

            with st.expander("Reactive power and grid-limit violations over time", expanded=False):
                r1, r2 = st.columns(2)
                with r1:
                    if "external_grid_q_mvar" in optimized_results.columns:
                        fig_q = px.line(
                            optimized_results,
                            x="elapsed_hours",
                            y="external_grid_q_mvar",
                            title="External-grid reactive power over time",
                            labels={"external_grid_q_mvar": "Reactive power (MVAr)", "elapsed_hours": "Elapsed time (h)"},
                        )
                        fig_q.update_layout(template="plotly_white", height=360, hovermode="x unified")
                        st.plotly_chart(fig_q, use_container_width=True)
                with r2:
                    violation_cols = [c for c in ["voltage_violation_count", "line_overload_count", "transformer_overload_count"] if c in optimized_results.columns]
                    if violation_cols:
                        viol_df = optimized_results[["elapsed_hours"] + violation_cols].melt(id_vars="elapsed_hours", value_vars=violation_cols, var_name="Violation type", value_name="Count")
                        viol_df["Violation type"] = viol_df["Violation type"].replace({
                            "voltage_violation_count": "Voltage violations",
                            "line_overload_count": "Line overloads",
                            "transformer_overload_count": "Transformer overloads",
                        })
                        fig_viol = px.area(
                            viol_df,
                            x="elapsed_hours",
                            y="Count",
                            color="Violation type",
                            title="Grid-limit violations over time",
                            labels={"elapsed_hours": "Elapsed time (h)"},
                        )
                        fig_viol.update_layout(template="plotly_white", height=360, hovermode="x unified")
                        st.plotly_chart(fig_viol, use_container_width=True)

            st.markdown("### 4. What does the grid look like?")
            topology_view = st.radio(
                "Choose grid view",
                ["HPC engineering diagram", "Interactive PyVis topology", "Readable electrical layers", "Actual pandapower topology"],
                horizontal=True,
                help=(
                    "Engineering diagram shows the modeled HPC centers clearly. "
                    "Readable layers explain the electrical hierarchy. Actual topology uses real pandapower buses/lines/transformers."
                ),
            )
            if topology_view == "HPC engineering diagram":
                st.info(
                    "This view makes the modeled facilities visible: each HPC Center is shown as a large block connected to the grid by a service cable/line. "
                    "The values come from the actual pandapower objects: HPC buses in net.bus, service cables in net.line, and rack loads in net.load."
                )
                fig_hpc_engineering = create_hpc_engineering_diagram(
                    net,
                    number_of_centers=number_of_centers,
                    clusters_per_center=clusters_per_center,
                    racks_per_cluster=racks_per_cluster,
                    snapshot_summary=grid_snapshot_summary,
                    max_centers_to_draw=12,
                )
                st.plotly_chart(fig_hpc_engineering, use_container_width=True)
                hpc_summary_df = _extract_hpc_center_summary(net)
                if len(hpc_summary_df):
                    st.caption("HPC Center summary from actual pandapower load/bus objects.")
                    st.dataframe(
                        hpc_summary_df.rename(columns={
                            "center_id": "HPC Center",
                            "hpc_bus": "HPC bus",
                            "grid_bus": "Grid bus",
                            "service_line": "Service line",
                            "vn_kv": "Voltage level kV",
                            "vm_pu": "Voltage pu",
                            "p_mw": "Active load MW",
                            "q_mvar": "Reactive load MVAr",
                            "rack_load_elements": "Rack/load elements",
                            "service_line_loading_percent": "Service line loading %",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )
            elif topology_view == "Interactive PyVis topology":
                st.info(
                    "Interactive topology view: pan/zoom, drag nodes, and hover buses, lines, transformers, and HPC Centers. "
                    "This view is generated from the solved pandapower network but does not change the simulation."
                )
                pv_col1, pv_col2 = st.columns([1, 1])
                with pv_col1:
                    pyvis_focus_worst_area = st.checkbox(
                        "Focus around worst-voltage area",
                        value=False,
                        help="Show a smaller neighborhood around the bus with the lowest voltage. Useful for large SimBench grids.",
                    )
                with pv_col2:
                    pyvis_hops = st.slider(
                        "PyVis neighborhood depth",
                        min_value=1,
                        max_value=5,
                        value=3,
                        help="Number of graph hops to include around the worst-voltage bus when focus mode is active.",
                    )
                pyvis_html = create_pyvis_pandapower_topology_html(
                    net,
                    max_buses=300,
                    focus_worst_area=pyvis_focus_worst_area,
                    hops=pyvis_hops,
                )
                components.html(pyvis_html, height=840, scrolling=True)
            elif topology_view == "Readable electrical layers":
                fig_layered = create_layered_grid_figure(
                    number_of_centers=number_of_centers,
                    clusters_per_center=clusters_per_center,
                    racks_per_cluster=racks_per_cluster,
                    snapshot_summary=grid_snapshot_summary,
                )
                st.plotly_chart(fig_layered, use_container_width=True)
                st.caption(
                    "This is an explanatory electrical abstraction. The full pandapower object counts and tables below use every model element."
                )
            else:
                st.info(
                    "This view draws the actual pandapower bus/line/transformer topology. "
                    "Use the HPC engineering diagram if you want the facility-level view."
                )
                topo_col1, topo_col2 = st.columns([1, 1])
                with topo_col1:
                    focus_worst_area = st.checkbox(
                        "Focus around worst-voltage bus",
                        value=False,
                        help="If enabled, show only the local electrical neighborhood around the bus with the lowest voltage. Useful for large grids.",
                    )
                with topo_col2:
                    topo_hops = st.slider(
                        "Neighborhood depth",
                        min_value=1,
                        max_value=4,
                        value=2,
                        help="How many electrical hops around the worst-voltage bus are shown when focus mode is enabled.",
                    )
                try:
                    fig_actual_grid = create_actual_pandapower_network_figure(
                        net,
                        max_buses=260,
                        focus_worst_area=focus_worst_area,
                        hops=topo_hops,
                    )
                    st.plotly_chart(fig_actual_grid, use_container_width=True)
                except Exception as topo_error:
                    st.error("Topology drawing failed, but the pandapower calculation results are still valid.")
                    st.exception(topo_error)
                    st.info("Use the voltage/loading tables below. This error affects only visualization, not pp.runpp().")
                legend_df = pd.DataFrame([
                    {"Visual item": "Green bus", "Meaning": "Voltage normal", "Rule": "0.97 ≤ vm_pu ≤ 1.03"},
                    {"Visual item": "Yellow bus", "Meaning": "Voltage close to limit", "Rule": "0.95–0.97 or 1.03–1.05 pu"},
                    {"Visual item": "Red bus", "Meaning": "Voltage violation", "Rule": "vm_pu < 0.95 or vm_pu > 1.05"},
                    {"Visual item": "Orange square", "Meaning": "HPC Center bus", "Rule": "actual pandapower bus with HPC rack loads attached"},
                    {"Visual item": "Orange dashed edge", "Meaning": "HPC service connection line/cable", "Rule": "net.line branch connecting grid bus to HPC center bus"},
                    {"Visual item": "Grey/orange/red edge", "Meaning": "Line or cable", "Rule": "Width/color increase with loading_percent"},
                    {"Visual item": "Purple dotted edge + diamond", "Meaning": "Transformer", "Rule": "net.trafo / net.res_trafo"},
                    {"Visual item": "Blue star", "Meaning": "External grid / slack bus", "Rule": "net.ext_grid"},
                ])
                st.dataframe(legend_df, use_container_width=True, hide_index=True)

            st.markdown("### 4. Pandapower result charts")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.plotly_chart(create_voltage_distribution_figure(bus_df), use_container_width=True)
            with chart_col2:
                st.plotly_chart(create_voltage_box_figure(bus_df), use_container_width=True)

            st.plotly_chart(create_losses_bar_figure(grid_snapshot_summary), use_container_width=True)

            chart_col3, chart_col4 = st.columns(2)
            with chart_col3:
                st.plotly_chart(
                    create_top_loading_figure(
                        line_df,
                        "res_loading_percent",
                        "Most loaded lines/cables",
                        "Line/cable",
                        top_n=15,
                    ),
                    use_container_width=True,
                )
            with chart_col4:
                st.plotly_chart(
                    create_top_loading_figure(
                        trafo_df,
                        "res_loading_percent",
                        "Most loaded transformers",
                        "Transformer",
                        top_n=15,
                    ),
                    use_container_width=True,
                )

            chart_col5, chart_col6 = st.columns(2)
            with chart_col5:
                st.plotly_chart(create_loading_distribution_figure(line_df, trafo_df), use_container_width=True)
            with chart_col6:
                st.plotly_chart(create_power_balance_figure(grid_snapshot_summary), use_container_width=True)

            st.markdown("### 5. Time-series grid behavior")
            st.caption(
                "These charts use the repeated pandapower simulation results over all measured CSV samples. "
                "They show whether voltage/loading problems appear only at peak time or throughout the trace."
            )
            st.plotly_chart(create_grid_timeseries_figure(optimized_results, "Scenario grid constraints over time"), use_container_width=True)
            violation_df = build_grid_violation_summary(optimized_results)
            st.dataframe(violation_df, use_container_width=True, hide_index=True)

            ts_col1, ts_col2 = st.columns(2)
            with ts_col1:
                st.plotly_chart(create_losses_timeseries_figure(optimized_results), use_container_width=True)
            with ts_col2:
                st.plotly_chart(create_reactive_power_figure(optimized_results), use_container_width=True)

            st.plotly_chart(create_violation_timeseries_figure(optimized_results), use_container_width=True)

            st.markdown("### 6. Worst timestep analysis")
            st.caption("This finds the measured sample where each grid metric is most critical.")
            worst_ts_df = build_worst_timestep_table(optimized_results)
            st.dataframe(worst_ts_df, use_container_width=True, hide_index=True)

            st.markdown("### 7. Critical elements and flow directions")
            worst_elements_df = build_worst_elements_table(grid_result_tables, n=5)
            if len(worst_elements_df):
                st.dataframe(worst_elements_df, use_container_width=True, hide_index=True)
            else:
                st.info("No element-level result rows were available for this snapshot.")

            st.markdown("#### Strongest line-flow directions")
            st.caption("Shows where active power is flowing on the strongest lines. Direction is inferred from net.res_line.p_from_mw / p_to_mw.")
            flow_df = build_line_flow_direction_table(line_df, n=10)
            if len(flow_df):
                st.dataframe(flow_df, use_container_width=True, hide_index=True)
            else:
                st.info("Line-flow direction data was not available for this grid backend or snapshot.")

            st.markdown("### 8. N-1 contingency check")
            st.caption("Simple robustness test: remove the most loaded lines/transformers one at a time and rerun AC power flow. This is not OPF and does not change dispatch; it only checks grid security after an outage.")
            nminus_df = run_n_minus_one_contingency(grid_snapshot, top_n=3)
            if len(nminus_df):
                st.dataframe(nminus_df, use_container_width=True, hide_index=True)
            else:
                st.info("N-1 check was not available because the snapshot did not converge or no candidate elements were present.")

            st.markdown("### 9. Network object counts")
            element_counts = pd.DataFrame([
                {"Pandapower object": "Buses", "Count": len(net.bus), "Input table": "net.bus", "Result table": "net.res_bus"},
                {"Pandapower object": "Lines", "Count": len(net.line), "Input table": "net.line", "Result table": "net.res_line"},
                {"Pandapower object": "Transformers", "Count": len(net.trafo), "Input table": "net.trafo", "Result table": "net.res_trafo"},
                {"Pandapower object": "Loads", "Count": len(net.load), "Input table": "net.load", "Result table": "net.res_load"},
                {"Pandapower object": "External grids", "Count": len(net.ext_grid), "Input table": "net.ext_grid", "Result table": "net.res_ext_grid"},
            ])
            st.dataframe(element_counts, use_container_width=True, hide_index=True)

            with st.expander("Full pandapower result tables and downloads", expanded=False):
                st.caption(
                    "Input columns describe configured elements. Result columns are prefixed with `res_` and come from the solved AC power-flow result tables."
                )
                table_options = {
                    "bus + res_bus": bus_df,
                    "line + res_line": line_df,
                    "trafo + res_trafo": trafo_df,
                    "load + res_load": load_df,
                    "ext_grid + res_ext_grid": ext_df,
                }
                selected_table_name = st.selectbox("Pandapower table", list(table_options.keys()), key="grid_table_selector_v22")
                selected_table_df = table_options[selected_table_name]
                st.dataframe(selected_table_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download selected table as CSV",
                    data=dataframe_to_csv_bytes(selected_table_df),
                    file_name=f"{selected_table_name.replace(' ', '_').replace('+', 'plus')}.csv",
                    mime="text/csv",
                    key="grid_download_selected_table_v22",
                )

                raw_names = []
                for name in ["sgen", "gen", "storage", "switch", "shunt", "ward", "xward", "impedance", "dcline", "res_sgen", "res_gen", "res_storage", "res_switch", "res_shunt"]:
                    if hasattr(net, name):
                        try:
                            tbl = getattr(net, name)
                            if isinstance(tbl, pd.DataFrame) and len(tbl) > 0:
                                raw_names.append(name)
                        except Exception:
                            pass
                if raw_names:
                    raw_choice = st.selectbox("Additional raw pandapower table", raw_names, key="grid_raw_table_selector_v22")
                    raw_df = getattr(net, raw_choice).reset_index().rename(columns={"index": "element_index"})
                    st.dataframe(raw_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download additional raw table as CSV",
                        data=dataframe_to_csv_bytes(raw_df),
                        file_name=f"{raw_choice}.csv",
                        mime="text/csv",
                        key="grid_download_raw_table_v22",
                    )
                else:
                    st.info("No non-empty additional pandapower tables such as sgen/gen/storage/switch were present in this snapshot.")

            with st.expander("What is stored from the full time-series run?", expanded=False):
                st.markdown(
                    """
                    The app runs pandapower for every workload sample. To keep the simulation fast and memory-safe, the time-series table stores the most important extracted values per timestep:

                    - `min_voltage_pu` from `net.res_bus.vm_pu`
                    - `max_line_loading_percent` from `net.res_line.loading_percent`
                    - `max_transformer_loading_percent` from `net.res_trafo.loading_percent`
                    - `converged` from the pandapower solver state
                    - `total_power_mw`, `active_centers`, and energy integration columns

                    The full element-level `net.res_*` tables are shown for the peak-load snapshot because storing every bus/line/trafo result for every timestep can become very large.
                    """
                )
        with tabs[2]:
            st.subheader("Optimization Audit: What Changed From Baseline")

            st.dataframe(audit_df, use_container_width=True, hide_index=True)

            st.markdown(
                f"""
                **Scenario:** {scenario}  
                **Energy formula:** Energy = Σ Power(t) × Δt  
                **Modeled rule:** {audit_notes['formula']}  
                **GPU cap runtime model:** {audit_notes.get('performance_model', 'not active')}
                """
            )

            if scenario in ["GPU Power Limit", "Combined Optimization"]:
                st.warning(
                    "A GPU power limit is not automatically a 10% energy saving. "
                    "This version uses measured GPU utilization from `gpu_util_percent` when the utilization-based model is selected. "
                    "Same-work energy depends on lower GPU power, fixed non-GPU node power, and longer runtime."
                )


        with tabs[7]:
            st.subheader("Training vs Inference vs Simultaneous Workload")
            st.markdown(
                """
                This comparison uses the same facility scaling settings as the main simulation.
                It does **not** rerun pandapower for every option; it compares the electrical load profile that would be injected into the grid.
                
                - **Training Run:** averaged MLPerf training trace.
                - **Inference Run:** averaged inference trace.
                - **Simultaneous:** training trace plus a repeated inference pattern running at the same time.
                """
            )

            if workload_comparison_df.empty:
                st.warning("No workload comparison could be built. Check the training/inference folders.")
            else:
                c1, c2, c3 = st.columns(3)
                peak_row = workload_comparison_df.loc[workload_comparison_df["Peak total grid load (MW)"].idxmax()]
                energy_row = workload_comparison_df.loc[workload_comparison_df["Integrated trace energy (MWh)"].idxmax()]
                c1.metric("Highest peak load", f"{peak_row['Peak total grid load (MW)']:.2f} MW", peak_row["Workload"])
                c2.metric("Highest trace energy", f"{energy_row['Integrated trace energy (MWh)']:.2f} MWh", energy_row["Workload"])
                c3.metric("Selected workload", workload_mode)

                fig_workload_power = px.line(
                    workload_curve_df,
                    x="elapsed_hours",
                    y="total_power_mw",
                    color="Workload",
                    title="Grid load profile comparison: training, inference and simultaneous operation",
                    labels={
                        "elapsed_hours": "Elapsed time (hours)",
                        "total_power_mw": "Total facility load injected into grid (MW)",
                    },
                    template="plotly_white",
                )
                fig_workload_power.update_traces(line=dict(width=2.6))
                fig_workload_power.update_layout(
                    height=470,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    margin=dict(l=20, r=20, t=70, b=30),
                )
                st.plotly_chart(fig_workload_power, use_container_width=True)

                bar_df = workload_comparison_df.melt(
                    id_vars="Workload",
                    value_vars=["Avg total grid load (MW)", "Peak total grid load (MW)", "Integrated trace energy (MWh)"],
                    var_name="Metric",
                    value_name="Value",
                )
                fig_workload_bar = px.bar(
                    bar_df,
                    x="Workload",
                    y="Value",
                    color="Metric",
                    barmode="group",
                    title="Which workload affects the grid more?",
                    template="plotly_white",
                )
                fig_workload_bar.update_layout(height=430, margin=dict(l=20, r=20, t=70, b=30))
                st.plotly_chart(fig_workload_bar, use_container_width=True)

                display_df = workload_comparison_df.copy()
                for col in ["Trace duration (h)", "Avg total grid load (MW)", "Peak total grid load (MW)", "Integrated trace energy (MWh)"]:
                    display_df[col] = display_df[col].map(lambda x: f"{x:.3f}")
                for col in ["Avg GPU power (W)", "Peak GPU power (W)", "Avg GPU util (%)"]:
                    if col in display_df:
                        display_df[col] = display_df[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                st.info(
                    "Interpretation: training usually stresses the grid longer, inference can create short high-utilization bursts, "
                    "and simultaneous operation approximates a data-center situation where training jobs and serving jobs run together."
                )

        with tabs[8]:
            st.subheader("Model Explanation: What Data and Formulas Are Used")

            st.markdown(
                """
                ### Data used from CSV
                - `timestamp`: calculates `delta_seconds` and total trace duration.
                - `total_gpu_power_w`: measured GPU power used as the base GPU power trace.
                - `gpu_util_percent`: measured GPU utilization used for the utilization-based power-cap runtime model.

                ### Facility scaling
                `node_power_w = gpu_power_w + cpu_power_w + ram_power_w + storage_power_w + network_power_w`

                `center_power_mw = node_power_w × nodes_per_center × PUE / 1,000,000`

                `total_grid_power_mw = center_power_mw × active_centers`

                ### Improved Cooling / PUE model
                Improved Cooling is not a total-load multiplier. It reduces only the non-IT overhead from PUE.

                `IT_power = center_it_power_w`

                `overhead_power = center_total_power_w - center_it_power_w`

                `new_overhead_power = overhead_power × cooling_overhead_factor`

                `new_total_power = IT_power + new_overhead_power`

                `new_PUE = 1 + (baseline_PUE - 1) × cooling_overhead_factor`

                Example: if PUE = 1.30 and cooling factor = 0.85, then `new_PUE = 1.255` and total facility multiplier is `1.255 / 1.30 = 0.965`. So the energy saving is about 3.5%, not 15%.

                ### Energy integration
                `energy_mwh = Σ total_grid_power_mw(t) × delta_seconds(t) / 3600`

                ### GPU Power Limit model
                The GPU cap uses measured utilization instead of one fixed fake slowdown value:

                `u(t) = gpu_util_percent(t) / 100`

                `p(t) = 1 - alpha × u(t) × (1 - gpu_power_factor)`

                `delta_seconds_new(t) = delta_seconds_old(t) / p(t)`

                This means highly utilized GPU phases slow down more than low-utilization phases.

                ### Time-of-day electricity price model
                Cost is not calculated from energy alone when time-of-day pricing is enabled.

                `energy_kwh(t) = total_power_mw(t) × delta_seconds(t) / 3600 × 1000`

                `clock_hour(t) = simulation_start_hour + elapsed_time(t)`

                `cost(t) = energy_kwh(t) × price(clock_hour(t))`

                `total_cost = Σ cost(t)`

                Delayed Training therefore does not reduce energy by itself. It can reduce or increase cost depending on whether the shifted load lands in cheaper or more expensive price periods.

                ### Important interpretation
                A 10% lower GPU power cap does not automatically produce 10% energy savings, because runtime can increase.
                Improved Cooling reduces only non-IT facility overhead: new_total = IT_power + overhead_power × cooling_factor. It does not change ML runtime.
                Delayed Training is a scheduling/cost scenario: energy saving should be 0 unless another power-reduction scenario is also active.
                """
            )

            if "gpu_util_percent" in training_profile.columns:
                util_col1, util_col2, util_col3 = st.columns(3)
                util_col1.metric(
                    "Average GPU Utilization",
                    f"{training_profile['gpu_util_percent'].mean():.1f}%",
                    help="Measured CSV column gpu_util_percent averaged across all training runs and timesteps.",
                )
                util_col2.metric(
                    "Minimum GPU Utilization",
                    f"{training_profile['gpu_util_percent'].min():.1f}%",
                    help="Minimum measured utilization in the averaged training profile.",
                )
                util_col3.metric(
                    "Maximum GPU Utilization",
                    f"{training_profile['gpu_util_percent'].max():.1f}%",
                    help="Maximum measured utilization in the averaged training profile.",
                )

                fig_util = px.line(
                    training_profile,
                    x="elapsed_hours",
                    y="gpu_util_percent",
                    title="Measured GPU Utilization Used by the Runtime Model",
                    hover_data=["gpu_util_percent", "gpu_power_w", "delta_seconds"],
                )
                st.plotly_chart(fig_util, use_container_width=True)

            if "gpu_performance_factor_t" in optimized_profile.columns:
                fig_perf = px.line(
                    optimized_profile,
                    x="elapsed_hours",
                    y="gpu_performance_factor_t",
                    title="Modeled Performance Factor per Timestep under GPU Power Cap",
                    hover_data=["gpu_utilization_fraction", "gpu_performance_factor_t", "gpu_runtime_multiplier_t"],
                )
                st.plotly_chart(fig_perf, use_container_width=True)

            st.info(
                "This model is explainable and data-driven, but it is still a model. "
                "The strongest validation would be a second real run with the GPU power cap applied and measured directly."
            )

        with tabs[3]:
            st.subheader("Cost / Time-of-Day Pricing")

            st.info(
                "Delayed Training is kept as a scheduling/cost scenario. It does not save energy by itself. "
                "It can reduce cost only if the same workload is shifted into cheaper clock-hour price periods."
            )

            cst1, cst2, cst3, cst4 = st.columns(4)
            cst1.metric(
                "Baseline Trace Cost",
                f"{baseline_trace_cost_eur:,.2f} €",
                help="Formula: Σ energy_kwh(t) × price(t).",
            )
            cst2.metric(
                f"Scenario Trace Cost ({active_scenario_label})",
                f"{optimized_trace_cost_eur:,.2f} €",
                help="Cost of the current scenario trace using the selected pricing method.",
            )
            cst3.metric(
                "Trace Cost Difference",
                f"{trace_cost_saving_eur:,.2f} €",
                f"{trace_cost_saving_percent:.2f} %",
                help="Positive means the scenario is cheaper than baseline. For delayed training this can change even when energy is unchanged.",
            )
            cst4.metric(
                "Pricing Method",
                pricing_mode,
                help="Flat price uses one price. Time-of-day price changes price by clock-hour period.",
            )

            st.subheader("Workload Timing Used for Price Calculation")
            st.caption(
                "This states exactly how long the measured workload runs and where it lies on the 24-hour tariff clock. "
                "The workload duration comes from the CSV timestamps; the start hour is a scenario input."
            )

            timing_df = pd.DataFrame(
                [
                    {
                        "Case": "Baseline",
                        "Start time": baseline_timing["start_label"],
                        "End time": baseline_timing["end_label"],
                        "Duration": f"{baseline_timing['duration_hours']:.3f} h",
                        "Crosses midnight": "Yes" if baseline_timing["crosses_midnight"] else "No",
                        "Explanation": "Original workload clock placement used for baseline cost.",
                    },
                    {
                        "Case": "Scenario",
                        "Start time": scenario_timing["start_label"],
                        "End time": scenario_timing["end_label"],
                        "Duration": f"{scenario_timing['duration_hours']:.3f} h",
                        "Crosses midnight": "Yes" if scenario_timing["crosses_midnight"] else "No",
                        "Explanation": "Same measured workload placed at the scenario start time for pricing. The clock shift changes price assignment, not physical energy.",
                    },
                ]
            )
            st.dataframe(timing_df, use_container_width=True, hide_index=True)

            if enable_delayed_training:
                st.info(
                    f"Delayed Training pricing comparison: baseline workload runs from "
                    f"{baseline_timing['start_label']} to {baseline_timing['end_label']} "
                    f"({baseline_timing['duration_hours']:.3f} h). Scenario workload runs from "
                    f"{scenario_timing['start_label']} to {scenario_timing['end_label']} "
                    f"({scenario_timing['duration_hours']:.3f} h). Cost changes only because these samples can fall into different tariff periods."
                )

            st.subheader("Paper-Style Timeline: Power Demand with Electricity Price Overlay")
            st.caption(
                "Both charts are rendered at once so switching views does not rerun or stop the simulation. "
                "Use these as paper-style figures for explaining how the same workload is priced at different clock times."
            )
            timeline_tabs = st.tabs(["Scenario timeline", "Baseline timeline"])
            with timeline_tabs[0]:
                fig_overlay = create_power_price_overlay(
                    optimized_cost_df,
                    title=(
                        f"Scenario workload: {scenario_timing['start_label']}–{scenario_timing['end_label']} "
                        f"({scenario_timing['duration_hours']:.3f} h)"
                    ),
                )
                st.plotly_chart(fig_overlay, use_container_width=True)
            with timeline_tabs[1]:
                fig_overlay_baseline = create_power_price_overlay(
                    baseline_cost_df,
                    title=(
                        f"Baseline workload: {baseline_timing['start_label']}–{baseline_timing['end_label']} "
                        f"({baseline_timing['duration_hours']:.3f} h)"
                    ),
                )
                st.plotly_chart(fig_overlay_baseline, use_container_width=True)

            st.markdown(
                """
                **Cost formula**

                `energy_kwh(t) = total_power_mw(t) × delta_seconds(t) / 3600 × 1000`

                `cost(t) = energy_kwh(t) × price_eur_per_kwh(t)`

                `total_cost = Σ cost(t)`

                For **Delayed Training**, the measured power trace is priced at a different clock time. Physical energy stays the same; cost changes only when `price(t)` changes.
                """
            )

            if pricing_mode == "German-style time-of-day price":
                st.subheader("Assumed Time-of-Day Tariff")
                st.dataframe(price_table, use_container_width=True, hide_index=True)

                st.subheader("Baseline Tariff Coverage")
                st.caption("How much of the baseline workload runtime, energy and cost lies in each price period.")
                st.dataframe(baseline_tariff_coverage, use_container_width=True, hide_index=True)

                st.subheader("Scenario Tariff Coverage")
                st.caption("How much of the delayed/scenario workload runtime, energy and cost lies in each price period.")
                st.dataframe(scenario_tariff_coverage, use_container_width=True, hide_index=True)
            else:
                st.caption("Flat price selected: every sample uses the same €/kWh value.")

        with tabs[4]:
            st.subheader("Load Balancing / Workload Scheduling")

            st.markdown(
                """
                This tab tests whether section **4. Workload Scheduling Across Centers** behaves correctly.

                **Expected behavior**
                - `same_centers_active`: the same first centers stay active for all timesteps.
                - `rotating_centers`: the active set moves through the centers over time, so work is distributed more fairly.
                - `variable_activity`: the number of active centers changes over time, and the active subset rotates so all centers can participate.

                Scheduling changes **where and when load appears**. A lower trace energy in this tab means less work was executed inside the visible window. It is not a real energy saving unless a power-changing scenario is also active.
                """
            )

            if not enable_load_balancing:
                st.info(
                    "Workload Scheduling is disabled. Enable it in sidebar section 4, choose max active centers and a strategy, then run again."
                )
            else:
                summary_df = build_scheduling_summary(optimized_profile, number_of_centers)
                if not summary_df.empty:
                    st.subheader("Scheduling Sanity Check")
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric(
                    "Strategy",
                    load_balancing_strategy,
                    help="Scheduling rule selected in sidebar section 4.",
                )
                c2.metric(
                    "Max simultaneous centers",
                    f"{max_active_centers} / {number_of_centers}",
                    help="Upper limit for centers allowed to receive workload at the same timestep.",
                )
                c3.metric(
                    "Observed max active centers",
                    f"{int(optimized_results['active_centers'].max())}",
                    help="Should be <= the configured max simultaneous centers.",
                )
                c4.metric(
                    "Peak power change",
                    f"{(optimized_results['total_power_mw'].max() - baseline_results['total_power_mw'].max()):.3f} MW",
                    help="Negative means scheduling lowered the peak grid load in the simulated trace.",
                )

                st.subheader("1) Active Center Count")
                st.caption(
                    "Use this plot to verify the simultaneous number of active centers. "
                    "same_centers_active and rotating_centers should be flat; variable_activity should move up and down."
                )
                st.plotly_chart(create_active_centers_figure(optimized_results), use_container_width=True)

                st.subheader("2) Center Activity Heatmap")
                st.caption(
                    "Green means the center receives load at that timestep. This is the easiest way to see whether rotation or variable activity is really happening."
                )
                activity_cols = get_center_activity_columns(optimized_profile)
                if activity_cols:
                    st.plotly_chart(create_center_activity_heatmap(optimized_profile), use_container_width=True)
                else:
                    st.warning("No center_X_active columns found. Scheduling columns were not generated.")

                st.subheader("3) Per-Center Runtime / Fairness")
                runtime_table = build_center_runtime_table(optimized_profile)
                if not runtime_table.empty:
                    st.dataframe(runtime_table, use_container_width=True, hide_index=True)
                    fig_runtime = px.bar(
                        runtime_table,
                        x="Center",
                        y="Active share (%)",
                        title="Per-center active share: scheduling fairness check",
                    )
                    fig_runtime.update_layout(template="plotly_white", height=430, yaxis_title="Active share (%)")
                    st.plotly_chart(fig_runtime, use_container_width=True)

                st.subheader("4) Power Impact on Grid")
                st.caption(
                    "This figure shows whether scheduling reduces simultaneous grid load. If fewer centers are active at once, peak power should usually decrease."
                )
                st.plotly_chart(create_power_scheduling_comparison(baseline_results, optimized_results), use_container_width=True)

                with st.expander("How to test the three strategies", expanded=True):
                    st.markdown(
                        """
                        **Test A — same_centers_active**  
                        Set `Maximum Simultaneously Active Centers = 5` with `20` total centers.  
                        Expected: heatmap shows only centers 1–5 active; active-center line is flat at 5.

                        **Test B — rotating_centers**  
                        Keep max active centers at 5.  
                        Expected: active-center line is still flat at 5, but the heatmap diagonal/rotation pattern moves across centers. Per-center active shares should become much more balanced.

                        **Test C — variable_activity**  
                        Keep max active centers at 5.  
                        Expected: active-center line rises and falls between 1 and 5. The heatmap should also rotate across centers. Total power should rise and fall with active centers.
                        """
                    )

                with st.expander("Raw scheduled simulation output", expanded=False):
                    st.dataframe(optimized_results, use_container_width=True)

        with tabs[5]:
            st.subheader("Hosting Capacity / Grid Allowance Test")
            st.caption(
                "This tab answers one question: how many HPC centers with the selected workload and nodes-per-center can this grid host before a pandapower limit fails? "
                "It uses the peak-load sample and sweeps the number of HPC centers from 1 to the selected maximum."
            )

            with st.expander("What is used and what is ignored in Hosting Capacity mode?", expanded=True):
                st.markdown(
                    """
                    **Used inputs**
                    - selected workload type: Training / Inference / Simultaneous
                    - nodes per center, CPU power, PUE, rack/cluster structure
                    - selected grid backend: Synthetic or SimBench
                    - peak measured workload sample
                    - maximum number of centers to test

                    **Ignored inputs**
                    - GPU power-cap optimization
                    - cooling optimization
                    - delayed training / electricity price
                    - workload scheduling across centers

                    The reason is simple: hosting capacity is a grid-limit test. It asks: **if we add more equal HPC centers with the same peak load, when does the grid become unsafe?**
                    """
                )

            if capacity_df is None:
                st.warning(
                    "Hosting Capacity has not been run yet. Enable **Hosting Capacity mode** or **Run Hosting Capacity Analysis** in the sidebar, choose the grid and max centers, then press the run button."
                )
            else:
                safe_df = capacity_df[capacity_df["grid_ok"] == True]
                fail_df = capacity_df[capacity_df["grid_ok"] == False]
                max_safe_centers = safe_df["centers"].max() if len(safe_df) > 0 else 0
                first_fail = fail_df.iloc[0] if len(fail_df) > 0 else None

                if first_fail is None:
                    first_fail_text = "No failure in tested range"
                    fail_reason = "All tested center counts remained inside voltage/loading/convergence limits."
                    fail_element = "None"
                else:
                    first_fail_text = f"{int(first_fail['centers'])} centers"
                    fail_reason = str(first_fail.get("failure_reason", "constraint violation"))
                    fail_name = str(first_fail.get("failing_element_name", ""))
                    fail_idx = first_fail.get("failing_element_index", "")
                    fail_comp = str(first_fail.get("failing_component", ""))
                    fail_element = f"{fail_comp} | index {fail_idx} | {fail_name}".strip()

                cap1, cap2, cap3, cap4 = st.columns(4)
                cap1.metric(
                    "Maximum safe HPC centers",
                    f"{int(max_safe_centers)}",
                    help="Largest tested center count where pp.runpp converged and voltage, line loading, and transformer loading stayed within limits.",
                )
                cap2.metric(
                    "First failing point",
                    first_fail_text,
                    help="First center count that violates a grid constraint or does not converge.",
                )
                cap3.metric(
                    "Failure reason",
                    fail_reason[:42] + ("..." if len(fail_reason) > 42 else ""),
                    help=fail_reason,
                )
                cap4.metric(
                    "Grid backend",
                    backend_label,
                    help="Hosting capacity depends strongly on the selected synthetic or SimBench grid.",
                )

                if first_fail is not None:
                    st.error(f"First failing element: **{fail_element}**")
                else:
                    st.success("No failure occurred within the tested range.")

                st.markdown("### Safe vs failing operating region")
                cap_plot = capacity_df.copy()
                cap_plot["Status"] = cap_plot["grid_ok"].map({True: "Safe", False: "Failing"})
                fig_status = px.scatter(
                    cap_plot,
                    x="centers",
                    y="peak_power_mw",
                    color="Status",
                    symbol="Status",
                    size="peak_power_mw",
                    title="Hosting capacity: injected peak power as HPC centers increase",
                    labels={"centers": "HPC centers", "peak_power_mw": "Injected peak HPC power (MW)"},
                    hover_data=[
                        "failure_reason",
                        "failing_component",
                        "failing_element_name",
                        "min_voltage_pu",
                        "max_transformer_loading_percent",
                        "max_line_loading_percent",
                    ],
                )
                fig_status.update_layout(template="plotly_white", height=420)
                st.plotly_chart(fig_status, use_container_width=True)

                st.markdown("### Which limit fails first?")
                cvol, cload = st.columns(2)
                with cvol:
                    fig_capacity_voltage = px.line(
                        capacity_df,
                        x="centers",
                        y="min_voltage_pu",
                        markers=True,
                        title="Voltage limit check",
                        labels={"min_voltage_pu": "Minimum bus voltage (pu)", "centers": "HPC centers"},
                        hover_data=["grid_ok", "failure_reason", "failing_element_name"],
                    )
                    fig_capacity_voltage.add_hline(y=0.95, line_dash="dash", annotation_text="lower limit 0.95 pu")
                    fig_capacity_voltage.add_hline(y=1.05, line_dash="dash", annotation_text="upper limit 1.05 pu")
                    fig_capacity_voltage.update_layout(template="plotly_white", height=390)
                    st.plotly_chart(fig_capacity_voltage, use_container_width=True)
                with cload:
                    loading_long = capacity_df.melt(
                        id_vars=["centers", "grid_ok", "failure_reason", "failing_element_name"],
                        value_vars=["max_transformer_loading_percent", "max_line_loading_percent"],
                        var_name="Component",
                        value_name="Loading percent",
                    )
                    loading_long["Component"] = loading_long["Component"].replace({
                        "max_transformer_loading_percent": "Transformer",
                        "max_line_loading_percent": "Line/cable",
                    })
                    fig_capacity_loading = px.line(
                        loading_long,
                        x="centers",
                        y="Loading percent",
                        color="Component",
                        markers=True,
                        title="Line and transformer loading limit check",
                        labels={"centers": "HPC centers"},
                        hover_data=["grid_ok", "failure_reason", "failing_element_name"],
                    )
                    fig_capacity_loading.add_hline(y=100, line_dash="dash", annotation_text="100% loading limit")
                    fig_capacity_loading.update_layout(template="plotly_white", height=390)
                    st.plotly_chart(fig_capacity_loading, use_container_width=True)

                st.markdown("### Exact failure table")
                show_cols = [
                    "centers",
                    "peak_power_mw",
                    "grid_ok",
                    "failure_reason",
                    "failing_component",
                    "failing_element_index",
                    "failing_element_name",
                    "failing_value",
                    "threshold",
                    "min_voltage_pu",
                    "max_voltage_pu",
                    "max_line_loading_percent",
                    "max_transformer_loading_percent",
                    "converged",
                ]
                st.dataframe(capacity_df[[c for c in show_cols if c in capacity_df.columns]], use_container_width=True, hide_index=True)

        with tabs[9]:
            st.subheader("Calculation Trace")

            st.markdown(
                """
                | Metric | Source | Formula / Method |
                |---|---|---|
                | GPU Power | CSV | Instantaneous GPU power sample in watts |
                | Sample Duration | CSV timestamps | Time difference between power samples |
                | RAM Power | Assumption | 40 W per node |
                | Storage Power | Assumption | 10 W per node |
                | Network Power | Assumption | 10 W per node |
                | Node Power | Model | GPU + CPU + RAM + Storage + Network |
                | Center Power | Model | Node Power × Nodes per Center × PUE |
                | Total Power | Model | Center Power × Active Centers |
                | Energy in Trace | Integration | Σ Power(t) × Δt |
                | Estimated 1h / 24h Energy | Projection | Average MW × hours |
                | Minimum Voltage | pandapower | `min(net.res_bus["vm_pu"])` |
                | Transformer Loading | pandapower | `max(net.res_trafo["loading_percent"])` |
                | Line Loading | pandapower | `max(net.res_line["loading_percent"])` |
                """
            )

            example_gpu_power = training_profile["gpu_power_w"].mean()
            example_node_power = training_profile["node_power_w"].mean()
            example_center_power = training_profile["center_total_power_mw"].mean()

            st.code(
                f"""
Average GPU Power:
{example_gpu_power:.2f} W

Node Power:
GPU + CPU + RAM + Storage + Network
= {example_gpu_power:.2f} + {cpu_power_per_node} + 40 + 10 + 10
= {example_node_power:.2f} W

Average HPC Center Power:
Node Power × Nodes per Center × PUE
= {example_node_power:.2f} × {nodes_per_center} × {pue}
= {example_center_power:.4f} MW

Energy in trace:
Σ Power(t) × Δt

Estimated 24h Energy:
Average Power × 24 hours
= {optimized_projection['average_power_mw']:.4f} MW × 24
= {optimized_projection['energy_24h_mwh']:.4f} MWh
                """
            )

            fig_profile = px.line(
                training_profile,
                x="timestep",
                y="gpu_power_w",
                title="Average GPU Power Across Training Runs",
                hover_data=["gpu_power_w", "gpu_power_std", "delta_seconds"],
            )
            st.plotly_chart(fig_profile, use_container_width=True)

            fig_std = px.line(
                training_profile,
                x="timestep",
                y="gpu_power_std",
                title="Training Profile Stability",
                hover_data=["gpu_power_std"],
            )
            st.plotly_chart(fig_std, use_container_width=True)

        with tabs[6]:
            st.subheader("MLPerf Measured Trace Pipeline")
            st.markdown(
                """
                This tab documents the **measured MLPerf input data** before it is scaled to node, center, facility and grid level.
                The simulation uses the averaged trace generated from the CSV files in the selected training folder.
                """
            )

            if mlperf_raw_summary_df.empty:
                st.warning("No raw CSV files could be inspected. Check the Training CSV Folder path.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Raw MLPerf runs", f"{len(mlperf_raw_summary_df)}")
                c2.metric("Representative samples", f"{len(training_profile):,}")
                c3.metric("Avg GPU power", f"{training_profile['total_gpu_power_w'].mean():.2f} W")
                c4.metric("Avg GPU utilization", f"{training_profile['gpu_util_percent'].mean():.1f}%")

                st.subheader("Data quality checklist")
                st.dataframe(mlperf_checklist_df, use_container_width=True, hide_index=True)

                st.subheader("Raw run summary")
                st.caption("Each row is one uploaded MLPerf measurement run. These values are measured before HPC scaling.")
                st.dataframe(mlperf_raw_summary_df, use_container_width=True, hide_index=True)

                st.subheader("Representative averaged MLPerf trace")
                st.caption(
                    "The app trims all runs to the shortest common length, averages GPU power/utilization per timestep, "
                    "and keeps real sample intervals from the timestamps."
                )

                fig_mlperf_power = go.Figure()
                fig_mlperf_power.add_trace(
                    go.Scatter(
                        x=training_profile["elapsed_hours"],
                        y=training_profile["total_gpu_power_w"],
                        mode="lines",
                        name="Average total GPU power (W)",
                        line=dict(width=2.4),
                    )
                )
                fig_mlperf_power.add_trace(
                    go.Scatter(
                        x=training_profile["elapsed_hours"],
                        y=training_profile["gpu_util_percent"],
                        mode="lines",
                        name="Average GPU utilization (%)",
                        yaxis="y2",
                        line=dict(width=2.0, dash="dot"),
                    )
                )
                fig_mlperf_power.update_layout(
                    title="Measured MLPerf workload trace: GPU power and utilization",
                    xaxis_title="Elapsed time (hours)",
                    yaxis=dict(title="GPU power (W)"),
                    yaxis2=dict(title="GPU utilization (%)", overlaying="y", side="right", range=[0, 100]),
                    hovermode="x unified",
                    template="plotly_white",
                    height=430,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                st.plotly_chart(fig_mlperf_power, use_container_width=True)

                fig_variability = px.line(
                    training_profile,
                    x="elapsed_hours",
                    y="gpu_power_std",
                    title="Run-to-run GPU power variability after alignment",
                    labels={
                        "elapsed_hours": "Elapsed time (hours)",
                        "gpu_power_std": "Standard deviation across runs (W)",
                    },
                    template="plotly_white",
                )
                fig_variability.update_traces(line=dict(width=2.4))
                fig_variability.update_layout(height=360)
                st.plotly_chart(fig_variability, use_container_width=True)

                st.subheader("How this trace enters the pandapower simulation")
                st.markdown(
                    f"""
                    1. **Measured input:** `total_gpu_power_w(t)` and `gpu_util_percent(t)` from the MLPerf CSV files.  
                    2. **Node power model:** GPU power + CPU/RAM/storage/network assumptions.  
                    3. **Facility scaling:** node power × `{nodes_per_center}` nodes × PUE `{pue}`.  
                    4. **Grid injection:** resulting center power is written into pandapower load elements as `p_mw`; reactive demand is modeled as `q_mvar = p_mw × 0.33`.  
                    5. **Power-flow result:** pandapower calculates bus voltages, line/transformer loading, losses and external grid supply for every timestep.
                    """
                )

                st.info(
                    "The workload profile is measured from MLPerf GPU training runs. "
                    "CPU power, facility PUE, center size, and grid topology remain configurable modeling assumptions."
                )

    except Exception as error:
        st.error("Simulation failed.")
        st.exception(error)
