"""
Implementation Guide for Enhanced Framework

Getting Started with DS_Proejct_v0
"""

# QUICK START GUIDE

## 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pandapower, streamlit, pandas; print('OK')"
```

## 2. Basic Workflow

```python
from simulation import profile_builder, power_model, run_simulation, cost_model, carbon_model
import pandas as pd

# Step 1: Load and process traces
profile = profile_builder.build_measured_profile(
    "data/raw_runs/training/",
    workload_label="Training"
)

# Step 2: Convert to facility-level power
facility_profile = power_model.convert_training_profile_to_center(
    profile,
    nodes_per_center=20,
    dynamic_cpu_power=True,      # NEW: Dynamic modeling
    dynamic_memory_power=True
)

# Step 3: Run power flow simulation
sim_results = run_simulation.run_hpc_simulation(
    facility_profile,
    number_of_centers=3,
    grid_backend="Synthetic HPC grid"
)

# Step 4: Calculate costs
cost_table = cost_model.build_tou_price_table()
sim_with_costs, total_cost = cost_model.calculate_time_of_day_costs(
    sim_results,
    cost_table,
    simulation_start_hour=12.0
)

# Step 5: Calculate carbon emissions (NEW)
sim_with_carbon, total_emissions, summary = carbon_model.calculate_carbon_emissions(
    sim_with_costs,
    simulation_start_hour=12.0
)

print(f"Total Cost: €{total_cost:.2f}")
print(f"Total Emissions: {total_emissions:.2f} kg CO2")
```

---

# KEY IMPROVEMENTS IN v2.0

## 1. Dynamic Power Modeling

**Before (v1.0):**
```python
# Static CPU power regardless of utilization
node_power = gpu_power + 150 + 40 + storage + network
```

**After (v2.0):**
```python
# CPU and memory scale with utilization
cpu_power = 150 × (0.3 + 0.7 × cpu_util%)  # 45-150 W range
memory_power = 40 × (0.5 + 0.5 × avg_util%)  # 20-40 W range
node_power = gpu_power + cpu_power + memory_power + storage + network

# More accurate representation of real hardware behavior
```

**Impact:**
- More realistic power profiles when utilization data available
- Better accuracy for optimization scenarios
- Graceful fallback to static model when utilization unknown

## 2. Carbon Tracking

**New Capability:**
```python
# Track grid carbon intensity by time-of-day
# German grid: 80 gCO2/kWh at solar peak, 250 gCO2/kWh at evening peak

# Identify optimal scheduling windows
results_carbon, emissions, summary = carbon_model.calculate_carbon_emissions(
    sim_results,
    simulation_start_hour=12.0  # Shift to midday (80 g/kWh) vs evening (250 g/kWh)
)

# Potential 2-3× carbon reduction through scheduling
```

**Environmental Benefits:**
- Quantify sustainability impact
- Identify low-carbon execution windows
- Support corporate ESG reporting

## 3. Enhanced Configuration

**Centralized Parameters:**
- All tuning in `config/CONFIGURATION.md`
- No hardcoded values in code
- Easy sensitivity analysis

```python
# Example: Sensitivity analysis on PUE
for pue in [1.1, 1.3, 1.5]:
    profile = power_model.convert_training_profile_to_center(
        workload,
        pue=pue
    )
    results = run_simulation.run_hpc_simulation(profile, ...)
    print(f"PUE {pue}: {results['total_power_mw'].max():.2f} MW peak")
```

## 4. Modular Architecture

**Clear Separation of Concerns:**
- `profile_builder.py` - Only handles trace processing
- `power_model.py` - Only handles power calculations
- `grid_model.py` - Only handles grid topology
- `run_simulation.py` - Only handles power flow
- `cost_model.py` - Only handles economics
- `carbon_model.py` - Only handles sustainability

**Advantages:**
- Easy to test each module independently
- Easy to replace/upgrade individual components
- Clear documentation of inputs/outputs
- Facilitates future enhancements

---

# NEXT STEPS

## Phase 1: Validation (This Week)
- [ ] Load sample MLPerf traces from Master thesis data
- [ ] Verify simulations run without errors
- [ ] Compare baseline results with thesis findings
- [ ] Document any discrepancies

## Phase 2: Dashboard Integration (This Sprint)
- [ ] Copy/adapt Streamlit app.py
- [ ] Add new carbon tracking visualizations
- [ ] Update parameter sidebar with configuration options
- [ ] Create scenario comparison table

## Phase 3: Testing (Next Sprint)
- [ ] Unit tests for profile_builder (trace validation)
- [ ] Unit tests for power_model (scaling equations)
- [ ] Unit tests for cost_model (ToD pricing)
- [ ] Unit tests for carbon_model (emission calculations)
- [ ] Integration tests (end-to-end workflow)

## Phase 4: Documentation (Ongoing)
- [ ] Docstring completion
- [ ] API documentation
- [ ] Tutorial notebooks
- [ ] Scenario guides

## Phase 5: Features (Future)
- [ ] Real EPEX SPOT price data integration
- [ ] Live weather data for temperature-dependent PUE
- [ ] Multi-GPU trace support
- [ ] Distributed optimization algorithms

---

# TROUBLESHOOTING

## Import Errors

```bash
# pandapower not found
pip install pandapower

