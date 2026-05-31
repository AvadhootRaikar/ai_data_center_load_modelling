"""
HPC Power Flow Simulation Runner

Executes time-series AC power flow simulation using pandapower
for each timestep of the workload.
"""

import pandas as pd
import pandapower as pp
from grid_model import create_hpc_grid


def run_hpc_simulation(
    workload_df: pd.DataFrame,
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
    fast_mode: bool = False,
    grid_backend: str = "Synthetic HPC grid",
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_simbench_loads: bool = True,
) -> pd.DataFrame:
    """
    Runs pandapower power flow for each timestep.
    
    Parameters:
    -----------
    fast_mode : bool
        If True, uses DC power flow (faster); if False, uses AC power flow
    grid_backend : str
        "Synthetic HPC grid" or "SimBench German benchmark grid"
    """
    net, center_load_map = create_hpc_grid(
        number_of_centers=number_of_centers,
        clusters_per_center=clusters_per_center,
        racks_per_cluster=racks_per_cluster,
        grid_backend=grid_backend,
        simbench_code=simbench_code,
        include_existing_simbench_loads=include_existing_simbench_loads,
    )

    results = []
    elapsed_seconds = 0.0

    for _, row in workload_df.iterrows():
        center_power_mw = row["center_total_power_mw"]
        delta_seconds = float(row.get("delta_seconds", 5.0))
        elapsed_seconds += delta_seconds

        active_centers = 0

        for center_id, load_indices in center_load_map.items():
            active_column = f"center_{center_id}_active"

            if active_column in row:
                is_active = int(row[active_column])
            else:
                is_active = 1

            if is_active:
                active_centers += 1

            center_load_mw = center_power_mw if is_active else 0.0
            power_per_rack = center_load_mw / max(len(load_indices), 1)

            for load_idx in load_indices:
                net.load.at[load_idx, "p_mw"] = power_per_rack
                net.load.at[load_idx, "q_mvar"] = power_per_rack * 0.33

        total_power_mw = center_power_mw * active_centers

        try:
            if fast_mode:
                pp.rundcpp(net)
                converged = True
            else:
                pp.runpp(net, algorithm="nr", max_iteration=30)
                converged = net.converged

            min_voltage = net.res_bus["vm_pu"].min() if not fast_mode else None
            max_voltage = net.res_bus["vm_pu"].max() if not fast_mode else None

            max_trafo = net.res_trafo["loading_percent"].max() if len(net.res_trafo) else 0.0
            max_line = net.res_line["loading_percent"].max() if len(net.res_line) else 0.0

            line_losses_mw = float(net.res_line["pl_mw"].sum()) if hasattr(net, "res_line") and "pl_mw" in net.res_line.columns else 0.0
            trafo_losses_mw = float(net.res_trafo["pl_mw"].sum()) if hasattr(net, "res_trafo") and "pl_mw" in net.res_trafo.columns else 0.0
            total_losses_mw = line_losses_mw + trafo_losses_mw

            ext_grid_p_mw = float(net.res_ext_grid["p_mw"].sum()) if hasattr(net, "res_ext_grid") and "p_mw" in net.res_ext_grid.columns else 0.0
            ext_grid_q_mvar = float(net.res_ext_grid["q_mvar"].sum()) if hasattr(net, "res_ext_grid") and "q_mvar" in net.res_ext_grid.columns else 0.0
            apparent_power_mva = (ext_grid_p_mw ** 2 + ext_grid_q_mvar ** 2) ** 0.5
            power_factor = ext_grid_p_mw / apparent_power_mva if apparent_power_mva > 0 else None

            voltage_violation_count = int(((net.res_bus["vm_pu"] < 0.95) | (net.res_bus["vm_pu"] > 1.05)).sum()) if not fast_mode and hasattr(net, "res_bus") and "vm_pu" in net.res_bus.columns else 0
            line_overload_count = int((net.res_line["loading_percent"] > 100.0).sum()) if hasattr(net, "res_line") and "loading_percent" in net.res_line.columns else 0
            trafo_overload_count = int((net.res_trafo["loading_percent"] > 100.0).sum()) if hasattr(net, "res_trafo") and "loading_percent" in net.res_trafo.columns else 0
            loss_percent_of_supply = (total_losses_mw / ext_grid_p_mw * 100.0) if ext_grid_p_mw > 0 else 0.0

        except Exception as e:
            converged = False
            min_voltage = None
            max_voltage = None
            max_trafo = None
            max_line = None
            line_losses_mw = None
            trafo_losses_mw = None
            total_losses_mw = None
            ext_grid_p_mw = None
            ext_grid_q_mvar = None
            power_factor = None
            voltage_violation_count = 0
            line_overload_count = 0
            trafo_overload_count = 0
            loss_percent_of_supply = None

        results.append({
            "timestep": row["timestep"],
            "delta_seconds": delta_seconds,
            "elapsed_seconds": elapsed_seconds,
            "elapsed_hours": elapsed_seconds / 3600.0,
            "total_power_mw": total_power_mw,
            "active_centers": active_centers,
            "min_voltage_pu": min_voltage,
            "max_voltage_pu": max_voltage,
            "max_transformer_loading_percent": max_trafo,
            "max_line_loading_percent": max_line,
            "converged": converged,
            "line_losses_mw": line_losses_mw,
            "transformer_losses_mw": trafo_losses_mw,
            "total_losses_mw": total_losses_mw,
            "loss_percent_of_supply": loss_percent_of_supply,
            "external_grid_p_mw": ext_grid_p_mw,
            "external_grid_q_mvar": ext_grid_q_mvar,
            "power_factor": power_factor,
            "voltage_violation_count": voltage_violation_count,
            "line_overload_count": line_overload_count,
            "transformer_overload_count": trafo_overload_count,
            "grid_backend": grid_backend,
            "simbench_code": simbench_code if grid_backend == "SimBench German benchmark grid" else "",
        })

    return pd.DataFrame(results)


def calculate_energy(results_df: pd.DataFrame) -> tuple:
    """Calculate total energy from results."""
    df = results_df.copy()
    df["delta_hours"] = df["delta_seconds"] / 3600.0
    df["energy_mwh"] = df["total_power_mw"] * df["delta_hours"]
    total_energy = df["energy_mwh"].sum()
    return df, total_energy
