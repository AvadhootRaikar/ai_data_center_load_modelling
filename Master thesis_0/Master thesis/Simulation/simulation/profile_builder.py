from pathlib import Path
import math
import pandas as pd


def load_and_prepare(file_path: str | Path) -> pd.DataFrame:
    """
    Loads one MLPerf CSV and prepares it for profile generation.

    Required:
    - timestamp
    - total_gpu_power_w

    Optional but used when available:
    - gpu_util_percent
    - gpu_power_w
    - cpu_util_percent
    - num_gpus
    - epoch / step / note
    """
    df = pd.read_csv(file_path)

    required_columns = ["timestamp", "total_gpu_power_w"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"{file_path} is missing columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S", errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError(f"{file_path} contains invalid timestamp values")

    df = df.sort_values("timestamp").reset_index(drop=True)

    df["delta_seconds"] = df["timestamp"].diff().dt.total_seconds()
    median_delta = df["delta_seconds"].dropna().median()
    if pd.isna(median_delta) or median_delta <= 0:
        median_delta = 5.0

    df["delta_seconds"] = df["delta_seconds"].fillna(median_delta)
    df.loc[df["delta_seconds"] <= 0, "delta_seconds"] = median_delta
    df.loc[df["delta_seconds"] > 300, "delta_seconds"] = median_delta

    df["elapsed_seconds"] = df["delta_seconds"].cumsum()
    df["elapsed_hours"] = df["elapsed_seconds"] / 3600.0

    for col in ["gpu_util_percent", "gpu_power_w", "total_gpu_power_w", "cpu_util_percent", "num_gpus", "epoch", "step"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def align_and_trim(dfs: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """Makes all runs the same length by cutting to the shortest run."""
    min_len = min(len(df) for df in dfs)
    return [df.iloc[:min_len].copy() for df in dfs]


def _average_optional_column(dfs: list[pd.DataFrame], column: str) -> pd.Series | None:
    available = [df[column].to_numpy() for df in dfs if column in df.columns]
    if not available:
        return None
    return pd.DataFrame(available).mean(axis=0)


def build_measured_profile(folder_path: str | Path, workload_label: str = "Training") -> pd.DataFrame:
    """
    Builds one averaged measured workload profile from multiple MLPerf CSV runs.

    The function is generic: it works for training and inference CSVs as long as
    the files contain timestamp and total_gpu_power_w.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Workload folder not found: {folder}")

    files = sorted(folder.glob("*.csv"))
    if len(files) == 0:
        raise ValueError(f"No CSV files found in: {folder}")
    if len(files) < 2:
        raise ValueError("At least 2 CSV files are recommended for representative averaging.")

    dfs = [load_and_prepare(file) for file in files]
    dfs = align_and_trim(dfs)

    total_power_matrix = pd.DataFrame([df["total_gpu_power_w"].to_numpy() for df in dfs])
    delta_matrix = pd.DataFrame([df["delta_seconds"].to_numpy() for df in dfs])

    avg_total_gpu_power = total_power_matrix.mean(axis=0)
    std_total_gpu_power = total_power_matrix.std(axis=0)
    avg_delta_seconds = delta_matrix.mean(axis=0)

    profile = pd.DataFrame(
        {
            "timestep": range(len(avg_total_gpu_power)),
            "delta_seconds": avg_delta_seconds,
            "delta_hours": avg_delta_seconds / 3600.0,
            "gpu_power_w": avg_total_gpu_power,
            "total_gpu_power_w": avg_total_gpu_power,
            "gpu_power_std": std_total_gpu_power,
        }
    )

    avg_gpu_power = _average_optional_column(dfs, "gpu_power_w")
    avg_gpu_util = _average_optional_column(dfs, "gpu_util_percent")
    avg_cpu_util = _average_optional_column(dfs, "cpu_util_percent")
    avg_num_gpus = _average_optional_column(dfs, "num_gpus")

    if avg_gpu_power is not None:
        profile["single_gpu_power_w"] = avg_gpu_power
    if avg_gpu_util is not None:
        profile["gpu_util_percent"] = avg_gpu_util.clip(lower=0, upper=100)
    else:
        peak = float(profile["total_gpu_power_w"].max())
        profile["gpu_util_percent"] = (profile["total_gpu_power_w"] / peak * 100.0).clip(lower=0, upper=100) if peak > 0 else 100.0
    if avg_cpu_util is not None:
        profile["cpu_util_percent"] = avg_cpu_util.clip(lower=0, upper=100)
    if avg_num_gpus is not None:
        profile["num_gpus"] = avg_num_gpus

    profile["elapsed_seconds"] = profile["delta_seconds"].cumsum()
    profile["elapsed_hours"] = profile["elapsed_seconds"] / 3600.0
    profile["workload_label"] = workload_label
    profile["source_folder"] = str(folder)

    return profile


def _repeat_profile_to_length(profile: pd.DataFrame, target_len: int, target_delta_seconds: pd.Series) -> pd.DataFrame:
    """Repeats a shorter trace pattern to match another trace length."""
    if len(profile) == target_len:
        out = profile.copy().reset_index(drop=True)
    else:
        repeats = int(math.ceil(target_len / len(profile)))
        out = pd.concat([profile] * repeats, ignore_index=True).iloc[:target_len].copy()

    out["timestep"] = range(target_len)
    out["delta_seconds"] = target_delta_seconds.to_numpy()
    out["delta_hours"] = out["delta_seconds"] / 3600.0
    out["elapsed_seconds"] = out["delta_seconds"].cumsum()
    out["elapsed_hours"] = out["elapsed_seconds"] / 3600.0
    return out


def build_selected_workload_profile(
    training_folder: str | Path,
    inference_folder: str | Path,
    workload_mode: str = "Training Run",
) -> pd.DataFrame:
    """
    Builds the representative workload profile selected in the dashboard.

    Modes:
    - Training Run: averaged training MLPerf trace.
    - Inference Run: averaged inference trace.
    - Simultaneous Training + Inference: training trace plus a repeated inference
      pattern, aligned to the training timeline. This models concurrent inference
      traffic running while training is active.
    """
    training = build_measured_profile(training_folder, workload_label="Training")

    if workload_mode == "Training Run":
        training["workload_mode"] = workload_mode
        return training

    inference = build_measured_profile(inference_folder, workload_label="Inference")

    if workload_mode == "Inference Run":
        inference["workload_mode"] = workload_mode
        return inference

    if workload_mode == "Simultaneous Training + Inference":
        aligned_inference = _repeat_profile_to_length(
            inference,
            target_len=len(training),
            target_delta_seconds=training["delta_seconds"],
        )

        combined = training.copy().reset_index(drop=True)
        combined["training_total_gpu_power_w"] = training["total_gpu_power_w"].to_numpy()
        combined["inference_total_gpu_power_w"] = aligned_inference["total_gpu_power_w"].to_numpy()
        combined["training_gpu_util_percent"] = training["gpu_util_percent"].to_numpy()
        combined["inference_gpu_util_percent"] = aligned_inference["gpu_util_percent"].to_numpy()

        combined["total_gpu_power_w"] = combined["training_total_gpu_power_w"] + combined["inference_total_gpu_power_w"]
        combined["gpu_power_w"] = combined["total_gpu_power_w"]
        combined["gpu_power_std"] = (training.get("gpu_power_std", 0).to_numpy() if "gpu_power_std" in training else 0)
        combined["gpu_util_percent"] = combined[["training_gpu_util_percent", "inference_gpu_util_percent"]].max(axis=1).clip(0, 100)
        combined["workload_label"] = "Training + Inference"
        combined["workload_mode"] = workload_mode
        combined["inference_pattern_repeated"] = True
        return combined

    raise ValueError(f"Unknown workload_mode: {workload_mode}")


def build_training_profile(folder_path: str | Path) -> pd.DataFrame:
    """Backward-compatible wrapper used by older app versions."""
    return build_measured_profile(folder_path, workload_label="Training")
