"""
Scenario Comparison Analysis

Compares multiple optimization scenarios against the validated baseline:
- Scenario 1: GPU Power Limiting (reduce GPU power consumption)
- Scenario 2: PUE Improvements (reduce Power Usage Effectiveness)
- Scenario 3: Workload Shifting (schedule work at different times)

Each scenario is compared on:
- Total energy consumption (MWh)
- Peak power demand (MW)
- Operational costs (EUR)
- Carbon emissions (kg CO2e)

Run from project root: python scenario_comparisons.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation import (
    profile_builder, power_model, run_simulation, 
    energy_projection, cost_model, carbon_model
)

# ============================================================================
# CONFIGURATION
# ============================================================================

THESIS_DATA_ROOT = Path(__file__).parent.parent / "Master thesis_0" / "Master thesis" / "Simulation"
TRAINING_FOLDER = THESIS_DATA_ROOT / "data" / "raw_runs" / "training"

NODES_PER_CENTER = 20
NUMBER_OF_CENTERS = 3

OUTPUT_DIR = Path(__file__).parent / "outputs" / "scenarios"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_section(title):
    """Print formatted subsection."""
    print(f"\n[{title}]")
    print("-"*80)

def print_scenario(name, description):
    """Print scenario title."""
    print(f"\n  {name}")
    print(f"  {description}")

# ============================================================================
# BASELINE CALCULATION
# ============================================================================

def calculate_baseline():
    """Load and calculate baseline metrics."""
    print_section("LOADING BASELINE CONFIGURATION")
    
    # Load training profile
    profile = profile_builder.build_measured_profile(
        TRAINING_FOLDER,
        workload_label="Training"
    )
    print(f"  Training profile loaded: {len(profile)} samples")
    
    # Convert to facility power
    facility_profile = power_model.convert_training_profile_to_center(
        profile,
        nodes_per_center=NODES_PER_CENTER,
        dynamic_cpu_power=True,
        dynamic_memory_power=True,
    )
    print(f"  Baseline PUE: {facility_profile['baseline_pue'].iloc[0]:.2f}")
    print(f"  Baseline peak GPU power: {profile['gpu_power_w'].max():.1f} W")
    
    # Run simulation
    results = run_simulation.run_hpc_simulation(
        facility_profile,
        number_of_centers=NUMBER_OF_CENTERS,
        grid_backend="Synthetic HPC grid",
    )
    print(f"  Simulation: {len(results)} timesteps")
    
    # Calculate energy and costs
    results_final, total_energy = run_simulation.calculate_energy(results)
    
    price_table = cost_model.build_tou_price_table()
    cost_results, total_cost = cost_model.calculate_time_of_day_costs(
        results_final,
        price_table,
        simulation_start_hour=12.0
    )
    
    # Calculate carbon
    carbon_profile = carbon_model.build_german_carbon_intensity_profile()
    carbon_results, total_carbon = carbon_model.calculate_carbon_emissions(
        results_final,
        carbon_profile,
        simulation_start_hour=12.0
    )
    
    metrics = {
        'energy_mwh': total_energy,
        'peak_power_mw': results_final['total_power_mw'].max(),
        'avg_power_mw': results_final['total_power_mw'].mean(),
        'total_cost_eur': total_cost,
        'total_carbon_kg': total_carbon,
        'convergence_rate': (results_final['converged'].sum() / len(results_final)) * 100,
    }
    
    print(f"  Energy: {metrics['energy_mwh']:.4f} MWh")
    print(f"  Peak power: {metrics['peak_power_mw']:.4f} MW")
    print(f"  Total cost: EUR {metrics['total_cost_eur']:.2f}")
    print(f"  Carbon emissions: {metrics['total_carbon_kg']:.1f} kg CO2e")
    
    return profile, facility_profile, metrics

# ============================================================================
# SCENARIO 1: GPU POWER LIMITING
# ============================================================================

def scenario_gpu_limiting(profile: pd.DataFrame, baseline_metrics: Dict) -> pd.DataFrame:
    """Test GPU power limiting by reducing peak power consumption."""
    print_section("SCENARIO 1: GPU POWER LIMITING")
    print_scenario("GPU Limiting", "Reduce GPU power consumption through frequency scaling")
    
    results_list = []
    reductions = [0.2, 0.4, 0.6]  # 20%, 40%, 60% reduction
    
    for reduction in reductions:
        scenario_name = f"GPU-{int(reduction*100)}%"
        print(f"\n  Testing: {scenario_name} power reduction")
        
        try:
            # Create modified profile with reduced GPU power
            profile_modified = profile.copy()
            original_peak = profile_modified['gpu_power_w'].max()
            reduction_factor = (1 - reduction)
            profile_modified['gpu_power_w'] = profile_modified['gpu_power_w'] * reduction_factor
            
            # Convert to facility power
            facility_profile = power_model.convert_training_profile_to_center(
                profile_modified,
                nodes_per_center=NODES_PER_CENTER,
                dynamic_cpu_power=True,
                dynamic_memory_power=True,
            )
            
            # Run simulation
            results = run_simulation.run_hpc_simulation(
                facility_profile,
                number_of_centers=NUMBER_OF_CENTERS,
                grid_backend="Synthetic HPC grid",
            )
            
            # Calculate metrics
            results_final, total_energy = run_simulation.calculate_energy(results)
            
            price_table = cost_model.build_tou_price_table()
            cost_results, total_cost = cost_model.calculate_time_of_day_costs(
                results_final,
                price_table,
                simulation_start_hour=12.0
            )
            
            carbon_profile = carbon_model.build_german_carbon_intensity_profile()
            carbon_results, total_carbon = carbon_model.calculate_carbon_emissions(
                results_final,
                carbon_profile,
                simulation_start_hour=12.0
            )
            
            # Calculate deltas
            energy_delta = ((total_energy - baseline_metrics['energy_mwh']) / baseline_metrics['energy_mwh']) * 100
            cost_delta = ((total_cost - baseline_metrics['total_cost_eur']) / baseline_metrics['total_cost_eur']) * 100
            carbon_delta = ((total_carbon - baseline_metrics['total_carbon_kg']) / baseline_metrics['total_carbon_kg']) * 100
            peak_power = results_final['total_power_mw'].max()
            
            results_list.append({
                'scenario': scenario_name,
                'category': 'GPU Limiting',
                'parameter': f'{int(reduction*100)}% reduction',
                'gpu_peak_w': original_peak * reduction_factor,
                'energy_mwh': total_energy,
                'energy_delta_pct': energy_delta,
                'peak_power_mw': peak_power,
                'cost_eur': total_cost,
                'cost_delta_pct': cost_delta,
                'carbon_kg': total_carbon,
                'carbon_delta_pct': carbon_delta,
            })
            
            print(f"    OK Energy: {total_energy:.4f} MWh ({energy_delta:+.1f}%)")
            print(f"       Cost: EUR {total_cost:.2f} ({cost_delta:+.1f}%)")
            print(f"       Carbon: {total_carbon:.1f} kg CO2e ({carbon_delta:+.1f}%)")
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
    
    return pd.DataFrame(results_list)

# ============================================================================
# SCENARIO 2: PUE IMPROVEMENTS
# ============================================================================

def scenario_pue_improvement(profile: pd.DataFrame, baseline_metrics: Dict) -> pd.DataFrame:
    """Test PUE improvements through efficiency gains."""
    print_section("SCENARIO 2: PUE IMPROVEMENTS")
    print_scenario("PUE Improvement", "Reduce data center overhead through cooling improvements")
    
    results_list = []
    pue_values = [1.2, 1.15, 1.1]  # Baseline is 1.3
    
    for target_pue in pue_values:
        scenario_name = f"PUE-{target_pue}"
        print(f"\n  Testing: {scenario_name}")
        
        try:
            # Convert to facility power with modified PUE
            facility_profile = power_model.convert_training_profile_to_center(
                profile,
                nodes_per_center=NODES_PER_CENTER,
                dynamic_cpu_power=True,
                dynamic_memory_power=True,
            )
            
            # Override PUE
            facility_profile['baseline_pue'] = target_pue
            facility_profile['environmental_pue'] = target_pue
            facility_profile['center_total_power_mw'] = (
                facility_profile['node_power_w'] * NODES_PER_CENTER / 1_000_000 * target_pue
            )
            
            # Run simulation
            results = run_simulation.run_hpc_simulation(
                facility_profile,
                number_of_centers=NUMBER_OF_CENTERS,
                grid_backend="Synthetic HPC grid",
            )
            
            # Calculate metrics
            results_final, total_energy = run_simulation.calculate_energy(results)
            
            price_table = cost_model.build_tou_price_table()
            cost_results, total_cost = cost_model.calculate_time_of_day_costs(
                results_final,
                price_table,
                simulation_start_hour=12.0
            )
            
            carbon_profile = carbon_model.build_german_carbon_intensity_profile()
            carbon_results, total_carbon = carbon_model.calculate_carbon_emissions(
                results_final,
                carbon_profile,
                simulation_start_hour=12.0
            )
            
            # Calculate deltas
            energy_delta = ((total_energy - baseline_metrics['energy_mwh']) / baseline_metrics['energy_mwh']) * 100
            cost_delta = ((total_cost - baseline_metrics['total_cost_eur']) / baseline_metrics['total_cost_eur']) * 100
            carbon_delta = ((total_carbon - baseline_metrics['total_carbon_kg']) / baseline_metrics['total_carbon_kg']) * 100
            peak_power = results_final['total_power_mw'].max()
            
            results_list.append({
                'scenario': scenario_name,
                'category': 'PUE Improvement',
                'parameter': f'PUE {target_pue}',
                'pue_value': target_pue,
                'energy_mwh': total_energy,
                'energy_delta_pct': energy_delta,
                'peak_power_mw': peak_power,
                'cost_eur': total_cost,
                'cost_delta_pct': cost_delta,
                'carbon_kg': total_carbon,
                'carbon_delta_pct': carbon_delta,
            })
            
            print(f"    OK Energy: {total_energy:.4f} MWh ({energy_delta:+.1f}%)")
            print(f"       Cost: EUR {total_cost:.2f} ({cost_delta:+.1f}%)")
            print(f"       Carbon: {total_carbon:.1f} kg CO2e ({carbon_delta:+.1f}%)")
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
    
    return pd.DataFrame(results_list)

# ============================================================================
# SCENARIO 3: WORKLOAD SHIFTING
# ============================================================================

def scenario_workload_shifting(profile: pd.DataFrame, baseline_metrics: Dict) -> pd.DataFrame:
    """Test workload shifting by running at different times of day."""
    print_section("SCENARIO 3: WORKLOAD SHIFTING")
    print_scenario("Workload Shifting", "Run workload at different times to minimize costs/carbon")
    
    results_list = []
    start_hours = [
        (0, "Off-peak (00:00)"),
        (6, "Early Morning (06:00)"),
        (12, "Midday (12:00)"),
        (19, "Evening (19:00)"),
    ]
    
    for start_hour, description in start_hours:
        scenario_name = f"Shift-{start_hour:02d}h"
        print(f"\n  Testing: {scenario_name} - {description}")
        
        try:
            # Convert to facility power
            facility_profile = power_model.convert_training_profile_to_center(
                profile,
                nodes_per_center=NODES_PER_CENTER,
                dynamic_cpu_power=True,
                dynamic_memory_power=True,
            )
            
            # Run simulation
            results = run_simulation.run_hpc_simulation(
                facility_profile,
                number_of_centers=NUMBER_OF_CENTERS,
                grid_backend="Synthetic HPC grid",
            )
            
            # Calculate metrics
            results_final, total_energy = run_simulation.calculate_energy(results)
            
            price_table = cost_model.build_tou_price_table()
            cost_results, total_cost = cost_model.calculate_time_of_day_costs(
                results_final,
                price_table,
                simulation_start_hour=float(start_hour)
            )
            
            carbon_profile = carbon_model.build_german_carbon_intensity_profile()
            carbon_results, total_carbon = carbon_model.calculate_carbon_emissions(
                results_final,
                carbon_profile,
                simulation_start_hour=float(start_hour)
            )
            
            # Calculate deltas
            energy_delta = ((total_energy - baseline_metrics['energy_mwh']) / baseline_metrics['energy_mwh']) * 100
            cost_delta = ((total_cost - baseline_metrics['total_cost_eur']) / baseline_metrics['total_cost_eur']) * 100
            carbon_delta = ((total_carbon - baseline_metrics['total_carbon_kg']) / baseline_metrics['total_carbon_kg']) * 100
            
            results_list.append({
                'scenario': scenario_name,
                'category': 'Workload Shifting',
                'parameter': description,
                'start_hour': start_hour,
                'energy_mwh': total_energy,
                'energy_delta_pct': energy_delta,
                'cost_eur': total_cost,
                'cost_delta_pct': cost_delta,
                'carbon_kg': total_carbon,
                'carbon_delta_pct': carbon_delta,
            })
            
            print(f"    OK Energy: {total_energy:.4f} MWh ({energy_delta:+.1f}%)")
            print(f"       Cost: EUR {total_cost:.2f} ({cost_delta:+.1f}%)")
            print(f"       Carbon: {total_carbon:.1f} kg CO2e ({carbon_delta:+.1f}%)")
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
    
    return pd.DataFrame(results_list)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_scenarios():
    """Execute all scenario comparisons."""
    
    print_header("SCENARIO COMPARISON ANALYSIS")
    print("Testing GPU limiting, PUE improvements, and workload shifting")
    
    try:
        # Calculate baseline
        profile, facility_profile, baseline_metrics = calculate_baseline()
        
        # Run scenarios
        print("\n")
        scenarios_gpu = scenario_gpu_limiting(profile, baseline_metrics)
        scenarios_pue = scenario_pue_improvement(profile, baseline_metrics)
        scenarios_shift = scenario_workload_shifting(profile, baseline_metrics)
        
        # Combine all scenarios
        all_scenarios = pd.concat(
            [scenarios_gpu, scenarios_pue, scenarios_shift],
            ignore_index=True
        )
        
        # Analysis
        print_section("COMPARISON ANALYSIS")
        
        if not all_scenarios.empty:
            # Best by energy
            best_energy = all_scenarios.loc[all_scenarios['energy_delta_pct'].idxmin()]
            energy_savings = abs(best_energy['energy_delta_pct'])
            print(f"\nBest Energy Savings: {best_energy['scenario']} ({energy_savings:.1f}% reduction)")
            
            # Best by cost
            best_cost = all_scenarios.loc[all_scenarios['cost_delta_pct'].idxmin()]
            cost_savings = abs(best_cost['cost_delta_pct'])
            print(f"Best Cost Reduction: {best_cost['scenario']} (EUR {best_cost['cost_eur']:.2f}, {cost_savings:.1f}% reduction)")
            
            # Best by carbon
            best_carbon = all_scenarios.loc[all_scenarios['carbon_delta_pct'].idxmin()]
            carbon_reduction = abs(best_carbon['carbon_delta_pct'])
            print(f"Best Carbon Reduction: {best_carbon['scenario']} ({carbon_reduction:.1f}% reduction)")
        
        # Export results
        print_section("EXPORTING RESULTS")
        
        # Baseline metrics
        baseline_df = pd.DataFrame([{
            'scenario': 'Baseline',
            'category': 'Baseline',
            'energy_mwh': baseline_metrics['energy_mwh'],
            'cost_eur': baseline_metrics['total_cost_eur'],
            'carbon_kg': baseline_metrics['total_carbon_kg'],
        }])
        
        # Combine
        comparison_df = pd.concat([baseline_df, all_scenarios], ignore_index=True)
        
        # Export CSV
        csv_path = OUTPUT_DIR / "scenario_comparison_results.csv"
        comparison_df.to_csv(csv_path, index=False)
        print(f"  OK Comparison results: {csv_path.name}")
        
        # Export details
        details_path = OUTPUT_DIR / "scenario_details.csv"
        all_scenarios.to_csv(details_path, index=False)
        print(f"  OK Scenario details: {details_path.name}")
        
        # Create summary report
        summary_text = f"""SCENARIO COMPARISON REPORT
