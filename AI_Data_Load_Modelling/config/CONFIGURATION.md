# Configuration Parameters

This file defines all configurable parameters for the simulation framework.

## Infrastructure Configuration

```yaml
# HPC Center Configuration
infrastructure:
  nodes_per_center: 20                # Number of compute nodes per center
  clusters_per_center: 4              # Clusters within a center
  racks_per_cluster: 10               # Racks per cluster
  
  # Power per node (in Watts)
  cpu_power_base_w: 150               # Base CPU power
  memory_power_base_w: 40             # Base memory power
  storage_power_base_w: 10            # Storage subsystem
  network_power_base_w: 10            # Network/switching
  
  # Power scaling behavior (when utilization data available)
  dynamic_cpu_power: true             # Scale CPU with utilization
  dynamic_memory_power: true          # Scale memory with utilization
  cpu_idle_power_ratio: 0.3           # CPU power at 0% utilization
  memory_idle_power_ratio: 0.5        # Memory power at 0% utilization
  
  # PUE (Power Usage Effectiveness)
  baseline_pue: 1.3                   # Baseline PUE
  dynamic_pue: false                  # Enable temperature adjustment
  reference_temperature_celsius: 20.0 # Reference temp for PUE baseline
  temperature_efficiency_factor: 0.02 # PUE change per °C deviation
```

## Grid Configuration

```yaml
grid:
  # Grid backend selection
  backend: "Synthetic HPC grid"       # Options: "Synthetic HPC grid", "SimBench German benchmark grid"
  
  # SimBench specific
  simbench_code: "1-MV-rural--0-sw"   # When using SimBench backend
  include_existing_simbench_loads: true # Keep existing grid loads in SimBench
  
  # Grid parameters
  simulation_fast_mode: false         # false=AC power flow, true=DC approx
  max_iterations: 30                  # Newton-Raphson iterations
  
  # Reactive power model
  reactive_power_factor: 0.33         # Q = factor × P (simple assumption)
```

## Pricing Configuration

```yaml
pricing:
  # Time-of-use tariff (German market profile, €/kWh)
  tou_rates:
    night:                            # 00:00-06:00
      start_hour: 0
      end_hour: 6
      price_eur_per_kwh: 0.27
      description: "Low-demand night hours"
    
    morning_peak:                     # 06:00-10:00
      start_hour: 6
      end_hour: 10
      price_eur_per_kwh: 0.44
      description: "Morning demand peak"
    
    midday:                           # 10:00-16:00
      start_hour: 10
      end_hour: 16
      price_eur_per_kwh: 0.31
      description: "Midday/renewable window (solar generation peak)"
    
    evening_peak:                     # 16:00-21:00
      start_hour: 16
      end_hour: 21
      price_eur_per_kwh: 0.50
      description: "Evening peak demand"
    
    late:                             # 21:00-24:00
      start_hour: 21
      end_hour: 24
      price_eur_per_kwh: 0.35
      description: "Late evening (demand decreases)"
  
  # Simulation start time (hour of day, 0-24)
  simulation_start_hour: 12.0         # Noon (affects cost calculation)
```

## Carbon Intensity Configuration

```yaml
carbon:
  # Time-of-day grid carbon intensity (German grid, gCO2/kWh)
  grid_intensity:
    night:                            # 00:00-06:00
      start_hour: 0
      end_hour: 6
      intensity_g_co2_per_kwh: 100
      description: "Low demand, reduced coal/gas firing"
    
    morning_peak:                     # 06:00-10:00
      start_hour: 6
      end_hour: 10
      intensity_g_co2_per_kwh: 200
      description: "Morning demand peak"
    
    midday:                           # 10:00-16:00
      start_hour: 10
      end_hour: 16
      intensity_g_co2_per_kwh: 80
      description: "Solar generation peak (low grid carbon)"
    
    evening_peak:                     # 16:00-21:00
      start_hour: 16
      end_hour: 21
      intensity_g_co2_per_kwh: 250
      description: "Evening peak demand"
    
    late:                             # 21:00-24:00
      start_hour: 21
      end_hour: 24
      intensity_g_co2_per_kwh: 120
      description: "Late evening (demand decreases)"
  
  # Renewable energy penetration
  renewable_fraction: 0.5             # Fraction of grid from renewables (0-1)
  non_renewable_intensity_g_per_kwh: 400  # Carbon intensity of non-renewable portion
```

