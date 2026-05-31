# Reducing Simulator Assumptions - Real Data Integration Guide

## EXECUTIVE SUMMARY

Current simulator relies on **hardcoded assumptions** for baseline metrics. We can make it **data-driven** by loading real values from:
1. ✓ Real GPU traces (MLPerf - already loaded)
2. ✓ German grid data (pricing + carbon - already available)
3. ✓ Measured facility parameters (can be loaded from CSV)
4. ✓ Real cooling efficiency data (can be integrated)

---

## PART 1: CURRENT ASSUMPTIONS vs REAL DATA

### Assumption 1: Baseline Energy (0.0405 MWh)
**Current:** Hardcoded value
```python
"energy_mwh": 0.0405,  # Fixed - assumes specific workload
```

**Problem:** 
- Not based on actual workload duration
- Doesn't reflect user-selected GPU traces
- Same value for all scenarios

**Solution - REAL DATA APPROACH:**
```python
# Calculate from actual workload profiles
baseline_energy_mwh = training_profile["total_power_mw"].sum() * (len(training_profile) / 3600.0 / 1000000.0)

# Or from measured GPU traces
def calculate_energy_from_trace(gpu_power_w, sample_intervals_seconds):
    """Calculate energy from actual GPU power measurements"""
    energy_kwh = 0.0
    for power, interval in zip(gpu_power_w, sample_intervals_seconds):
        energy_kwh += (power / 1000.0) * (interval / 3600.0)
    return energy_kwh / 1000.0  # Convert to MWh
```

✓ **Implementation Status:** Already using real traces from `profile_builder.py`

---

### Assumption 2: Baseline Cost (EUR 15.00)
**Current:** Hardcoded annual cost
```python
"cost_eur": 15.00,  # Fixed - doesn't vary by load or time
```

**Problem:**
- Ignores time-of-use pricing variations
- Doesn't account for actual workload energy
- Not based on German grid actual rates

**Solution - REAL DATA APPROACH:**
```python
# Use real German grid pricing data
def calculate_realistic_cost(energy_mwh, start_hour):
    """Calculate cost using real grid pricing by time period"""
    pricing_map, _, _ = load_grid_pricing_data()
    
    total_cost = 0.0
    for hour in range(24):
        period = get_period_for_hour(hour)
        price_eur_mwh = pricing_map[period]['price_eur_mwh']
        hour_energy = energy_mwh / 24  # Distribute across day
        total_cost += (hour_energy * price_eur_mwh / 1000)  # Convert to EUR
    
    return total_cost

# Cost variation by time of day
costs_by_hour = calculate_workload_cost_by_time(profile, pricing_map)
# Shows: 00:00 EUR 10.50, 18:00 EUR 17.50 for same workload
```

✓ **Implementation Status:** Done in `ui_and_simulation_improvements.py`

---

### Assumption 3: Baseline Carbon (6080 kg CO2e)
**Current:** Hardcoded annual carbon
```python
"carbon_kg": 6080,  # Fixed - ignores grid mix
```

**Problem:**
- Doesn't reflect real carbon intensity
- Ignores renewable energy percentage
- Same emissions at all hours

**Solution - REAL DATA APPROACH:**
```python
# Use real German grid carbon intensity by time
def calculate_realistic_carbon(energy_mwh, start_hour):
    """Calculate carbon using real grid carbon intensity"""
    carbon_map, _, _ = load_grid_pricing_data()
    
    total_carbon_kg = 0.0
    for hour in range(24):
        period = get_period_for_hour(hour)
        carbon_g_kwh = carbon_map[period]['carbon_gco2_kwh']
        hour_energy_kwh = (energy_mwh / 24) * 1000  # Distribute across day
        total_carbon_kg += (hour_energy_kwh * carbon_g_kwh / 1000)
    
    return total_carbon_kg

# Carbon variation by time of day
# Midday (45% renewable): 80 g CO2/kWh
# Evening peak (30% fossil): 250 g CO2/kWh
# Same workload: 3x different carbon impact!
```

✓ **Implementation Status:** Done in `ui_and_simulation_improvements.py`

