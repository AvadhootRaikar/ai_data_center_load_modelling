from __future__ import annotations

import pandas as pd
import pandapower as pp


def create_german_hpc_grid(
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
):
    """
    Creates the original synthetic center-level pandapower grid model.

    This is intentionally kept as the baseline/custom grid so older scenarios remain
    reproducible. It is not a real German transmission grid; it is an assumption-based
    HPC connection model with German-like voltage levels (110 kV / 20 kV / 0.4 kV).
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
        "Original assumption-based 110/20/0.4 kV HPC connection model. "
        "Useful for controlled experiments, but not a German benchmark grid."
    )
    return net, center_load_map


def _candidate_simbench_buses(net: pp.pandapowerNet, number_of_centers: int) -> list[int]:
    """Select buses suitable for extra HPC load injection.

    Preference order:
    1. Medium-voltage buses (about 10-30 kV), usually suitable for industrial/HPC load stress tests.
    2. High-voltage buses if too few MV buses exist.
    3. Any bus as fallback.
    """
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
        raise ValueError("No suitable buses found in SimBench network for HPC load injection.")

    # Spread centers over the available candidate list instead of just taking adjacent buses.
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
    Creates a pandapower network from SimBench and injects HPC centers as additional loads.

    SimBench is a public German benchmark-grid dataset already integrated with pandapower
    via simbench.get_simbench_net(). This function keeps the SimBench topology, lines,
    transformers, base loads and generators, then adds controllable HPC rack loads.

    If include_existing_loads=False, non-HPC loads are set to zero so the dashboard can
    isolate the HPC impact on the SimBench topology.
    """
    try:
        import simbench as sb
    except ImportError as exc:
        raise ImportError(
            "SimBench mode requires the Python package 'simbench'. Install it with: pip install simbench"
        ) from exc

    net = sb.get_simbench_net(simbench_code)
    net["hpc_grid_backend"] = "SimBench German benchmark grid"
    net["hpc_simbench_code"] = simbench_code
    net["hpc_grid_description"] = (
        f"SimBench network {simbench_code}. HPC centers are added as extra controllable loads "
        "through explicit named HPC connection buses attached to selected MV/HV/LV buses. Existing SimBench load/generation data can be kept or disabled."
    )

    if not include_existing_loads and len(net.load):
        net.load.loc[:, "p_mw"] = 0.0
        if "q_mvar" in net.load.columns:
            net.load.loc[:, "q_mvar"] = 0.0

    selected_buses = _candidate_simbench_buses(net, number_of_centers)
    center_load_map = {}
    center_connection_map = {}
    racks_per_center = max(1, clusters_per_center * racks_per_cluster)

    for center_id, grid_bus in enumerate(selected_buses, start=1):
        grid_bus = int(grid_bus)
        vn_kv = float(net.bus.at[grid_bus, "vn_kv"])

        # Explicit HPC connection bus:
        # This makes each HPC center visible in the pandapower topology. The
        # controllable rack loads are still ordinary net.load elements, but
        # they are attached to a named HPC bus instead of being hidden directly
        # on a SimBench grid bus.
        hpc_bus = pp.create_bus(
            net,
            vn_kv=vn_kv,
            name=f"HPC Center {center_id} - connection bus ({vn_kv:g} kV)",
            type="b",
            zone="HPC",
        )

        # Short generic service connection from SimBench grid bus to HPC center.
        # It is a visible electrical branch in net.line / net.res_line. For a
        # real site study, replace these generic parameters with operator data.
        if vn_kv < 1.0:
            r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka = 0.25, 0.08, 200.0, 0.60
            length_km = 0.05
        elif vn_kv <= 30.0:
            r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka = 0.12, 0.10, 180.0, 0.80
            length_km = 0.20
        else:
            r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka = 0.06, 0.30, 12.0, 0.80
            length_km = 1.00

        service_line = pp.create_line_from_parameters(
            net,
            from_bus=grid_bus,
            to_bus=hpc_bus,
            length_km=length_km,
            r_ohm_per_km=r_ohm_per_km,
            x_ohm_per_km=x_ohm_per_km,
            c_nf_per_km=c_nf_per_km,
            max_i_ka=max_i_ka,
            name=f"HPC Center {center_id} service connection to SimBench bus {grid_bus}",
        )

        center_connection_map[center_id] = {
            "grid_bus": grid_bus,
            "hpc_bus": int(hpc_bus),
            "service_line": int(service_line),
            "vn_kv": vn_kv,
        }

        center_load_map[center_id] = []
        for rack_id in range(1, racks_per_center + 1):
            load_idx = pp.create_load(
                net,
                bus=hpc_bus,
                p_mw=0.0,
                q_mvar=0.0,
                name=f"HPC Center {center_id} / Rack {rack_id} (HPC bus {hpc_bus}, SimBench bus {grid_bus})",
                type="HPC",
            )
            center_load_map[center_id].append(load_idx)

    net["hpc_center_connection_map"] = center_connection_map
    return net, center_load_map


def create_hpc_grid(
    number_of_centers: int,
    clusters_per_center: int = 4,
    racks_per_cluster: int = 10,
    grid_backend: str = "Synthetic HPC grid",
    simbench_code: str = "1-MV-rural--0-sw",
    include_existing_simbench_loads: bool = True,
):
    """Factory used by simulation and dashboard snapshot code."""
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