## Scenario Configuration

```yaml
scenarios:
  # GPU Power Limiting Scenario
  gpu_power_limiting:
    gpu_power_factor: 0.90            # Reduce GPU power to 90%
    slowdown_sensitivity: 0.7         # Performance degradation model
    min_performance_factor: 0.50      # Minimum performance (50% max slowdown)
    model: "utilization_based"        # Use utilization-aware slowdown
  
  # PUE Improvement Scenario
  pue_improvement:
    pue_factor: 0.85                  # Reduce PUE overhead to 85%
    description: "Better cooling efficiency"
  
  # Workload Shifting Scenario
  workload_shifting:
    target_start_hour: 0.0            # Start time (e.g., midnight)
    description: "Shift workload to cheaper/cleaner hours"
  
  # Load Distribution Scenario
  load_distribution:
    active_centers_fraction: 0.5      # Use only 50% of centers
    description: "Distribute load across fewer centers"
```

## Data Configuration

```yaml
data:
  # Paths relative to project root
  raw_training_folder: "data/raw_runs/training"
  raw_inference_folder: "data/raw_runs/inference"
  processed_data_folder: "data/processed"
  results_output_folder: "outputs"
  
  # Data validation
  min_trace_samples: 2                # Minimum CSV files for averaging
  max_timestamp_gap_seconds: 300      # Max gap before rejecting sample
  outlier_detection: true             # Remove anomalous power values
  outlier_quantile: 0.99              # Use 99th percentile for capping
```

## Logging Configuration

```yaml
logging:
  level: "INFO"                       # DEBUG, INFO, WARNING, ERROR
  file: "outputs/simulation.log"
  console_output: true
```

---

# Usage Examples

## Example 1: Dynamic Power Modeling

```python
from simulation import power_model

profile = pd.read_csv("workload_profile.csv")

# With dynamic power modeling (recommended)
enhanced_profile = power_model.convert_training_profile_to_center(
    profile,
    nodes_per_center=20,
    cpu_power_per_node=150,
    ram_power_per_node=40,
    dynamic_cpu_power=True,           # Scale CPU with utilization
    dynamic_memory_power=True,        # Scale memory with utilization
    ambient_temp_celsius=20,          # Environmental temperature
    dynamic_pue=False                 # Standard PUE (temp-based is optional)
)
```

## Example 2: Carbon Tracking

```python
from simulation import carbon_model

# Calculate emissions with German grid carbon intensity
results_with_carbon, total_emissions_kg, summary = carbon_model.calculate_carbon_emissions(
    simulation_results,
    simulation_start_hour=12.0        # Noon start
)

print(f"Total CO2 emissions: {total_emissions_kg:.2f} kg")
print(f"Carbon intensity by period:\n{summary}")
```

## Example 3: Time-of-Use Pricing

```python
from simulation import cost_model

price_table = cost_model.build_tou_price_table(
    night_price=0.27,
    morning_price=0.44,
    midday_price=0.31,
    evening_peak_price=0.50,
    late_price=0.35
)

results_with_costs, total_cost = cost_model.calculate_time_of_day_costs(
    simulation_results,
    price_table,
    simulation_start_hour=12.0        # Noon start
)
```

---

# Notes on Assumptions

- **PUE**: Assumes 1.3 by default (German HPC centers average)
- **Reactive Power**: Fixed proportional model (Q = 0.33 × P)
- **CPU Power Scaling**: Linear model between idle and full load
- **Carbon Intensity**: Based on typical German grid profile (may vary)
- **Temperature**: Assumes 20°C reference; adjust for specific sites
- **Renewable Fraction**: Configurable; defaults to 50% for German grid

