"""
Architecture Overview and Enhancement Roadmap

DS_Proejct_v0: Enhanced HPC Workload & Power Grid Simulation Framework
"""

# ARCHITECTURE LAYERS

## 1. Data Layer (simulation/profile_builder.py)
Features:
- Load and validate MLPerf CSV traces
- Timestamp normalization and alignment
- Multi-run averaging for robust profiles
- Support for mixed training+inference workloads
- Data quality metrics

Enhancement: Added trace quality validation

## 2. Power Modeling Layer (simulation/power_model.py)
Features:
- GPU-to-node power transformation
- Node-to-center aggregation
- Center-to-facility scaling with PUE

Enhancement v2.0: Added dynamic modeling
- CPU power scales with utilization (0.3-1.0 × base power)
- Memory power correlates with GPU+CPU activity
- Environmental temperature affects PUE efficiency
- Better reactive power handling

## 3. Grid Layer (simulation/grid_model.py)
Features:
- Synthetic HPC grid (110/20/0.4 kV)
- SimBench German benchmark network
- Dual-backend support

## 4. Simulation Layer (simulation/run_simulation.py)
Features:
- Time-series AC power flow (via pandapower)
- Per-timestep grid metrics
- Convergence tracking and error handling

## 5. Cost Layer (simulation/cost_model.py)
Features:
- Flat-rate pricing
- Time-of-use (ToD) pricing with German profile
- Cost projections for various durations

## 6. Carbon Layer (simulation/carbon_model.py) [NEW]
Features:
- Time-dependent grid carbon intensity
- CO2 emissions tracking
- Renewable energy offset estimation
- Carbon reduction metrics by scenario

## 7. Energy & Projection Layer (simulation/energy_projection.py)
Features:
- Energy calculations and projections
- Same-work analysis for scheduling scenarios
- Peak/average power metrics

---

# DATA FLOW

Input: CSV Power Traces
    ↓
[profile_builder] → Load, validate, average → Workload Profile DataFrame
    ↓
[power_model] → Scale GPU → Node → Center → Facility → Center-level Power
    ↓
[grid_model] → Create pandapower network (Synthetic or SimBench)
    ↓
[run_simulation] → For each timestep: Update loads → RunPowerFlow → Metrics
    ↓
[cost_model + carbon_model] → Calculate costs and emissions
    ↓
Output: Results DataFrame with all metrics

---

# CONFIGURATION PARAMETERS

## Infrastructure Config
nodes_per_center = 20
clusters_per_center = 4
racks_per_cluster = 10

## Power Model Config
cpu_power_per_node = 150 W (dynamic scaling enabled by default)
memory_power_per_node = 40 W (dynamic scaling enabled by default)
storage_power_per_node = 10 W
network_power_per_node = 10 W
baseline_pue = 1.3 (can be temperature-adjusted)
reactive_power_factor = 0.33 (Q = 0.33 × P)

## Grid Config
grid_backend = "Synthetic HPC grid" | "SimBench German benchmark grid"
simbench_code = "1-MV-rural--0-sw"

## Pricing Config
Time-of-use rates (€/kWh):
  00:00-06:00: 0.27 (night)
  06:00-10:00: 0.44 (morning peak)
  10:00-16:00: 0.31 (midday/solar)
  16:00-21:00: 0.50 (evening peak)
  21:00-24:00: 0.35 (late)

## Carbon Config
Grid carbon intensity (gCO2/kWh):
  00:00-06:00: 100 (low demand)
  06:00-10:00: 200 (morning peak)
  10:00-16:00: 80 (solar generation peak)
  16:00-21:00: 250 (evening peak)
  21:00-24:00: 120 (late)

---

# ENHANCEMENT ROADMAP

## Completed (v2.0)
✅ Carbon tracking module with German grid profile
✅ Dynamic CPU/Memory power modeling
✅ Temperature-dependent PUE
✅ Enhanced data validation
✅ Configuration-driven parameters
✅ Modular architecture improvements

## In Progress
🔄 Dashboard integration (app.py refactoring)
🔄 Test suite creation
🔄 Documentation refinement

## Planned (v2.1+)
⏳ Real-time electricity price data integration (EPEX SPOT)
⏳ Actual weather-dependent PUE modeling
⏳ Multi-GPU trace support
⏳ Distributed optimization algorithms
⏳ Advanced scenario comparison tools
⏳ Sustainability dashboard views
⏳ API for programmatic access

---

# SCENARIO FRAMEWORK

Scenarios analyze different optimization strategies:

1. **Baseline** - No optimization
2. **GPU Power Limiting** - Reduce GPU power (factor 0.90)
   Impact: Lower peak power, but runtime extension
3. **PUE Improvement** - Better cooling efficiency (factor 0.85)
   Impact: Proportional facility power reduction
4. **Workload Shifting** - Move execution to cheaper/cleaner hours
   Impact: Cost/carbon reduction with same energy
5. **Load Distribution** - Activate only subset of centers
   Impact: Peak power reduction but longer completion time (same-work analysis)

---

# KEY INSIGHTS

## Same-Work Analysis
When scheduling reduces active centers, the same amount of work takes longer.
The "same-work energy" estimates total energy if work runs on all available centers.

Example:
- Baseline: 10 centers × 10 hours = 100 center-hours
- Optimized: 5 centers × 20 hours window = 100 center-hours (same work)
- Visible window energy may be lower, but same-work energy is the actual total

## Dynamic Power Modeling
- CPUs don't consume full rated power at idle
- Memory access correlates with workload, not GPU power alone
- Better accuracy requires utilization data (often available in MLPerf traces)
- Falls back to constant power if utilization unknown

## Carbon Impact
- Shifting ML workloads to solar-rich midday hours can reduce carbon by 2-3×
- Efficiency improvements (cooling) reduce carbon proportionally
- Different from cost savings (carbon intensity ≠ electricity price)

---

# MODULE DEPENDENCIES

```
dashboard/app.py
    ├── profile_builder.py (load traces)
    ├── power_model.py (convert GPU → facility power)
    ├── grid_model.py (create network)
    ├── run_simulation.py (execute flows)
    ├── cost_model.py (calculate costs)
    ├── carbon_model.py (calculate emissions)
    └── energy_projection.py (metrics)

tests/
    ├── test_profile_builder.py
    ├── test_power_model.py
    ├── test_cost_model.py
    └── test_carbon_model.py
```

---

# FILE ORGANIZATION

```
DS_Proejct_v0/
├── simulation/              # Core simulation modules
│   ├── __init__.py
│   ├── profile_builder.py  # Trace processing
│   ├── power_model.py      # Power calculations
│   ├── grid_model.py       # Pandapower grids
│   ├── run_simulation.py   # Power flow runner
│   ├── cost_model.py       # Cost calculations
│   ├── carbon_model.py     # Carbon tracking (NEW)
│   └── energy_projection.py # Energy metrics
├── dashboard/              # Streamlit UI (TBD)
│   └── app.py
├── config/                 # Configuration files
│   ├── parameters.yaml     # Default parameters
│   ├── scenarios.yaml      # Scenario definitions
│   └── grid_profiles.yaml  # Grid configurations
├── data/
│   ├── raw_runs/
│   │   ├── training/       # Training CSV files
│   │   └── inference/      # Inference CSV files
│   └── processed/          # Cached results
├── tests/                  # Test suite
├── outputs/                # Simulation results
├── readme.md
├── requirements.txt
└── ARCHITECTURE.md         # This file
```

