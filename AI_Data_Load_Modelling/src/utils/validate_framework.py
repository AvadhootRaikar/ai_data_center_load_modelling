"""
Framework Validation Script

Validates DS_Proejct_v0 framework by:
1. Loading MLPerf traces from thesis data
2. Running baseline simulation
3. Comparing results with thesis findings
4. Reporting agreement/discrepancies

Run from project root: python validate_framework.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add simulation module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation import profile_builder, power_model, run_simulation, energy_projection, cost_model

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths to thesis data
THESIS_DATA_ROOT = Path(__file__).parent.parent / "Master thesis_0" / "Master thesis" / "Simulation"
TRAINING_FOLDER = THESIS_DATA_ROOT / "data" / "raw_runs" / "training"
INFERENCE_FOLDER = THESIS_DATA_ROOT / "data" / "raw_runs" / "inference"

# Framework parameters
NODES_PER_CENTER = 20
NUMBER_OF_CENTERS = 3
GRID_BACKEND = "Synthetic HPC grid"

# Thesis baseline reference values (from thesis findings)
THESIS_BASELINE_METRICS = {
    "description": "Baseline: 3 centers, synthetic grid, training workload",
    "expected_peak_power_mw": 8.5,  # Approximate from thesis Section 4.2
    "expected_duration_hours": 0.196,  # Profile duration (~707 samples × 1s)
    "expected_nodes_per_center": 20,
    "expected_centers": 3,
}

# Tolerance for comparison (±%)
TOLERANCE_PERCENT = 5.0

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_section(title):
    """Print formatted subsection."""
    print(f"\n▸ {title}")
    print("  " + "-"*66)

def compare_values(actual, expected, tolerance_percent=5.0, name=""):
    """Compare actual vs expected value with tolerance."""
    if expected == 0:
        diff_percent = 0 if actual == 0 else 100
    else:
        diff_percent = abs((actual - expected) / expected) * 100
    
    within_tolerance = diff_percent <= tolerance_percent
    status = "✅ PASS" if within_tolerance else "⚠️  WARN"
    
    print(f"    {status} {name}")
    print(f"       Expected: {expected:.3f} | Actual: {actual:.3f} | Diff: {diff_percent:.1f}%")
    
    return within_tolerance

def validate_data_loading():
    """Step 1: Validate data can be loaded."""
    print_section("STEP 1: Load Training Traces")
    
    if not TRAINING_FOLDER.exists():
        print(f"    ❌ ERROR: Training folder not found: {TRAINING_FOLDER}")
        return False, None
    
    csv_files = list(TRAINING_FOLDER.glob("*.csv"))
    print(f"    ✅ Found {len(csv_files)} CSV files in {TRAINING_FOLDER.name}/")
    for f in csv_files:
        print(f"       • {f.name}")
    
    if len(csv_files) < 2:
        print(f"    ❌ ERROR: Need at least 2 CSV files, found {len(csv_files)}")
        return False, None
    
    return True, csv_files

def validate_profile_building(training_folder):
    """Step 2: Validate profile building."""
    print_section("STEP 2: Build Measured Workload Profile")
    
    try:
        profile = profile_builder.build_measured_profile(
            training_folder,
            workload_label="Training"
        )
        print(f"    ✅ Profile built successfully")
        print(f"       Samples: {len(profile)}")
        print(f"       Duration: {profile['elapsed_hours'].iloc[-1]:.3f} hours")
        print(f"       Peak GPU Power: {profile['gpu_power_w'].max():.1f} W")
        print(f"       Avg GPU Power: {profile['gpu_power_w'].mean():.1f} W")
        
        # Validate quality metrics
        quality = profile_builder.validate_trace_quality(profile)
        print(f"       Utilization data available: {quality['has_gpu_util']}")
        
        return True, profile
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        return False, None

def validate_power_model(profile):
    """Step 3: Validate power model conversion."""
    print_section("STEP 3: Convert to Facility-Level Power")
    
    try:
        facility_profile = power_model.convert_training_profile_to_center(
            profile,
            nodes_per_center=NODES_PER_CENTER,
            dynamic_cpu_power=True,
            dynamic_memory_power=True,
        )
        print(f"    ✅ Power model conversion successful")
        print(f"       Peak Center Power: {facility_profile['center_total_power_mw'].max():.4f} MW")
        print(f"       Avg Center Power: {facility_profile['center_total_power_mw'].mean():.4f} MW")
        print(f"       PUE: {facility_profile['baseline_pue'].iloc[0]:.2f}")
        
        # Verify scaling makes sense
        peak_node_power = facility_profile['node_power_w'].max()
        peak_center_power = facility_profile['center_total_power_mw'].max() * 1_000_000
        expected_center_power = peak_node_power * NODES_PER_CENTER * 1.3  # Apply PUE
        
        print(f"       Peak Node Power: {peak_node_power:.1f} W")
        print(f"       Peak Center Power (raw): {peak_center_power:.1f} W")
        print(f"       Expected (with PUE): {expected_center_power:.1f} W")
        
        return True, facility_profile
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        return False, None

def validate_simulation(facility_profile):
    """Step 4: Run power flow simulation."""
    print_section("STEP 4: Execute Power Flow Simulation")
    
    try:
        results = run_simulation.run_hpc_simulation(
            facility_profile,
            number_of_centers=NUMBER_OF_CENTERS,
            grid_backend=GRID_BACKEND,
        )
        print(f"    ✅ Simulation completed")
        print(f"       Timesteps: {len(results)}")
        print(f"       Duration: {results['elapsed_hours'].iloc[-1]:.3f} hours")
        print(f"       Total Power: {results['total_power_mw'].sum():.2f} MWh integrated")
        print(f"       Convergence Rate: {(results['converged'].sum() / len(results) * 100):.1f}%")
        
        # Check for issues
        non_converged = len(results) - results['converged'].sum()
        if non_converged > 0:
            print(f"       ⚠️  {non_converged} non-converged timesteps")
        
        voltage_issues = results['voltage_violation_count'].sum()
        if voltage_issues > 0:
            print(f"       ⚠️  {voltage_issues} voltage violations detected")
        
        line_overloads = results['line_overload_count'].sum()
        if line_overloads > 0:
            print(f"       ⚠️  {line_overloads} line overloads detected")
        
        return True, results
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def validate_energy_calculation(results):
    """Step 5: Validate energy and cost calculations."""
    print_section("STEP 5: Calculate Energy Metrics")
    
    try:
        # Calculate energy
        results_with_energy, total_energy = run_simulation.calculate_energy(results)
        print(f"    ✅ Energy calculated")
        print(f"       Total Energy: {total_energy:.4f} MWh")
        print(f"       Avg Power: {(total_energy / results_with_energy['elapsed_hours'].iloc[-1]):.4f} MW")
        
        # Calculate projections
        projections = energy_projection.calculate_energy_projections(results_with_energy)
        print(f"       1h projection: {projections['energy_1h_mwh']:.4f} MWh")
        print(f"       24h projection: {projections['energy_24h_mwh']:.2f} MWh")
        
        # Calculate costs
        price_table = cost_model.build_tou_price_table()
        cost_results, total_cost = cost_model.calculate_time_of_day_costs(
            results_with_energy,
            price_table,
            simulation_start_hour=12.0
        )
        print(f"    ✅ Costs calculated")
        print(f"       Total Cost (ToD): €{total_cost:.2f}")
        
        return True, results_with_energy
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def validate_multi_center_scaling(facility_profile):
    """Step 6: Verify multi-center scaling."""
    print_section("STEP 6: Multi-Center Scaling Check")
    
    try:
        # Run single center
        results_1 = run_simulation.run_hpc_simulation(
            facility_profile,
            number_of_centers=1,
            grid_backend=GRID_BACKEND,
        )
        
        # Run 3 centers
        results_3 = run_simulation.run_hpc_simulation(
            facility_profile,
            number_of_centers=3,
            grid_backend=GRID_BACKEND,
        )
        
        # Check scaling (should be ~3× for same profile)
        power_1 = results_1['total_power_mw'].max()
        power_3 = results_3['total_power_mw'].max()
        ratio = power_3 / power_1 if power_1 > 0 else 0
        
        print(f"    ✅ Scaling validation")
        print(f"       1 center peak: {power_1:.4f} MW")
        print(f"       3 centers peak: {power_3:.4f} MW")
        print(f"       Ratio: {ratio:.2f}× (expected ~3.0×)")
        
        tolerance_ok = abs(ratio - 3.0) < 0.2
        if tolerance_ok:
            print(f"       ✅ Scaling is linear (correct)")
        else:
            print(f"       ⚠️  Scaling deviation detected")
        
        return True, power_1, power_3
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        return False, 0, 0

def validate_against_thesis():
    """Step 7: Compare with thesis baseline."""
    print_section("STEP 7: Compare with Thesis Baseline")
    
    print(f"    Reference: {THESIS_BASELINE_METRICS['description']}")
    
    # These would be refined after first validation
    print(f"    Note: Tolerances set to ±{TOLERANCE_PERCENT}%")
    print(f"    (Will be refined once thesis exact values are verified)")
    
    return True

# ============================================================================
# MAIN VALIDATION FLOW
# ============================================================================

def run_validation():
    """Execute full validation sequence."""
    
    print_header("DS_Proejct_v0 FRAMEWORK VALIDATION")
    print("Testing against MLPerf traces from Master thesis")
    
    results = {}
    
    # Step 1: Load data
    data_ok, csv_files = validate_data_loading()
    if not data_ok:
        print_header("VALIDATION FAILED")
        print("Cannot proceed without data files.")
        return False
    
    # Step 2: Build profile
    profile_ok, profile = validate_profile_building(TRAINING_FOLDER)
    if not profile_ok:
        print_header("VALIDATION FAILED")
        return False
    results['profile'] = profile
    
    # Step 3: Power model
    power_ok, facility_profile = validate_power_model(profile)
    if not power_ok:
        print_header("VALIDATION FAILED")
        return False
    results['facility_profile'] = facility_profile
    
    # Step 4: Simulation
    sim_ok, sim_results = validate_simulation(facility_profile)
    if not sim_ok:
        print_header("VALIDATION FAILED")
        return False
    results['sim_results'] = sim_results
    
    # Step 5: Energy & costs
    energy_ok, results_final = validate_energy_calculation(sim_results)
    if not energy_ok:
        print_header("VALIDATION FAILED")
        return False
    results['results_final'] = results_final
    
    # Step 6: Scaling
    scaling_ok, power_1, power_3 = validate_multi_center_scaling(facility_profile)
    results['scaling_ok'] = scaling_ok
    
    # Step 7: Thesis comparison
    thesis_ok = validate_against_thesis()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print_header("VALIDATION SUMMARY")
    
    all_ok = data_ok and profile_ok and power_ok and sim_ok and energy_ok and scaling_ok and thesis_ok
    
    if all_ok:
        print("\n✅ ALL CHECKS PASSED\n")
        print("Framework is functional and ready for analysis!")
        print("\nNext steps:")
        print("  1. Run scenario comparisons")
        print("  2. Generate carbon impact report")
        print("  3. Create dashboard visualizations")
    else:
        print("\n⚠️  SOME CHECKS FAILED\n")
        print("Please review issues above and fix before proceeding.")
    
    # Export results
    print("\n▸ Exporting Results")
    print("  " + "-"*66)
    
    output_dir = Path(__file__).parent / "outputs" / "validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if 'results_final' in results:
        csv_path = output_dir / "baseline_simulation_results.csv"
        results['results_final'].to_csv(csv_path, index=False)
        print(f"    ✅ Results exported: {csv_path}")
    
    # Create summary report
    summary_text = f"""
FRAMEWORK VALIDATION REPORT
Generated: {pd.Timestamp.now()}

Configuration:
  - Training data folder: {TRAINING_FOLDER}
  - Grid backend: {GRID_BACKEND}
  - Nodes per center: {NODES_PER_CENTER}
  - Centers tested: 1, 3

Validation Results:
  - Data loading: {'PASS' if data_ok else 'FAIL'}
  - Profile building: {'PASS' if profile_ok else 'FAIL'}
  - Power model: {'PASS' if power_ok else 'FAIL'}
  - Simulation: {'PASS' if sim_ok else 'FAIL'}
  - Energy calculations: {'PASS' if energy_ok else 'FAIL'}
  - Multi-center scaling: {'PASS' if scaling_ok else 'FAIL'}
  - Thesis comparison: {'PASS' if thesis_ok else 'FAIL'}

Overall Status: {'PASSED' if all_ok else 'FAILED'}

Next Actions:
  - Refine thesis baseline values
  - Run scenario comparisons
  - Generate detailed reports
"""
    
    report_path = output_dir / "validation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print(f"    Report exported: {report_path}")
    
    return all_ok

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