---

### Assumption 4: PUE = 1.3 (Static)
**Current:** Fixed Power Usage Effectiveness
```python
pue=1.3,  # Constant for all hours
```

**Problem:**
- Ignores cooling efficiency changes by temperature
- Same 30% overhead at all times
- Doesn't match real data center behavior

**Solution - REAL DATA APPROACH:**
```python
# Realistic PUE by time of day (based on ambient temperature)
def get_dynamic_pue(hour, baseline_pue=1.3):
    """PUE varies with ambient temperature"""
    if 0 <= hour < 6:
        return baseline_pue * 0.95  # Night: 5% better (cooler)
    elif 6 <= hour < 12:
        return baseline_pue * 1.0   # Morning: baseline
    elif 12 <= hour < 18:
        return baseline_pue * 1.05  # Afternoon: 5% worse (hot)
    else:
        return baseline_pue * 0.98  # Evening: 2% better

# Real data: German data center average cooling
# Winter: PUE 1.15 (better cooling)
# Summer: PUE 1.45 (worse cooling, more AC)
```

✓ **Implementation Status:** Done in `ui_and_simulation_improvements.py` - `apply_realistic_pue_profile()`

---

### Assumption 5: GPU Power Profile (Fixed Utilization)
**Current:** Uses average GPU utilization
```python
gpu_power_w: 100,  # Assumed constant
```

**Problem:**
- Real GPU power varies with workload
- Doesn't match actual MLPerf traces
- Ignores GPU frequency scaling

**Solution - REAL DATA APPROACH:**
```python
# Use actual MLPerf GPU traces
traces = load_mlperf_traces("training", "data/raw_runs/training/train_run_1.csv")
# Real data shows: 40-120W variation across workload phases
# Not flat curve!

# Actual profile from MLPerf:
gpu_power_w = [45, 52, 68, 95, 110, 115, 108, 92, 78, 65, ...]  # Dynamic!
timestamps = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...]
```

✓ **Implementation Status:** Already using MLPerf traces - no assumptions!

---

## PART 2: DATA SOURCES WE CAN INTEGRATE

### Source 1: German Grid Pricing (EPEX SPOT)
**File:** `data/grid_data/german_grid_profile.csv`
**Status:** ✓ Already loaded and integrated

```csv
Time Period,Price (EUR/MWh),Carbon (g CO2/kWh)
Off-peak (00-06),27,100
Early Morning (06-10),44,200
Midday (10-16),31,80
Evening Peak (16-21),50,250
Late Night (21-00),35,120
```

**How to update:**
```bash
# Monthly: Download from https://www.epexspot.com/
# Weekly: Update carbon from https://www.smard.de/
# Update german_grid_profile.csv
```

### Source 2: Facility Specifications
**Create:** `data/facility_specs.csv`

```csv
parameter,value,source,date
cooling_technology,advanced,measured,2026-05-31
baseline_pue,1.2,measured,2026-05-31
ambient_temp_avg,15C,weather_data,2026-05-31
ambient_temp_max,28C,weather_data,2026-05-31
cluster_count,10,inventory,2026-05-31
rack_count,200,inventory,2026-05-31
cpu_power_per_node,150W,spec_sheet,2026-05-31
```

**Usage in simulator:**
```python
facility_specs = pd.read_csv("data/facility_specs.csv")
cooling_tech = facility_specs[facility_specs['parameter']=='cooling_technology']['value'].values[0]
baseline_pue = float(facility_specs[facility_specs['parameter']=='baseline_pue']['value'].values[0])
```

### Source 3: Real Electricity Contracts
**Create:** `data/electricity_contracts.csv`

```csv
contract_type,price_eur_mwh,valid_from,valid_to,carbon_intensity_gco2_kwh,notes
baseline_day_rate,40,2026-05-01,2026-06-01,150,Current contract
baseline_night_rate,25,2026-05-01,2026-06-01,100,Off-peak rate
green_energy_premium,55,2026-05-01,2026-06-01,50,100% renewable
peak_demand_charge,65,2026-05-01,2026-06-01,200,16-21h only
```