Generated: {pd.Timestamp.now()}

BASELINE METRICS
================
Energy: {baseline_metrics['energy_mwh']:.4f} MWh
Peak Power: {baseline_metrics['peak_power_mw']:.4f} MW
Total Cost: EUR {baseline_metrics['total_cost_eur']:.2f}
Carbon Emissions: {baseline_metrics['total_carbon_kg']:.1f} kg CO2e
Convergence Rate: {baseline_metrics['convergence_rate']:.1f}%

"""
        
        if not all_scenarios.empty:
            summary_text += "TOP OPPORTUNITIES\n"
            summary_text += "=================\n"
            
            best_energy = all_scenarios.loc[all_scenarios['energy_delta_pct'].idxmin()]
            best_cost = all_scenarios.loc[all_scenarios['cost_delta_pct'].idxmin()]
            best_carbon = all_scenarios.loc[all_scenarios['carbon_delta_pct'].idxmin()]
            
            summary_text += f"\n1. Energy Savings: {best_energy['scenario']}\n"
            summary_text += f"   Reduction: {abs(best_energy['energy_delta_pct']):.1f}%\n"
            summary_text += f"   Parameter: {best_energy['parameter']}\n"
            
            summary_text += f"\n2. Cost Reduction: {best_cost['scenario']}\n"
            summary_text += f"   Cost: EUR {best_cost['cost_eur']:.2f}\n"
            summary_text += f"   Reduction: {abs(best_cost['cost_delta_pct']):.1f}%\n"
            
            summary_text += f"\n3. Carbon Reduction: {best_carbon['scenario']}\n"
            summary_text += f"   Carbon: {best_carbon['carbon_kg']:.1f} kg CO2e\n"
            summary_text += f"   Reduction: {abs(best_carbon['carbon_delta_pct']):.1f}%\n"
        
        summary_text += "\nALL SCENARIOS\n"
        summary_text += "=============\n"
        summary_text += all_scenarios.to_string()
        
        summary_text += "\n\nNEXT STEPS\n"
        summary_text += "==========\n"
        summary_text += "- Review CSV files for detailed analysis\n"
        summary_text += "- Evaluate combined scenarios\n"
        summary_text += "- Assess implementation feasibility\n"
        
        report_path = OUTPUT_DIR / "comparison_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print(f"  OK Report: {report_path.name}")
        
        print_header("SCENARIO ANALYSIS COMPLETE")
        print(f"Results: {OUTPUT_DIR}")
        return True
        
    except Exception as e:
        print_header("ERROR IN SCENARIO ANALYSIS")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_scenarios()
    sys.exit(0 if success else 1)
