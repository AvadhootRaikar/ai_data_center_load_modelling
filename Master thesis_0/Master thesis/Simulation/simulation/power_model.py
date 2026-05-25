import pandas as pd


def convert_training_profile_to_center(
    profile_df: pd.DataFrame,
    nodes_per_center: int,
    cpu_power_per_node: float = 150.0,
    ram_power_per_node: float = 40.0,
    storage_power_per_node: float = 10.0,
    network_power_per_node: float = 10.0,
    pue: float = 1.3,
) -> pd.DataFrame:
    """
    Converts averaged GPU training profile into full HPC center power demand.

    Important columns:
    - center_it_power_w: useful IT workload power only
    - center_overhead_power_w: cooling/infrastructure overhead from PUE
    - center_total_power_w: IT + overhead

    The Improved Cooling scenario uses these columns to reduce only overhead,
    not the ML/IT workload itself.
    """

    df = profile_df.copy()

    df["node_power_w"] = (
        df["gpu_power_w"]
        + cpu_power_per_node
        + ram_power_per_node
        + storage_power_per_node
        + network_power_per_node
    )

    df["center_it_power_w"] = df["node_power_w"] * nodes_per_center
    df["baseline_pue"] = float(pue)

    df["center_total_power_w"] = df["center_it_power_w"] * pue
    df["center_overhead_power_w"] = df["center_total_power_w"] - df["center_it_power_w"]
    df["center_total_power_mw"] = df["center_total_power_w"] / 1_000_000

    return df
