import os
import sys
import warnings
# Suppress pandapower numba warning spam
warnings.filterwarnings("ignore", category=UserWarning, message="numba cannot be imported")

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional


# Add parent directory of simulation to sys.path so we can import it
sys.path.insert(0, str(Path(__file__).parent))

from simulation.profile_builder import load_and_prepare, build_measured_profile
from simulation.power_model import convert_training_profile_to_center
from simulation.optimization_scenarios import apply_optimization_scenario, apply_center_level_load_balancing
from simulation.run_simulation import run_hpc_simulation, calculate_energy
from simulation.cost_model import build_tou_price_table, calculate_time_of_day_costs
from simulation.ui_and_simulation_improvements import (
    load_grid_pricing_data, get_auto_pricing_for_hour,
    calculate_workload_cost_by_time, calculate_workload_carbon_by_time,
    calculate_grid_stability_impact, apply_realistic_pue_profile
)

app = FastAPI(title="HPC Energy Simulation API", version="2.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data"
TRAINING_DIR = DATA_DIR / "raw_runs" / "training"
INFERENCE_DIR = DATA_DIR / "raw_runs" / "inference"

class SimulationRequest(BaseModel):
    workload_mode: str = "Training Run"
    training_file: str = "train_run_1.csv"
    inference_file: str = "inference_run_1.csv"
    target_pue: float = 1.25
    optimization_goal: str = "Minimize Cost"
    enable_gpu_limiting: bool = False
    enable_cooling_upgrade: bool = False
    enable_smart_scheduling: bool = False
    enable_load_balancing: bool = False
    number_of_centers: int = 3
    nodes_per_center: int = 64
    grid_backend: str = "Synthetic HPC grid"
    fast_mode: bool = True
    expansion_mode: bool = False
    transformer_headroom: float = 1.2

@app.get("/api/config-options")
def get_config_options():
    """Returns the list of available workload files for training and inference."""
    try:
        training_files = sorted([f.name for f in TRAINING_DIR.glob("*.csv")]) if TRAINING_DIR.exists() else []
        inference_files = sorted([f.name for f in INFERENCE_DIR.glob("*.csv")]) if INFERENCE_DIR.exists() else []
        return {
            "training_files": training_files,
            "inference_files": inference_files,
            "default_pue": 1.25,
            "default_centers": 3,
            "default_nodes": 64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan workload traces: {str(e)}")

def get_workload_profile(workload_mode: str, training_file: str, inference_file: str) -> pd.DataFrame:
    """Builds or loads the selected workload profile."""
    # Build training profile
    if workload_mode == "Training Run" or workload_mode == "Simultaneous Training + Inference":
        if training_file and training_file != "all":
            file_path = TRAINING_DIR / training_file
            if not file_path.exists():
                raise FileNotFoundError(f"Training file not found: {training_file}")
            df = load_and_prepare(file_path)
            df["timestep"] = range(len(df))
            df["gpu_power_std"] = 0.0
            if "gpu_power_w" not in df.columns:
                df["gpu_power_w"] = df["total_gpu_power_w"]
            if "single_gpu_power_w" not in df.columns:
                df["single_gpu_power_w"] = df["gpu_power_w"]
            df["workload_label"] = "Training"
            df["source_folder"] = str(TRAINING_DIR)
            training_profile = df
        else:
            training_profile = build_measured_profile(TRAINING_DIR, workload_label="Training")

    # Build inference profile
    if workload_mode == "Inference Run" or workload_mode == "Simultaneous Training + Inference":
        if inference_file and inference_file != "all":
            file_path = INFERENCE_DIR / inference_file
            if not file_path.exists():
                raise FileNotFoundError(f"Inference file not found: {inference_file}")
            df = load_and_prepare(file_path)
            df["timestep"] = range(len(df))
            df["gpu_power_std"] = 0.0
            if "gpu_power_w" not in df.columns:
                df["gpu_power_w"] = df["total_gpu_power_w"]
            if "single_gpu_power_w" not in df.columns:
                df["single_gpu_power_w"] = df["gpu_power_w"]
            df["workload_label"] = "Inference"
            df["source_folder"] = str(INFERENCE_DIR)
            inference_profile = df
        else:
            inference_profile = build_measured_profile(INFERENCE_DIR, workload_label="Inference")

    if workload_mode == "Training Run":
        training_profile["workload_mode"] = workload_mode
        return training_profile
    elif workload_mode == "Inference Run":
        inference_profile["workload_mode"] = workload_mode
        return inference_profile
    elif workload_mode == "Simultaneous Training + Inference":
        from simulation.profile_builder import _repeat_profile_to_length
        aligned_inference = _repeat_profile_to_length(
            inference_profile,
            target_len=len(training_profile),
            target_delta_seconds=training_profile["delta_seconds"],
        )

        combined = training_profile.copy().reset_index(drop=True)
        combined["training_total_gpu_power_w"] = training_profile["total_gpu_power_w"].to_numpy()
        combined["inference_total_gpu_power_w"] = aligned_inference["total_gpu_power_w"].to_numpy()
        combined["training_gpu_util_percent"] = training_profile["gpu_util_percent"].to_numpy()
        combined["inference_gpu_util_percent"] = aligned_inference["gpu_util_percent"].to_numpy()

        combined["total_gpu_power_w"] = combined["training_total_gpu_power_w"] + combined["inference_total_gpu_power_w"]
        combined["gpu_power_w"] = combined["total_gpu_power_w"]
        combined["gpu_power_std"] = training_profile.get("gpu_power_std", 0).to_numpy() if "gpu_power_std" in training_profile else 0
        combined["gpu_util_percent"] = combined[["training_gpu_util_percent", "inference_gpu_util_percent"]].max(axis=1).clip(0, 100)
        combined["workload_label"] = "Training + Inference"
        combined["workload_mode"] = workload_mode
        combined["inference_pattern_repeated"] = True
        return combined

    raise ValueError(f"Unknown workload mode: {workload_mode}")

@app.post("/api/simulate")
def run_simulation_endpoint(req: SimulationRequest):
    """Executes the simulation pipeline based on the request configuration."""
    try:
        # 1. Load Workload Profile
        try:
            profile = get_workload_profile(req.workload_mode, req.training_file, req.inference_file)
        except FileNotFoundError as fnf:
            raise HTTPException(status_code=404, detail=str(fnf))

        # Load grid pricing mappings
        pricing_map, carbon_map, grid_df = load_grid_pricing_data()
        
        # 2. Build Baseline Profile & Facility Conversion
        baseline_profile = convert_training_profile_to_center(
            profile,
            nodes_per_center=req.nodes_per_center,
            pue=1.3,  # Baseline standard
            dynamic_cpu_power=True,
            dynamic_memory_power=True
        )
        
        # 3. Apply Optimizations to Current Profile
        # A. GPU Capping (Cap GPU power by 20% if enabled)
        gpu_power_factor = 0.80 if req.enable_gpu_limiting else 1.0
        optimized_profile = apply_optimization_scenario(
            profile,
            scenario="custom",
            gpu_power_factor=gpu_power_factor
        )

        # B. Cooling Upgrade (PUE reduction)
        current_pue = req.target_pue
        if req.enable_cooling_upgrade:
            current_pue = max(1.10, current_pue - 0.15)  # upgrade reduces PUE by 0.15, floor at 1.10

        # C. Load Balancing (Scale total node power across centers if active)
        if req.enable_load_balancing:
            optimized_profile = apply_center_level_load_balancing(
                optimized_profile,
                number_of_centers=req.number_of_centers,
                max_active_centers=max(1, req.number_of_centers - 1)
            )

        # Convert optimized profile to center facility level
        current_facility_profile = convert_training_profile_to_center(
            optimized_profile,
            nodes_per_center=req.nodes_per_center,
            pue=current_pue,
            dynamic_cpu_power=True,
            dynamic_memory_power=True
        )

        # D. Smart Scheduling (Time of day pricing shift)
        # Standard runs start at 12:00 (midday). Smart Scheduling shifts start to greenest/cheapest hours
        start_hour = 12.0
        if req.enable_smart_scheduling:
            if req.optimization_goal == "Minimize Cost":
                start_hour = 0.0  # Night off-peak (Cheapest)
            elif req.optimization_goal == "Minimize Carbon":
                start_hour = 12.0 # Midday (Highest Solar)
            else:
                start_hour = 0.0  # Default balanced to night

        # 4. Run Pandapower Grid Flow Simulation
        # Baseline Grid Simulation
        baseline_grid_df = run_hpc_simulation(
            baseline_profile,
            number_of_centers=req.number_of_centers,
            fast_mode=req.fast_mode,
            grid_backend=req.grid_backend,
            transformer_headroom=req.transformer_headroom
        )
        
        # Optimized Grid Simulation
        optimized_grid_df = run_hpc_simulation(
            current_facility_profile,
            number_of_centers=req.number_of_centers,
            fast_mode=req.fast_mode,
            grid_backend=req.grid_backend,
            transformer_headroom=req.transformer_headroom
        )

        # 5. Integrate Energy, Cost and Carbon
        baseline_grid_with_energy, baseline_energy_mwh = calculate_energy(baseline_grid_df)
        optimized_grid_with_energy, current_energy_mwh = calculate_energy(optimized_grid_df)
        
        # Calculate Costs (German Grid Tariff)
        price_table = build_tou_price_table()
        _, baseline_cost_eur = calculate_time_of_day_costs(
            baseline_grid_with_energy,
            price_table,
            simulation_start_hour=12.0 # Baseline always starts at midday
        )
        
        _, current_cost_eur = calculate_time_of_day_costs(
            optimized_grid_with_energy,
            price_table,
            simulation_start_hour=start_hour
        )

        # Calculate Carbon (Integrated SMARD carbon profile)
        # integrated carbon intensity calculation
        baseline_carbon_kg = 0.0
        current_carbon_kg = 0.0
        
        # Integrate carbon over timesteps
        for _, row in baseline_grid_with_energy.iterrows():
            hour = int((12.0 + row["elapsed_hours"]) % 24)
            period_data = get_auto_pricing_for_hour(hour, pricing_map)
            carbon_g = period_data["carbon_gco2_kwh"]
            # Energy in MWh * 1000 = kWh. Carbon in gCO2 / 1000 = kgCO2
            # Net: MWh * carbon_g = kgCO2
            step_energy_mwh = row["total_power_mw"] * (row["delta_seconds"] / 3600.0)
            baseline_carbon_kg += step_energy_mwh * carbon_g

        for _, row in optimized_grid_with_energy.iterrows():
            hour = int((start_hour + row["elapsed_hours"]) % 24)
            period_data = get_auto_pricing_for_hour(hour, pricing_map)
            carbon_g = period_data["carbon_gco2_kwh"]
            step_energy_mwh = row["total_power_mw"] * (row["delta_seconds"] / 3600.0)
            current_carbon_kg += step_energy_mwh * carbon_g

        # Scaling savings
        energy_saved_pct = ((baseline_energy_mwh - current_energy_mwh) / baseline_energy_mwh * 100.0) if baseline_energy_mwh > 0 else 0
        cost_saved_pct = ((baseline_cost_eur - current_cost_eur) / baseline_cost_eur * 100.0) if baseline_cost_eur > 0 else 0
        carbon_saved_pct = ((baseline_carbon_kg - current_carbon_kg) / baseline_carbon_kg * 100.0) if baseline_carbon_kg > 0 else 0
        
        # Annual Projections (Assuming 1 run per day)
        annual_energy_saved_mwh = (baseline_energy_mwh - current_energy_mwh) * 365
        annual_cost_saved_eur = (baseline_cost_eur - current_cost_eur) * 365
        annual_carbon_saved_tons = (baseline_carbon_kg - current_carbon_kg) * 365 / 1000.0

        # Weighted avg power and peak power
        weighted_avg_power_mw = current_facility_profile["center_total_power_mw"].mean() * req.number_of_centers
        peak_power_mw = current_facility_profile["center_total_power_mw"].max() * req.number_of_centers

        # 6. Build Projections Table
        # Baseline vs historical/simulation components
        # Components: IT Compute, Cooling, Power distribution losses (3%), UPS Parasitic (1.5%), Aux (0.8%)
        total_it_mwh = (current_facility_profile["center_it_power_w"].sum() / 1_000_000) * (profile["delta_seconds"].mean() / 3600.0) * req.number_of_centers
        total_cooling_mwh = (current_facility_profile["center_overhead_power_w"].sum() / 1_000_000) * (profile["delta_seconds"].mean() / 3600.0) * req.number_of_centers
        total_losses_mwh = total_it_mwh * 0.03
        total_ups_mwh = total_it_mwh * 0.015
        total_aux_mwh = total_it_mwh * 0.008

        # Reference Historical (mocked slightly above baseline)
        hist_it = total_it_mwh * 1.05
        hist_cooling = total_cooling_mwh * 1.25 if not req.enable_cooling_upgrade else total_cooling_mwh * 0.90
        hist_losses = total_losses_mwh * 1.08
        hist_ups = total_ups_mwh * 1.30
        hist_aux = total_aux_mwh * 0.95

        def make_row(label, est, hist):
            dev = ((est - hist) / hist * 100.0) if hist > 0 else 0
            status = "PASS" if abs(dev) < 15 else ("WARN" if abs(dev) < 25 else "FAIL")
            return {
                "category": label,
                "estimated": f"{est:.2f} MWh",
                "historical": f"{hist:.2f} MWh",
                "deviation": f"{dev:+.1f}%",
                "status": status,
                "statusType": status.lower()
            }

        projections_table = [
            make_row("IT Load (Compute)", total_it_mwh, hist_it),
            make_row("Cooling System (Chilled Water)", total_cooling_mwh, hist_cooling),
            make_row("Power Distribution Losses", total_losses_mwh, hist_losses),
            make_row("UPS Parasitic Load", total_ups_mwh, hist_ups),
            make_row("Lighting & Auxiliary", total_aux_mwh, hist_aux)
        ]

        # 7. Grid Health & Security Checks
        grid_capacity = 30.0 if req.expansion_mode else 20.0
        grid_stability = calculate_grid_stability_impact(optimized_grid_df, grid_capacity_mw=grid_capacity) # synthetic capacity
        
        # Security Checks: N-1 contingency loading
        # Mock load flow contingency profiles based on actual transformer loading
        max_loading = float(optimized_grid_df["max_transformer_loading_percent"].max())
        scale_factor = 0.75 if req.expansion_mode else 1.0
        pre_fault_trafo = max_loading * 0.5 * scale_factor
        post_fault_trafo = max_loading * 0.9 * scale_factor
        
        def make_security_row(element, type_str, metric, pre, post):
            margin = 100.0 - post
            status = "PASS" if post < 80 else ("WARN" if post < 95 else "FAIL")
            return {
                "element": element,
                "type": type_str,
                "metric": metric,
                "preFault": f"{pre:.1f}%",
                "postFault": f"{post:.1f}%",
                "margin": f"{margin:.1f}%",
                "status": status
            }

        security_checks = [
            make_security_row("Trafo HV/MV", "110→20 kV Transformer", "Loading", pre_fault_trafo, post_fault_trafo),
            make_security_row("Line MV-01", "20 kV Cable", "Loading", pre_fault_trafo * 0.8, post_fault_trafo * 0.85),
            make_security_row("Line MV-02", "20 kV Cable", "Loading", pre_fault_trafo * 0.7, post_fault_trafo * 1.10),
            make_security_row("Trafo MV/LV-1", "20→0.4 kV Transformer", "Loading", pre_fault_trafo * 1.1, post_fault_trafo * 1.15),
            make_security_row("External Grid", "Grid Connection", "Voltage", 100.0, 97.0),
        ]

        # Solver load simulation
        solver_load = 76 if not req.fast_mode else 12

        # 8. Time Series Data for SVG Charts
        # Draw 12 steps for demand chart overlay (every 2 hours across a 24h cycle)
        hours_24 = [h for h in range(0, 25, 2)]
        
        baseline_mw_series = []
        optimized_mw_series = []
        price_series = []
        carbon_series = []
        
        for h in hours_24:
            # Map hours to grid profiles
            period_data = get_auto_pricing_for_hour(h % 24, pricing_map)
            price_series.append(period_data["price_eur_mwh"])
            carbon_series.append(period_data["carbon_gco2_kwh"])
            
            # Map baseline power demand based on trace index
            idx_base = int((h / 24.0) * (len(baseline_profile) - 1))
            baseline_mw_series.append(float(baseline_profile["center_total_power_mw"].iloc[idx_base]) * req.number_of_centers)
            
            # Map optimized power demand based on trace index and scheduling start hour
            h_shifted = (h + int(start_hour - 12.0)) % 24
            idx_shifted = int((h_shifted / 24.0) * (len(current_facility_profile) - 1))
            optimized_mw_series.append(float(current_facility_profile["center_total_power_mw"].iloc[idx_shifted]) * req.number_of_centers)

        # Cumulative Savings Chart (over 24 timesteps)
        savings_series = []
        cum_savings = 0.0
        for h in range(24):
            period_data = get_auto_pricing_for_hour(h, pricing_map)
            rate = period_data["price_eur_mwh"]
            
            # Savings = (Baseline MW - Optimized MW) * 1 hour * rate
            base_p = float(baseline_profile["center_total_power_mw"].mean()) * req.number_of_centers
            opt_p = float(current_facility_profile["center_total_power_mw"].mean()) * req.number_of_centers
            
            # Smart scheduling cost savings
            base_period_data = get_auto_pricing_for_hour((h + 12) % 24, pricing_map)
            opt_period_data = get_auto_pricing_for_hour((h + int(start_hour)) % 24, pricing_map)
            
            hour_base_cost = base_p * base_period_data["price_eur_mwh"]
            hour_opt_cost = opt_p * opt_period_data["price_eur_mwh"]
            
            cum_savings += max(0, hour_base_cost - hour_opt_cost)
            savings_series.append(cum_savings)

        # 9. Simulation Results Detail (First 20 steps to show in the table)
        results_table = []
        for i, row in optimized_grid_df.head(20).iterrows():
            ts = profile["timestamp"].iloc[i] if "timestamp" in profile.columns else "00:00:00"
            if isinstance(ts, pd.Timestamp):
                ts_str = ts.strftime("%H:%M:%S")
            else:
                ts_str = str(ts)
                
            results_table.append({
                "timestep": int(row["timestep"]),
                "time": ts_str,
                "power": f"{row['total_power_mw']:.4f} MW",
                "voltage": f"{row['min_voltage_pu']:.3f} p.u." if row['min_voltage_pu'] is not None else "1.000 p.u.",
                "loading": f"{row['max_transformer_loading_percent']:.1f}%",
                "status": "PASS" if row["converged"] else "FAIL"
            })

        return {
            "metrics": {
                "baseline_energy": round(baseline_energy_mwh, 4),
                "current_energy": round(current_energy_mwh, 4),
                "energy_change_pct": round(energy_saved_pct, 1),
                "baseline_cost": round(baseline_cost_eur, 2),
                "current_cost": round(current_cost_eur, 2),
                "cost_change_pct": round(cost_saved_pct, 1),
                "baseline_carbon": round(baseline_carbon_kg, 0),
                "current_carbon": round(current_carbon_kg, 0),
                "carbon_change_pct": round(carbon_saved_pct, 1),
                "weighted_avg_power": round(weighted_avg_power_mw, 4),
                "peak_power": round(peak_power_mw, 4),
                "annual_energy_saved": round(annual_energy_saved_mwh, 1),
                "annual_cost_saved": round(annual_cost_saved_eur, 2),
                "annual_carbon_saved": round(annual_carbon_saved_tons, 1)
            },
            "projections_table": projections_table,
            "grid_health": {
                "voltage_stability": 99.2 if optimized_grid_df["converged"].all() else round(float(optimized_grid_df["converged"].sum() / len(optimized_grid_df) * 100), 1),
                "harmonic_distortion": round(2.1 + (peak_power_mw / 20.0), 2),
                "transformer_load": round(max_loading, 1),
                "solver_load": solver_load,
                "stability_status": "Healthy - Adequate Grid Capacity" if max_loading < 70 else ("Warning - Moderate Grid Stress" if max_loading < 90 else "Critical - High Grid Stress"),
                "recommended_shift": grid_stability["recommended_shift"],
                "insight_message": f"The current scenario shows a {cost_saved_pct:.1f}% economic reduction compared to the baseline trace, primarily driven by target PUE constraints ({current_pue}) and smart workload shift to {start_hour:02.0f}:00 pricing windows."
            },
            "demand_chart": {
                "hours": hours_24,
                "baseline_mw": baseline_mw_series,
                "optimized_mw": optimized_mw_series,
                "price_eur_mwh": price_series,
                "carbon_intensity_g": carbon_series
            },
            "cumulative_savings": {
                "hours": list(range(24)),
                "savings_eur": savings_series
            },
            "security_checks": security_checks,
            "simulation_results_table": results_table
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Simulation runner error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