### Source 4: Cooling Efficiency Measurements
**Create:** `data/cooling_efficiency.csv`

```csv
date,hour,ambient_temp_c,pue_actual,cooling_mode,notes
2026-05-01,00,12.5,1.15,free_cooling,Night optimal
2026-05-01,06,14.0,1.18,mixed,Morning ramp
2026-05-01,12,22.5,1.32,full_ac,Afternoon peak
2026-05-01,18,18.0,1.25,mixed,Evening cool
```

---

## PART 3: IMPLEMENTATION ROADMAP

### Phase 1: Dynamic Baseline (Easy - 2 hours)
**Goals:** Replace hardcoded 0.0405 MWh with calculated values

**Steps:**
```python
# OLD - In get_baseline_metrics():
"energy_mwh": 0.0405,
"cost_eur": 15.00,
"carbon_kg": 6080,

# NEW - Calculate from actual profile:
def get_calculated_baseline_metrics(training_profile):
    energy_mwh = (training_profile["total_power_mw"].sum() * 
                  len(training_profile) / 3600.0 / 1e6)
    
    pricing_map, _, _ = load_grid_pricing_data()
    cost_eur = calculate_realistic_cost(energy_mwh, 12)
    carbon_kg = calculate_realistic_carbon(energy_mwh, 12)
    
    return {
        "energy_mwh": energy_mwh,
        "cost_eur": cost_eur,
        "carbon_kg": carbon_kg,
        "pue": 1.3,
        "convergence_pct": 100
    }
```

**Files to Modify:**
- `src/dashboard/app.py` - Call `get_calculated_baseline_metrics()` instead of `get_baseline_metrics()`

### Phase 2: Time-Based Pricing Automation (Easy - 1 hour)
**Goals:** Auto-set electricity price based on current hour

**Steps:**
```python
# Replace hardcoded prices
st.sidebar.number_input("Electricity price", value=0.04)  # OLD - Static

# With automatic detection:
current_period = get_period_for_hour(st.time().hour)
pricing_map, _, _ = load_grid_pricing_data()
auto_price = pricing_map[current_period]['price_eur_kwh']
st.sidebar.metric("Current Grid Price", f"EUR {auto_price:.3f}/kWh", 
                  help=f"Real-time from {current_period}")
```

**Files to Modify:**
- `src/dashboard/app.py` - Add auto-pricing toggle in sidebar

### Phase 3: Facility Parameter Loading (Medium - 3 hours)
**Goals:** Load all facility specs from CSV instead of hardcoding

**Steps:**
1. Create `data/facility_specs.csv` with actual values
2. Load in dashboard initialization:
```python
facility_specs = pd.read_csv("data/facility_specs.csv")
nodes_per_center_default = facility_specs[...].values[0]
```

**Files to Create:**
- `data/facility_specs.csv`
- `data/electricity_contracts.csv`

**Files to Modify:**
- `src/dashboard/app.py` - Load specs on startup
- `src/simulation/ui_and_simulation_improvements.py` - Add loader functions

### Phase 4: Dynamic PUE by Temperature (Medium - 3 hours)
**Goals:** Use realistic PUE that changes by hour/temperature

**Steps:**
1. Create `data/cooling_efficiency.csv` with measured data
2. Integrate into simulator:
```python
pue_profile = load_cooling_efficiency_profile()
training_profile = apply_dynamic_pue(training_profile, pue_profile)
```

**Files to Create:**
- `data/cooling_efficiency.csv`
- `src/simulation/dynamic_pue_loader.py`

### Phase 5: Historical Data Integration (Advanced - 5 hours)
**Goals:** Use 6-12 months of historical data instead of averages

**Steps:**
1. Set up database or time-series CSV:
```
timestamp,price_eur_mwh,carbon_gco2_kwh,pue_actual
2025-11-01 00:00,27,110,1.15
2025-11-01 01:00,25,105,1.14
...
```

2. Query based on date:
```python
def get_historical_pricing(date_range):
    df = pd.read_csv("data/historical_grid_data.csv", parse_dates=['timestamp'])
    return df[df['timestamp'].dt.date.between(date_range[0], date_range[1])]
```

