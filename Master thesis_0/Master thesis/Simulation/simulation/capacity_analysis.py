import pandas as pd
import pandapower as pp

from simulation.grid_model import create_hpc_grid


def _apply_workload_row_to_grid(net, center_load_map, row):
    """Apply one workload row to the pandapower net and return total applied HPC load."""
    center_power_mw = float(row["center_total_power_mw"])
    active_centers = 0

    for center_id, load_indices in center_load_map.items():
        active_column = f"center_{center_id}_active"
        is_active = int(row[active_column]) if active_column in row else 1
        if is_active:
            active_centers += 1

        center_load_mw = center_power_mw if is_active else 0.0
        power_per_rack = center_load_mw / max(len(load_indices), 1)
        for load_idx in load_indices:
            net.load.at[load_idx, "p_mw"] = power_per_rack
            net.load.at[load_idx, "q_mvar"] = power_per_rack * 0.33

    return center_power_mw * active_centers, active_centers


def _safe_name(table, idx):
    try:
        if idx is not None and idx in table.index and "name" in table.columns:
            return str(table.at[idx, "name"])
    except Exception:
        pass
    return ""


def _evaluate_capacity_snapshot(
    workload_df: pd.DataFrame,
    centers: int,
    clusters_per_center: int,
    racks_per_cluster: int,
    voltage_low_limit_pu: float,
    voltage_high_limit_pu: float,
    transformer_limit_percent: float,
    line_limit_percent: float,
    grid_backend: str,
    simbench_code: str,
    include_existing_simbench_loads: bool,
):
    """Run one peak-load snapshot and return aggregate + first failure details."""
    peak_idx = workload_df["center_total_power_mw"].idxmax()
    peak_row = workload_df.loc[peak_idx].copy()
    peak_row["timestep"] = 0

    net, center_load_map = create_hpc_grid(
        number_of_centers=centers,
        clusters_per_center=clusters_per_center,
        racks_per_cluster=racks_per_cluster,
        grid_backend=grid_backend,
        simbench_code=simbench_code,
        include_existing_simbench_loads=include_existing_simbench_loads,
    )
    peak_power, active_centers = _apply_workload_row_to_grid(net, center_load_map, peak_row)

    base = {
        "centers": centers,
        "active_centers": active_centers,
        "peak_power_mw": peak_power,
        "min_voltage_pu": None,
        "max_voltage_pu": None,
        "max_transformer_loading_percent": None,
        "max_line_loading_percent": None,
        "converged": False,
        "voltage_ok": False,
        "voltage_high_ok": False,
        "transformer_ok": False,
        "line_ok": False,
        "grid_ok": False,
        "failure_reason": "Power flow did not converge",
        "failing_component": "power_flow",
        "failing_element_index": None,
        "failing_element_name": "pandapower runpp",
        "failing_value": None,
        "threshold": "converged=True",
        "grid_backend": grid_backend,
        "simbench_code": simbench_code if "SimBench" in grid_backend else "not used",
    }

    try:
        pp.runpp(net, algorithm="nr", max_iteration=30)
    except Exception as exc:
        base["failure_reason"] = f"Power flow did not converge: {exc}"
        return base

    converged = bool(getattr(net, "converged", False))
    base["converged"] = converged
    if not converged:
        return base

    # Extract solved result values safely.
    res_bus = net.res_bus if hasattr(net, "res_bus") else pd.DataFrame()
    res_line = net.res_line if hasattr(net, "res_line") else pd.DataFrame()
    res_trafo = net.res_trafo if hasattr(net, "res_trafo") else pd.DataFrame()

    min_voltage = float(res_bus["vm_pu"].min()) if "vm_pu" in res_bus.columns and len(res_bus) else None
    max_voltage = float(res_bus["vm_pu"].max()) if "vm_pu" in res_bus.columns and len(res_bus) else None
    max_line = float(res_line["loading_percent"].max()) if "loading_percent" in res_line.columns and len(res_line) else 0.0
    max_trafo = float(res_trafo["loading_percent"].max()) if "loading_percent" in res_trafo.columns and len(res_trafo) else 0.0

    base.update({
        "min_voltage_pu": min_voltage,
        "max_voltage_pu": max_voltage,
        "max_transformer_loading_percent": max_trafo,
        "max_line_loading_percent": max_line,
    })

    voltage_ok = min_voltage is not None and min_voltage >= voltage_low_limit_pu
    voltage_high_ok = max_voltage is None or max_voltage <= voltage_high_limit_pu
    transformer_ok = max_trafo <= transformer_limit_percent
    line_ok = max_line <= line_limit_percent

    base.update({
        "voltage_ok": bool(voltage_ok),
        "voltage_high_ok": bool(voltage_high_ok),
        "transformer_ok": bool(transformer_ok),
        "line_ok": bool(line_ok),
    })

    # First failure reason in a deterministic order.
    if not voltage_ok:
        idx = int(res_bus["vm_pu"].idxmin())
        base.update({
            "failure_reason": f"Low voltage: {min_voltage:.4f} pu < {voltage_low_limit_pu:.2f} pu",
            "failing_component": "bus_voltage_low",
            "failing_element_index": idx,
            "failing_element_name": _safe_name(net.bus, idx),
            "failing_value": min_voltage,
            "threshold": f">= {voltage_low_limit_pu:.2f} pu",
        })
    elif not voltage_high_ok:
        idx = int(res_bus["vm_pu"].idxmax())
        base.update({
            "failure_reason": f"High voltage: {max_voltage:.4f} pu > {voltage_high_limit_pu:.2f} pu",
            "failing_component": "bus_voltage_high",
            "failing_element_index": idx,
            "failing_element_name": _safe_name(net.bus, idx),
            "failing_value": max_voltage,
            "threshold": f"<= {voltage_high_limit_pu:.2f} pu",
        })
    elif not line_ok:
        idx = int(res_line["loading_percent"].idxmax()) if len(res_line) else None
        base.update({
            "failure_reason": f"Line/cable overload: {max_line:.1f}% > {line_limit_percent:.0f}%",
            "failing_component": "line_overload",
            "failing_element_index": idx,
            "failing_element_name": _safe_name(net.line, idx),
            "failing_value": max_line,
            "threshold": f"<= {line_limit_percent:.0f}%",
        })
    elif not transformer_ok:
        idx = int(res_trafo["loading_percent"].idxmax()) if len(res_trafo) else None
        base.update({
            "failure_reason": f"Transformer overload: {max_trafo:.1f}% > {transformer_limit_percent:.0f}%",
            "failing_component": "transformer_overload",
            "failing_element_index": idx,
            "failing_element_name": _safe_name(net.trafo, idx),
            "failing_value": max_trafo,
            "threshold": f"<= {transformer_limit_percent:.0f}%",
        })
    else:
        base.update({
            "grid_ok": True,
            "failure_reason": "OK",
            "failing_component": "none",
            "failing_element_index": None,
            "failing_element_name": "none",
            "failing_value": None,
            "threshold": "all limits satisfied",
        })

    return base


