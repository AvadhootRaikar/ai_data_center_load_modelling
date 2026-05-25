"""
Grid Model Module

Creates pandapower networks for HPC center power flow simulation.
Supports both synthetic HPC grid and SimBench German benchmark grids.
"""

from __future__ import annotations
import pandas as pd
import pandapower as pp


def create_german_hpc_grid(
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
):
    """
    Creates synthetic HPC center-level pandapower grid model.

    This is an assumption-based HPC connection model with German-like voltage 
    levels (110 kV / 20 kV / 0.4 kV), useful for controlled experiments.
    """
    net = pp.create_empty_network()

    bus_hv = pp.create_bus(net, vn_kv=110, name="Synthetic 110 kV Grid Connection")
    pp.create_ext_grid(net, bus=bus_hv, vm_pu=1.0, name="External Grid")

    center_load_map = {}

    for center_id in range(1, number_of_centers + 1):
        bus_center_hv = pp.create_bus(
            net,
            vn_kv=110,
            name=f"HPC Center {center_id} - 110 kV Connection Bus",
        )

        pp.create_line_from_parameters(
            net,
            from_bus=bus_hv,
            to_bus=bus_center_hv,
            length_km=5.0,
            r_ohm_per_km=0.06,
            x_ohm_per_km=0.30,
            c_nf_per_km=12.0,
            max_i_ka=0.8,
            name=f"HPC Center {center_id} - 110 kV Grid Line",
        )

        bus_center_mv = pp.create_bus(
            net,
            vn_kv=20,
            name=f"HPC Center {center_id} - 20 kV Campus Bus",
        )

        pp.create_transformer_from_parameters(
            net,
            hv_bus=bus_center_hv,
            lv_bus=bus_center_mv,
            sn_mva=63,
            vn_hv_kv=110,
            vn_lv_kv=20,
            vk_percent=12.0,
            vkr_percent=0.5,
            pfe_kw=25,
            i0_percent=0.1,
            name=f"HPC Center {center_id} - 110/20 kV Transformer",
        )

        center_load_map[center_id] = []

        for cluster_id in range(1, clusters_per_center + 1):
            bus_cluster_mv = pp.create_bus(
                net,
                vn_kv=20,
                name=f"HPC {center_id} Cluster {cluster_id} - 20 kV Feeder Bus",
            )

            pp.create_line_from_parameters(
                net,
                from_bus=bus_center_mv,
                to_bus=bus_cluster_mv,
                length_km=0.5,
                r_ohm_per_km=0.20,
                x_ohm_per_km=0.08,
                c_nf_per_km=200.0,
                max_i_ka=0.4,
                name=f"HPC {center_id} Cluster {cluster_id} - 20 kV Cable",
            )

            bus_cluster_lv = pp.create_bus(
                net,
                vn_kv=0.4,
                name=f"HPC {center_id} Cluster {cluster_id} - 0.4 kV Bus",
            )

            pp.create_transformer_from_parameters(
                net,
                hv_bus=bus_cluster_mv,
                lv_bus=bus_cluster_lv,
                sn_mva=2.5,
                vn_hv_kv=20,
                vn_lv_kv=0.4,
                vk_percent=6.0,
                vkr_percent=0.7,
                pfe_kw=3,
                i0_percent=0.2,
                name=f"HPC {center_id} Cluster {cluster_id} - 20/0.4 kV Transformer",
            )

            for rack_id in range(1, racks_per_cluster + 1):
                load_idx = pp.create_load(
                    net,
                    bus=bus_cluster_lv,
                    p_mw=0.0,
                    q_mvar=0.0,
                    name=f"HPC {center_id} / Cluster {cluster_id} / Rack {rack_id}",
                )
                center_load_map[center_id].append(load_idx)

    net["hpc_grid_backend"] = "Synthetic HPC grid"
    net["hpc_grid_description"] = (
        "Assumption-based 110/20/0.4 kV HPC connection model. "
        "Useful for controlled experiments."
    )
    return net, center_load_map