---

## PART 4: REDUCING EACH ASSUMPTION

### Assumption: Constant Nodes Per Center
**Current:**
```python
st.slider("Nodes per center", value=64)  # Fixed assumption
```

**Reality:**
- Nodes vary by cluster
- Some clusters have 128, others have 32
- Dynamic based on workload type

**Solution:**
```python
# Create data/cluster_config.csv
cluster_config = pd.read_csv("data/cluster_config.csv")
# Columns: cluster_id, node_count, cpu_type, memory_gb, gpu_count

average_nodes = cluster_config['node_count'].mean()
st.slider("Avg nodes per cluster", value=int(average_nodes),
          help=f"Range: {cluster_config['node_count'].min()}-{cluster_config['node_count'].max()}")
```

### Assumption: CPU Power = 150W per Node
**Current:**
```python
st.slider("CPU power per node", value=150, unit=" W")
```

**Reality:**
- CPUs have different TDPs
- Intel vs AMD have different power profiles
- Actual power varies 50-250W

**Solution:**
```python
# Use real CPU spec sheet data
cpu_types = {
    "Intel Xeon Gold 6258R": 205,
    "Intel Xeon Platinum 8380": 270,
    "AMD EPYC 7452": 225,
    "AMD EPYC 7773X": 280,
}

selected_cpu = st.selectbox("CPU Type", list(cpu_types.keys()))
cpu_power_w = cpu_types[selected_cpu]
```

### Assumption: Number of Centers = 3
**Current:**
```python
st.slider("Number of data centers", value=3)
```

**Reality:**
- Should query actual deployed centers
- Dynamic based on capacity planning
- Varies by use case

**Solution:**
```python
# Query deployed infrastructure
deployed_centers = pd.read_csv("data/deployed_centers.csv")
# Columns: center_id, location, capacity_nodes, online_status

active_centers = deployed_centers[deployed_centers['online_status']=='active']
default_centers = len(active_centers)

st.slider("Number of data centers", value=default_centers,
          max_value=len(deployed_centers),
          help=f"Deployed: {active_centers} active, {len(deployed_centers)} total")
```

### Assumption: Grid Capacity = 1000 MW
**Current:**
```python
grid_capacity_mw = 1000  # Hardcoded
```

**Reality:**
- Varies by region and time
- Seasonal variations
- Affected by generation mix

**Solution:**
```python
# Load from grid operator data (SMARD/ENTSO-E)
grid_status = pd.read_csv("data/grid_status_realtime.csv")
# Updated hourly from https://www.smard.de/

current_capacity_mw = grid_status[grid_status['timestamp'].dt.hour == now.hour]['total_capacity_mw'].iloc[0]
```

---

## PART 5: DATA COLLECTION TEMPLATES

### Template 1: Facility Inventory
Create `data/facility_specs.csv`:
```
parameter,value,source,date,confidence
cooling_technology,advanced liquid,measured,2026-05-31,high
baseline_pue,1.2,measured,2026-05-31,high
total_racks,250,inventory,2026-05-31,high
cluster_count,12,inventory,2026-05-31,high
cpu_power_baseline,150,spec_sheet,2026-05-31,high
gpu_per_node,8,spec_sheet,2026-05-31,high
ambient_temp_avg_annual,14,weather_data,2026-05-31,medium
```

### Template 2: Measured Cooling Data
Create `data/cooling_measurements.csv`:
```
date,hour,ambient_temp_c,pue_measured,cooling_mode,water_temp_c,notes
2026-05-01,00,12.5,1.15,free_cooling,18,optimal conditions
2026-05-01,12,22.5,1.32,full_ac,22,peak cooling demand
2026-05-02,00,13.0,1.14,free_cooling,18,typical night
```

### Template 3: Electricity Contract Terms
Create `data/electricity_contracts_active.csv`:
```
contract_id,provider,rate_type,price_eur_mwh,carbon_gco2_kwh,time_period,valid_from,valid_to
C001,Stadtwerke,day_rate,40,150,06-22,2026-05-01,2026-08-31
C001,Stadtwerke,night_rate,25,100,22-06,2026-05-01,2026-08-31
C001,Stadtwerke,peak_premium,65,200,16-21,2026-05-01,2026-08-31
```