# simbench not found (optional, for SimBench grids)
pip install simbench

# networkx or pyvis missing
pip install networkx pyvis
```

## Power Flow Convergence Issues

```python
# Check for unrealistic loads
print(sim_results[sim_results['converged'] == False])

# Reduce simulation speed (longer timesteps)
# or use DC power flow instead of AC (fast_mode=True)
```

## Memory Issues with Large Traces

```python
# Process traces in chunks
chunk_size = 1000  # samples per chunk
profile_chunks = [profile[i:i+chunk_size] for i in range(0, len(profile), chunk_size)]

for chunk in profile_chunks:
    results = run_simulation.run_hpc_simulation(chunk, ...)
    results.to_csv(f"output/results_chunk_{i}.csv")
```

---

# PERFORMANCE TIPS

## Optimization Order (fastest to slowest)
1. **Fast Mode** - DC power flow (10-100× faster than AC)
2. **Fewer Centers** - Reduces grid size
3. **Coarser Timesteps** - Fewer iterations needed
4. **Simpler Grid** - Synthetic vs SimBench

Example: Quick sensitivity analysis
```python
results_fast = run_simulation.run_hpc_simulation(
    profile,
    number_of_centers=1,
    fast_mode=True  # DC power flow
)
# Runs in seconds instead of minutes
```

## Caching Strategy

```python
# Cache expensive computations
import joblib

cache_file = "cache/profile_result.pkl"
if os.path.exists(cache_file):
    facility_profile = joblib.load(cache_file)
else:
    facility_profile = power_model.convert_training_profile_to_center(...)
    joblib.dump(facility_profile, cache_file)
```

---

# COMMON CUSTOMIZATIONS

## Using Different Grid

```python
# SimBench instead of synthetic
results = run_simulation.run_hpc_simulation(
    profile,
    grid_backend="SimBench German benchmark grid",
    simbench_code="1-MV-rural--0-sw"  # Change grid code
)
```

## Custom Time-of-Use Pricing

```python
# Your own tariff
price_table = cost_model.build_tou_price_table(
    night_price=0.25,      # Your rates
    morning_price=0.40,
    midday_price=0.28,
    evening_peak_price=0.48,
    late_price=0.32
)
results, cost = cost_model.calculate_time_of_day_costs(
    sim_results,
    price_table
)
```

## Custom Carbon Intensity

```python
# Different grid carbon profile (e.g., coal-heavy region)
carbon_table = carbon_model.build_german_carbon_intensity_profile(
    night_intensity=150,
    morning_intensity=250,
    midday_intensity=150,     # Less solar in this region
    evening_intensity=300,
    late_intensity=150
)
results, emissions, summary = carbon_model.calculate_carbon_emissions(
    sim_results,
    carbon_table
)
```

---

# EXTENDING THE FRAMEWORK

## Adding a New Scenario

1. Create scenario function in `optimization_scenarios.py`
2. Modify workload profile with scenario parameters
3. Run simulation on modified profile
4. Compare against baseline

Example:
```python
def apply_demand_response_scenario(profile, reduction_hours):
    """Reduce power during specific hours."""
    profile = profile.copy()
    in_window = (profile['elapsed_hours'] >= reduction_hours[0]) & \
                (profile['elapsed_hours'] <= reduction_hours[1])
    profile.loc[in_window, 'center_total_power_mw'] *= 0.8  # 20% reduction
    return profile
```

## Adding a New Power Model

1. Create function in `power_model.py`
2. Document assumptions clearly
3. Add unit tests in `tests/`
4. Update `ARCHITECTURE.md`

Example:
```python
def calculate_gpu_power_with_frequency_scaling(
    base_gpu_power, frequency_ratio, power_law_exponent=3.0
):
    """Dynamic Voltage and Frequency Scaling (DVFS) model."""
    return base_gpu_power * (frequency_ratio ** power_law_exponent)
```

---

# FEEDBACK & IMPROVEMENTS

Track enhancement requests and issues in `docs/ISSUES.md`:

```
## Issue: Reactive power model too simplistic
**Description**: Q = 0.33 × P assumes fixed power factor
**Suggested Fix**: Make power factor load-dependent
**Priority**: Medium
**Owner**: TBD

## Enhancement: Multi-site simulation
**Description**: Support multi-site coordination scenarios
**Suggested Implementation**: Add site ID to results
**Priority**: Low
**Owner**: TBD
```