def _candidate_simbench_buses(net: pp.pandapowerNet, number_of_centers: int) -> list[int]:
    """Select buses suitable for HPC load injection from SimBench network."""
    buses = net.bus.copy()
    buses = buses[~buses.index.isin(net.ext_grid["bus"].tolist() if len(net.ext_grid) else [])]

    mv = buses[(buses["vn_kv"] >= 10.0) & (buses["vn_kv"] <= 30.0)]
    hv = buses[(buses["vn_kv"] > 30.0) & (buses["vn_kv"] <= 110.0)]
    lv = buses[(buses["vn_kv"] < 1.0)]

    ordered = list(mv.index) + list(hv.index) + list(lv.index) + list(buses.index)
    unique_ordered = []
    for bus in ordered:
        if bus not in unique_ordered:
            unique_ordered.append(int(bus))

    if not unique_ordered:
        raise ValueError("No suitable buses found in SimBench network.")

    if number_of_centers <= len(unique_ordered):
        positions = pd.Series(range(len(unique_ordered))).quantile(
            [i / max(number_of_centers - 1, 1) for i in range(number_of_centers)]
        ).round().astype(int).tolist()
        return [unique_ordered[pos] for pos in positions]

    return [unique_ordered[i % len(unique_ordered)] for i in range(number_of_centers)]


def create_simbench_hpc_grid(
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_loads: bool = True,
):
    """
    Creates pandapower network from SimBench and injects HPC centers as loads.
    """
    try:
        import simbench as sb
    except ImportError as exc:
        raise ImportError(
            "SimBench mode requires: pip install simbench"
        ) from exc

    net = sb.get_simbench_net(simbench_code)
    net["hpc_grid_backend"] = "SimBench German benchmark grid"
    net["hpc_simbench_code"] = simbench_code

    if not include_existing_loads and len(net.load):
        net.load.loc[:, "p_mw"] = 0.0
        if "q_mvar" in net.load.columns:
            net.load.loc[:, "q_mvar"] = 0.0

    selected_buses = _candidate_simbench_buses(net, number_of_centers)
    center_load_map = {}
    racks_per_center = max(1, clusters_per_center * racks_per_cluster)

    for center_id, grid_bus in enumerate(selected_buses, start=1):
        grid_bus = int(grid_bus)
        vn_kv = float(net.bus.at[grid_bus, "vn_kv"])

        hpc_bus = pp.create_bus(
            net,
            vn_kv=vn_kv,
            name=f"HPC Center {center_id} - connection bus ({vn_kv:g} kV)",
            type="b",
            zone="HPC",
        )

        pp.create_line_from_parameters(
            net,
            from_bus=grid_bus,
            to_bus=hpc_bus,
            length_km=0.2,
            r_ohm_per_km=0.12,
            x_ohm_per_km=0.10,
            c_nf_per_km=180.0,
            max_i_ka=0.80,
            name=f"HPC Center {center_id} connection",
        )

        center_load_map[center_id] = []
        for rack_id in range(1, racks_per_center + 1):
            load_idx = pp.create_load(
                net,
                bus=hpc_bus,
                p_mw=0.0,
                q_mvar=0.0,
                name=f"HPC Center {center_id} / Rack {rack_id}",
                type="HPC",
            )
            center_load_map[center_id].append(load_idx)

    return net, center_load_map


def create_hpc_grid(
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
    grid_backend: str = "Synthetic HPC grid",
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_simbench_loads: bool = True,
):
    """Factory function to select grid type."""
    if grid_backend == "SimBench German benchmark grid":
        return create_simbench_hpc_grid(
            number_of_centers=number_of_centers,
            clusters_per_center=clusters_per_center,
            racks_per_cluster=racks_per_cluster,
            simbench_code=simbench_code,
            include_existing_loads=include_existing_simbench_loads,
        )

    return create_german_hpc_grid(
        number_of_centers=number_of_centers,
        clusters_per_center=clusters_per_center,
        racks_per_cluster=racks_per_cluster,
    )