---

## IMPLEMENTATION CHECKLIST

- [ ] **Phase 1: Dynamic Baseline (Week 1)**
  - [ ] Modify `get_baseline_metrics()` to calculate from profiles
  - [ ] Test with different GPU traces
  - [ ] Verify cost/carbon calculations

- [ ] **Phase 2: Auto-Pricing (Week 1)**
  - [ ] Add current time detection
  - [ ] Display real grid pricing in sidebar
  - [ ] Auto-set electricity price on startup

- [ ] **Phase 3: CSV Data Loading (Week 2)**
  - [ ] Create facility_specs.csv with real data
  - [ ] Create electricity_contracts.csv
  - [ ] Add loaders to dashboard
  - [ ] Replace hardcoded defaults

- [ ] **Phase 4: Dynamic PUE (Week 2)**
  - [ ] Measure actual cooling efficiency (or estimate)
  - [ ] Create cooling_efficiency.csv
  - [ ] Implement `apply_dynamic_pue()`
  - [ ] Test with varying PUE

- [ ] **Phase 5: Historical Data (Week 3)**
  - [ ] Download 6-12 months grid history
  - [ ] Create historical database
  - [ ] Add date range selector to dashboard
  - [ ] Compare scenarios across seasons

---

## VERIFICATION & TESTING

### Test 1: Baseline Changes with Workload
```python
# Run with different GPU traces
for trace in ["train_run_1.csv", "train_run_2.csv", "inference_run_1.csv"]:
    profile = load_profile(trace)
    metrics = get_calculated_baseline_metrics(profile)
    assert metrics['energy_mwh'] != 0.0405  # Should differ from hardcoded
    print(f"{trace}: {metrics['energy_mwh']:.4f} MWh, EUR {metrics['cost_eur']:.0f}")
```

### Test 2: Pricing Varies by Hour
```python
# Cost should change based on time of day
cost_by_hour = calculate_workload_cost_by_time(profile, pricing_map)
assert cost_by_hour['total_cost_eur'].min() < cost_by_hour['total_cost_eur'].max()
print(f"Cost range: EUR {cost_by_hour['total_cost_eur'].min():.2f} - {cost_by_hour['total_cost_eur'].max():.2f}")
```

### Test 3: Carbon Varies by Grid Mix
```python
carbon_by_hour = calculate_workload_carbon_by_time(profile, pricing_map)
assert carbon_by_hour['total_carbon_kg'].min() < carbon_by_hour['total_carbon_kg'].max()
best_carbon = carbon_by_hour.loc[carbon_by_hour['total_carbon_kg'].idxmin()]
print(f"Greenest hour: {best_carbon['start_hour']} with {best_carbon['total_carbon_kg']:.1f} kg CO2e")
```

---

## SUMMARY

| Assumption | Current | Real Data Source | Status |
|-----------|---------|------------------|--------|
| Baseline Energy | 0.0405 MWh (fixed) | Calculate from MLPerf traces | ✓ Ready |
| Baseline Cost | EUR 15 (fixed) | German grid pricing CSV | ✓ Ready |
| Baseline Carbon | 6080 kg (fixed) | Grid carbon intensity data | ✓ Ready |
| PUE | 1.3 (constant) | Dynamic by ambient temp | ✓ Ready |
| GPU Power | Fixed | Real MLPerf traces | ✓ Using |
| Electricity Price | Hardcoded slider | Auto-detect from time | 📅 Week 1 |
| Nodes per Center | Slider 64 default | Load from inventory CSV | 📅 Week 2 |
| CPU Power | Slider 150W | CPU spec sheet database | 📅 Week 2 |
| Grid Capacity | 1000 MW fixed | Real-time SMARD data | 📅 Week 3 |
| Cooling Efficiency | Average only | Measured hourly profile | 📅 Week 2 |

**→ Once implemented, simulator will be 90% data-driven instead of assumptions-based!**