def run_capacity_analysis(
    workload_df: pd.DataFrame,
    max_centers: int,
    clusters_per_center: int,
    racks_per_cluster: int,
    voltage_limit_pu: float = 0.95,
    transformer_limit_percent: float = 100.0,
    line_limit_percent: float = 100.0,
    grid_backend: str = "Synthetic HPC grid",
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_simbench_loads: bool = True,
) -> pd.DataFrame:
    """
    Hosting capacity analysis.

    It uses the peak-power timestep and increases the number of modeled HPC centers
    until voltage, transformer, line, or convergence limits fail.
    This is a grid allowance test, not an energy-saving scenario.
    """
    if workload_df.empty:
        raise ValueError("workload_df is empty; capacity analysis cannot run.")

    rows = []
    for centers in range(1, max_centers + 1):
        rows.append(_evaluate_capacity_snapshot(
            workload_df=workload_df,
            centers=centers,
            clusters_per_center=clusters_per_center,
            racks_per_cluster=racks_per_cluster,
            voltage_low_limit_pu=voltage_limit_pu,
            voltage_high_limit_pu=1.05,
            transformer_limit_percent=transformer_limit_percent,
            line_limit_percent=line_limit_percent,
            grid_backend=grid_backend,
            simbench_code=simbench_code,
            include_existing_simbench_loads=include_existing_simbench_loads,
        ))

    return pd.DataFrame(rows)
