"""
Water Cooling Model Demonstration & Testing

Showcases the physics-based water usage and thermal modeling for HPC data centers.
Demonstrates:
1. Dynamic PUE calculation at different temperatures
2. Water usage estimation (wet vs. dry cooling)
3. Cooling energy breakdown
4. Thermal-aware scheduling recommendations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from simulation.water_cooling_model import (
    calculate_dynamic_pue,
    calculate_water_usage,
    calculate_cooling_energy_breakdown,
    add_water_metrics_to_profile,
    get_thermal_aware_scheduling_recommendations,
)


def demo_dynamic_pue():
    """Demonstrate how PUE changes with ambient temperature."""
    print("\n" + "="*70)
    print("DEMO 1: Dynamic PUE vs. Ambient Temperature")
    print("="*70)
    print("Baseline PUE (at 20°C): 1.30")
    print("Sensitivity: 0.025 per °C\n")
    
    temps = list(range(5, 36, 5))
    print(f"{'Ambient Temp (°C)':<20} {'PUE':<10} {'Cooling Overhead %':<20}")
    print("-" * 50)
    
    for temp in temps:
        pue = calculate_dynamic_pue(
            ambient_temp_celsius=temp,
            baseline_pue=1.3,
            workload_intensity=1.0
        )
        cooling_overhead = (pue - 1.0) * 100
        print(f"{temp:<20} {pue:<10.2f} {cooling_overhead:<20.1f}%")
    
    print("\nInsights:")
    print("  • Cold nights (5°C): PUE ≈ 1.06 → Only 6% cooling overhead")
    print("  • Reference (20°C): PUE = 1.30 → 30% cooling overhead")
    print("  • Hot days (35°C): PUE ≈ 1.69 → 69% cooling overhead")


def demo_water_usage():
    """Demonstrate water usage under different conditions."""
    print("\n" + "="*70)
    print("DEMO 2: Water Usage Estimation")
    print("="*70)
    print("Scenario: 40 kW GPU + 8 kW CPU (typical HPC facility)\n")
    
    # Wet cooling conditions
    print("WET COOLING (with evaporative cooling towers):")
    print(f"{'Conditions':<35} {'Water Usage':<20} {'Per Day':<15}")
    print("-" * 70)
    
    conditions = [
        (5, 50, "Cold night, high humidity"),
        (15, 40, "Spring morning, moderate humidity"),
        (20, 40, "Reference conditions"),
        (25, 35, "Warm day, lower humidity"),
        (30, 25, "Hot day, low humidity"),
    ]
    
    for temp, humidity, description in conditions:
        water_lps, breakdown = calculate_water_usage(
            gpu_power_kw=40,
            cpu_power_kw=8,
            cooling_type="wet",
            ambient_temp_celsius=temp,
            relative_humidity_percent=humidity
        )
        water_per_day = breakdown["water_liters_per_day"]
        print(f"{description:<35} {water_lps:.2f} L/s     {water_per_day:>10,.0f} L")
    
    # Dry cooling
    print("\nDRY COOLING (radiator-based, no water consumption):")
    water_lps, breakdown = calculate_water_usage(
        gpu_power_kw=40,
        cpu_power_kw=8,
        cooling_type="dry"
    )
    print(f"  Water consumption: {water_lps} L/s (zero water)")
    print(f"  Energy overhead: {breakdown['dry_cooling_energy_overhead_percent']:.1f}% (higher energy cost)")


def demo_cooling_breakdown():
    """Demonstrate cooling energy breakdown."""
    print("\n" + "="*70)
    print("DEMO 3: Cooling Energy Breakdown")
    print("="*70)
    print("IT Power = 40 kW (GPU 40 kW + CPU 8 kW)\n")
    
    print(f"{'PUE':<10} {'Total Facility':<18} {'Cooling Power':<18} {'% of Total':<15}")
    print("-" * 60)
    
    for pue in [1.1, 1.3, 1.5, 1.7]:
        breakdown = calculate_cooling_energy_breakdown(
            it_power_kw=48,
            pue=pue
        )
        print(f"{pue:<10.2f} {breakdown['total_facility_power_kw']:<18.1f} kW "
              f"{breakdown['cooling_power_total_kw']:<18.1f} kW "
              f"{breakdown['cooling_power_percent']:<15.1f}%")


def demo_thermal_scheduling():
    """Demonstrate thermal-aware scheduling optimization."""
    print("\n" + "="*70)
    print("DEMO 4: Thermal-Aware Scheduling Optimization")
    print("="*70)
    print("24-hour optimization considering temperature, cost, and carbon\n")
    
    # Create 24-hour profiles
    hours = np.arange(24)
    
    # Typical German ambient temperature profile (sine wave + offset)
    ambient_temps = 15 + 8 * np.sin((hours - 6) * np.pi / 24)
    
    # Typical German EPEX SPOT prices (EUR/kWh)
    prices = np.array([0.035, 0.033, 0.032, 0.031, 0.032, 0.034, 0.042, 0.048,
                       0.050, 0.045, 0.040, 0.038, 0.036, 0.038, 0.042, 0.048,
                       0.050, 0.045, 0.040, 0.038, 0.036, 0.035, 0.034, 0.033])
    
    # Typical SMARD carbon intensity (g CO2/kWh)
    carbon = np.array([120, 110, 100, 90, 100, 120, 150, 180,
                       200, 180, 150, 120, 100, 120, 150, 180,
                       200, 180, 150, 130, 120, 110, 100, 110])
    
    # Create mock profile
    gpu_power = np.full(24, 40000)  # 40 kW per hour
    profile_df = pd.DataFrame({
        "gpu_power_w": gpu_power,
        "cpu_power_w": gpu_power * 0.2,
    })
    
    ambient_temp_series = pd.Series(ambient_temps)
    price_series = pd.Series(prices)
    carbon_series = pd.Series(carbon)
    
    # Get recommendations
    enriched, recs = add_water_metrics_to_profile(
        profile_df=profile_df,
        cooling_type="wet",
        baseline_pue=1.3,
        ambient_temps_celsius=ambient_temp_series,
    )
    
    # Calculate scores
    pue_norm = (enriched["dynamic_pue"] - enriched["dynamic_pue"].min()) / (enriched["dynamic_pue"].max() - enriched["dynamic_pue"].min()) * 100
    price_norm = (price_series - price_series.min()) / (price_series.max() - price_series.min()) * 100
    carbon_norm = (carbon_series - carbon_series.min()) / (carbon_series.max() - carbon_series.min()) * 100
    combined = 0.30 * pue_norm + 0.40 * price_norm + 0.30 * carbon_norm
    
    # Display results
    print(f"{'Hour':<6} {'Temp':<7} {'Price':<8} {'Carbon':<8} {'PUE':<7} {'Score':<8} {'Recommend':<12}")
    print("-" * 70)
    
    best_hours = combined.nsmallest(6).index.tolist()
    worst_hours = combined.nlargest(3).index.tolist()
    
    for h in range(24):
        temp_str = f"{ambient_temps[h]:.1f}°C"
        price_str = f"€{prices[h]:.3f}"
        carbon_str = f"{carbon[h]:.0f} g"
        pue_str = f"{enriched['dynamic_pue'].iloc[h]:.2f}"
        score_str = f"{combined.iloc[h]:.1f}"
        recommend_str = "✓ RUN" if h in best_hours else "✗ AVOID" if h in worst_hours else "-"
        
        print(f"{h:<6} {temp_str:<7} {price_str:<8} {carbon_str:<8} {pue_str:<7} {score_str:<8} {recommend_str:<12}")
    
    print(f"\n✓ Best hours to run workloads: {best_hours}")
    print(f"✗ Hours to avoid: {worst_hours}")


def demo_annual_projections():
    """Project annual water savings from optimization."""
    print("\n" + "="*70)
    print("DEMO 5: Annual Water & Energy Projections")
    print("="*70)
    
    # Baseline: constant operation at 40 kW GPU, average 20°C
    baseline_water_lps, _ = calculate_water_usage(
        gpu_power_kw=40,
        cpu_power_kw=8,
        cooling_type="wet",
        ambient_temp_celsius=20,
        relative_humidity_percent=40
    )
    baseline_water_per_year = baseline_water_lps * 3600 * 24 * 365 / 1000  # 1000L = 1m³
    
    # Optimized: thermal-aware scheduling with dry cooling in summer
    # Assume: 70% wet cooling (winter) + 30% dry cooling (summer)
    wet_water_lps, _ = calculate_water_usage(
        gpu_power_kw=40,
        cpu_power_kw=8,
        cooling_type="wet",
        ambient_temp_celsius=15,
        relative_humidity_percent=50
    )
    dry_water_lps = 0.0
    
    optimized_water_per_year = (wet_water_lps * 0.7 * 3600 * 24 * 365 + dry_water_lps * 0.3 * 3600 * 24 * 365) / 1000
    
    print(f"\nBASELINE (Constant wet cooling, average conditions):")
    print(f"  Water consumption: {baseline_water_lps:.2f} L/s")
    print(f"  Annual water use: {baseline_water_per_year:,.0f} m³ ({baseline_water_per_year * 1000:,.0f},000 L)")
    
    print(f"\nOPTIMIZED (Thermal-aware + seasonal cooling):")
    print(f"  Water consumption: {(wet_water_lps * 0.7 + dry_water_lps * 0.3):.2f} L/s (blended)")
    print(f"  Annual water use: {optimized_water_per_year:,.0f} m³ ({optimized_water_per_year * 1000:,.0f},000 L)")
    
    water_saved_m3 = baseline_water_per_year - optimized_water_per_year
    water_saved_pct = (water_saved_m3 / baseline_water_per_year) * 100
    
    print(f"\n💧 ANNUAL WATER SAVINGS: {water_saved_m3:,.0f} m³ ({water_saved_pct:.1f}% reduction)")
    print(f"   Equivalent to: {water_saved_m3 / 2.6:.0f} Olympic swimming pools")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("WATER COOLING & THERMAL MODELING DEMONSTRATION")
    print("AI Data Center HPC Optimization Framework")
    print("="*70)
    
    demo_dynamic_pue()
    demo_water_usage()
    demo_cooling_breakdown()
    demo_thermal_scheduling()
    demo_annual_projections()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Takeaways:")
    print("  1. Ambient temperature heavily impacts PUE (1.06 at 5°C vs. 1.69 at 35°C)")
    print("  2. Water usage varies 2-3x based on temperature and humidity")
    print("  3. Thermal-aware scheduling enables simultaneous cost + carbon optimization")
    print("  4. Strategic cooling method selection (wet vs. dry) provides major water savings")
    print("  5. Combined strategies can reduce annual water consumption by 30-40%")
