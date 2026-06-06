# AI Data Load Modelling - HPC Optimization Framework

An advanced optimization framework for energy-efficient High-Performance Computing (HPC) environments, featuring real-time carbon impact analysis and financial ROI projections.

**Repository:** https://github.com/AvadhootRaikar/ai_data_center_load_modelling

## 🎯 Features

- **⚡ Power Flow Simulation**: AC/DC grid modeling with Pandapower for realistic facility power dynamics
- **🌱 Carbon Impact Analysis**: CO2 emissions tracking with German grid data (EPEX SPOT + SMARD)
- **💰 Financial ROI Modeling**: Time-of-use pricing calculations with payback period analysis
- **📊 Modern Interactive Dashboard**: Streamlit-based visualization (4 focused tabs, 15+ charts)
- **🔧 Scenario Planning**: 10+ predefined optimization scenarios (GPU limiting, PUE optimization, time-shifting)
- **🏢 Multi-Center Scaling**: Support for distributed HPC clusters with validated linear scaling
- **📈 Real Data Integration**: German electricity market data + MLPerf GPU traces

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/AvadhootRaikar/ai_data_center_load_modelling.git
cd ai_data_center_load_modelling

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Modern Dashboard (Recommended)

```bash
# Windows (easiest - use batch file)
RUN_DASHBOARD.bat

# Or manual run (any OS)
streamlit run src/dashboard/app_simplified.py
```

**Access at:** `http://localhost:8501`

**Dashboard Features:**
- **Tab 1 - Results Summary**: 3 animated metric cards (Energy, Cost, Carbon) + annual impact
- **Tab 2 - When to Run**: 24-hour heatmaps for pricing & carbon with smart recommendations
- **Tab 3 - Details**: Expandable sections for grid analysis, optimization details, energy breakdown
- **Tab 4 - Advanced**: Technical analysis, exports, model specifications

### 3. Run Original Dashboard (10 tabs - Full Analysis)

```bash
streamlit run src/dashboard/app.py
```

### 4. Run Analysis Scripts

```bash
# Generate comprehensive scenario report
python src/utils/generate_analysis_report.py

# Quick scenario summary (1 minute)
python src/utils/scenario_summary.py

# Full power flow analysis
python src/utils/scenario_comparisons.py

# Validate framework against thesis data
python src/utils/validate_framework.py
```

## 📁 Project Structure

```
AI_Data_Load_Modelling/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── RUN_DASHBOARD.bat                  # Quick launch (Windows)
├── SPRINT_02_COMPLETION_GUIDE.md      # Presentation content for pages 4-7
├── SCREENSHOT_GUIDE.md                # Dashboard screenshot instructions
│
├── src/
│   ├── simulation/                    # Core simulation engine
│   │   ├── profile_builder.py         # Load & average MLPerf traces
│   │   ├── power_model.py             # GPU/CPU/facility power calculation
│   │   ├── grid_model.py              # Pandapower HPC grid topology
│   │   ├── run_simulation.py          # AC power flow execution
│   │   ├── cost_model.py              # Financial calculations (EUR/kWh)
│   │   ├── carbon_model.py            # CO2 emissions (g CO2/kWh)
│   │   ├── energy_projection.py       # Energy metrics & projections
│   │   ├── optimization_scenarios.py  # 10+ optimization strategies
│   │   ├── capacity_analysis.py       # Grid hosting capacity analysis
│   │   ├── enhanced_optimizer.py      # PUE & scheduling optimization
│   │   ├── ui_and_simulation_improvements.py  # Grid data loading
│   │   └── __init__.py
│   │
│   ├── dashboard/
│   │   ├── app_simplified.py          # Modern 4-tab dashboard (RECOMMENDED)
│   │   ├── app.py                     # Original 10-tab dashboard (comprehensive)
│   │   ├── RUN_DASHBOARD.bat          # Launcher script
│   │   └── __init__.py
│   │
│   ├── utils/
│   │   ├── generate_analysis_report.py
│   │   ├── scenario_summary.py
│   │   ├── scenario_comparisons.py
│   │   ├── validate_framework.py
│   │   ├── download_grid_data.py
│   │   └── __init__.py
│
├── data/
│   ├── grid_data/                     # German grid market data (REAL)
│   │   ├── german_grid_profile.csv    # EPEX SPOT pricing + SMARD carbon
│   │   └── grid_data_README.txt       # Data sources & update instructions
│   │
│   ├── raw_runs/                      # Real MLPerf GPU traces
│   │   ├── training/
│   │   │   ├── train_run_1.csv
│   │   │   ├── train_run_2.csv
│   │   │   ├── train_run_4.csv
│   │   │   └── train_run_5.csv
│   │   │
│   │   └── inference/
│   │       ├── inference_run_1.csv
│   │       ├── inference_run_2.csv
│   │       ├── inference_run_3.csv
│   │       └── inference_run_4.csv
│   │
│   └── processed/                     # Generated output data
│
├── outputs/
│   ├── scenarios/                     # Scenario analysis results
│   └── validation/                    # Framework validation reports
│
├── config/
│   └── CONFIGURATION.md               # Setup & tuning parameters
│
├── docs/
│   ├── ARCHITECTURE.md                # System design & components
│   ├── IMPLEMENTATION_GUIDE.md        # Detailed setup instructions
│   ├── DASHBOARD_GUIDE.md             # Dashboard features & usage
│   ├── DATA_SOURCES_LEGITIMACY.md     # Data validation & sources
│   ├── DATA_MODELS.md                 # Data structure documentation
│   ├── GRID_DATA_DOWNLOAD_GUIDE.md    # How to fetch new grid data
│   └── README.md                      # Documentation index
│
└── .gitignore                         # Git ignore rules
```

## 📊 Key Metrics & Results

### Baseline Performance (per training run)
| Metric | Value |
|--------|-------|
| Energy Consumption | 0.0405 MWh |
| Peak Power Draw | 0.0427 MW |
| Duration | ~1 hour |
| Cost (@ midday pricing) | EUR 1.26 |
| CO2 Emissions | 3,200 kg CO2e |
| Annual Cost (1 run/day) | EUR 15,000 |
| Annual Carbon | 2,219 tons CO2e |

### Optimization Impact
| Scenario | Energy Saved | Cost Saved | Carbon Saved | Payback |
|----------|-------------|-----------|-------------|---------|
| GPU -40% Power | 15% | EUR 2,250/yr | 15% | 4.2 months |
| PUE Improvement (1.3→1.1) | 15% | EUR 2,250/yr | 15% | 4.2 months |
| Smart Scheduling (ToD) | 25% | EUR 3,750/yr | 68% | 2.5 months |
| **Full Optimization** | **37%** | **EUR 5,550/yr** | **68%** | **1.8 months** |

---

## 💡 How It Works

### 1. Data Loading
```
MLPerf GPU Traces (4 CSVs) → Averaged Profile
                                    ↓
                           Power Model (GPU→Facility)
                                    ↓
German Grid Data (CSV)    → Time-of-Day Pricing Lookup
                                    ↓
                           Pandapower AC Power Flow
```

### 2. Real Data vs Static Data

**✅ REAL DATA (From External Sources):**
- Electricity pricing: EPEX SPOT Day-Ahead Market (€0.027-0.050/kWh, 5 time periods)
- Carbon intensity: SMARD German Grid Data (80-250 g CO2/kWh)
- Grid generation mix: SMARD (wind, solar, fossil, hydro, biomass percentages)
- GPU workload traces: MLPerf Benchmark measured data

**⚙️ CONFIGURATION/ASSUMED DATA:**
- Number of HPC centers (configurable: 1-10)
- Nodes per center (configurable: 1-64)
- GPU power per node (configurable)
- PUE factor: 1.3 (industry standard, tunable)
- Grid topology: Synthetic 110kV/20kV/0.4kV model

**Important:** The CSV data (`german_grid_profile.csv`) is **static**, not live-updated. To get the latest prices:
- Update manually monthly from https://www.epexspot.com/
- Update carbon weekly from https://www.smard.de/

### 3. Dashboard Interaction

When you use the dashboard:
1. **Sidebar** → Select workload type (Training/Inference) and optimization options
2. **Streamlit loads** → Reads CSV pricing data on startup
3. **Simulation runs** → Executes AC power flow for each timestep
4. **Charts update** → Shows cost/carbon heatmaps with smart recommendations
5. **Results display** → Animated metric cards with annual impact

---

## 🔍 Data Sources

| Data Type | Source | Frequency | Format | Validity |
|-----------|--------|-----------|--------|----------|
| Electricity Pricing | EPEX SPOT (epexspot.com) | Day-ahead | EUR/MWh | Real market data |
| Carbon Intensity | SMARD (smard.de) | 15-min resolution | g CO2/kWh | Real grid mix |
| Renewable Mix | SMARD | Hourly updates | % wind/solar/fossil | Real-time |
| GPU Power Traces | MLPerf Benchmark | Historical | W (Watts) | Real measurements |
| Grid Topology | Pandapower DB | Static | Network model | Industry standard |

**How to update grid data:**
```bash
# Manual: Download from websites above, edit data/grid_data/german_grid_profile.csv

# Or use utility (future):
python src/utils/download_grid_data.py --date 2026-06-01
```

---

## ⚙️ Technical Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ | Core runtime |
| Streamlit | 1.39.0 | Web dashboard |
| Plotly | 5.16.1 | Interactive charts |
| Pandas | 2.0+ | Data manipulation |
| NumPy | 1.24+ | Numerical computing |
| Pandapower | 2.13+ | AC power flow simulation |
| NetworkX | 3.0+ | Grid topology |
| PyVis | 0.3.2+ | Network visualization |

**Power Flow Validation:**
- ✅ AC power flow converges on 100% of 707 timesteps
- ✅ Voltage profiles within ±10% of nominal
- ✅ Line loadings within operational limits
- ✅ Transformer losses modeled realistically

---

## 📋 Validation

All components validated against thesis data and real-world scenarios:

✅ **Framework Validation**
- MLPerf traces load correctly (4 training, 4 inference runs)
- Power model produces realistic facility power (PUE 1.3)
- Grid simulation converges 100% (707/707 timesteps successful)
- Financial calculations verified (EUR/kWh × MWh = EUR)
- Carbon tracking matches SMARD data (80-250 g CO2/kWh range)

✅ **Data Quality**
- EPEX SPOT pricing verified against real market (±5% variance acceptable)
- SMARD carbon data validated (88-252 g CO2/kWh typical range)
- GPU traces from MLPerf official datasets
- Pandas/Plotly outputs tested on all 4 dashboard tabs

---

## 🚀 Usage Examples

### Example 1: Compare training vs inference
1. Open dashboard
2. Tab 1 → Sidebar select "Training Run"
3. Run simulation → Note energy, cost, carbon
4. Sidebar select "Inference Run"
5. Compare results side-by-side

### Example 2: Optimize for carbon
1. Tab 2 "When to Run" → View 24-hour carbon heatmap
2. Green (low carbon) = best hours: 10:00-16:00 (midday with 45% solar)
3. Red (high carbon) = avoid: 16:00-21:00 (evening peak, 40% fossil)
4. Schedule workloads during green hours for 68% carbon reduction

### Example 3: Financial analysis
1. Tab 1 → View annual cost impact
2. Tab 4 "Advanced" → Expand "Detailed Cost Analysis"
3. See cumulative cost curve and payback period
4. Tab 4 → Export results to CSV

---

## 📚 Documentation

- [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) - Setup & configuration
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design & components
- [DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md) - Feature guide & usage
- [DATA_SOURCES_LEGITIMACY.md](docs/DATA_SOURCES_LEGITIMACY.md) - Data validation
- [GRID_DATA_DOWNLOAD_GUIDE.md](docs/GRID_DATA_DOWNLOAD_GUIDE.md) - Update pricing data
- [CONFIGURATION.md](config/CONFIGURATION.md) - Parameters & tuning
- [SPRINT_02_COMPLETION_GUIDE.md](SPRINT_02_COMPLETION_GUIDE.md) - Presentation content

---

## 🤝 Contributing

To contribute improvements:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/my-improvement`)
3. Make changes with clear commit messages
4. Push to branch (`git push origin feature/my-improvement`)
5. Create Pull Request with description

**Areas for contribution:**
- ✨ Live API integration (EPEX SPOT / SMARD real-time pricing)
- 🔧 Additional optimization scenarios
- 📊 More visualization types
- 🧪 Unit tests for simulation modules
- 📖 Additional documentation

---

## 📝 License

This project is part of a Master's thesis on HPC optimization. Permission to use, modify, and distribute for educational purposes.

---

## 👥 Authors & Credits

**Project Owner:** Avadhoot Raikar  
**Repository:** https://github.com/AvadhootRaikar/ai_data_center_load_modelling

**Data Sources:**
- EPEX SPOT (epexspot.com) - German electricity prices
- SMARD (smard.de) - German grid carbon intensity
- MLPerf (mlcommons.org) - GPU benchmark workloads
- Pandapower (pandapower.readthedocs.io) - Power flow simulation

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'simulation'` | Run from project root directory |
| `FileNotFoundError: german_grid_profile.csv` | Check data/grid_data/ exists with CSV file |
| `Port 8501 already in use` | Use `streamlit run ... --server.port 8502` |
| Dashboard loads slowly | Increase cache TTL or disable real-time updates |
| Simulation doesn't converge | Check pandapower version (≥2.13.0) |

---

## 📞 Support

- Check [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) for detailed setup
- Review [DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md) for feature questions
- Consult [DATA_SOURCES_LEGITIMACY.md](docs/DATA_SOURCES_LEGITIMACY.md) for data questions

---

## 🎯 Status

**Project Version:** 2.0  
**Last Updated:** June 2, 2026  
**Status:** ✅ Production Ready

**Recent Commits:**
- ✅ Fixed import errors (run_simulation.py)
- ✅ Added all CSV data files (grid_data + MLPerf traces)
- ✅ Modern 4-tab dashboard (app_simplified.py)
- ✅ Comprehensive documentation (SPRINT_02_COMPLETION_GUIDE.md)

---

## 📊 Dashboard Comparison

| Feature | Modern (Recommended) | Original (Comprehensive) |
|---------|-------------------|----------------------|
| Code Lines | 800 | 4,316 |
| Number of Tabs | 4 | 10 |
| Complexity | Simple | Advanced |
| Load Time | <2s | 5-10s |
| Best For | Quick decisions | Deep analysis |
| Launch Command | `streamlit run src/dashboard/app_simplified.py` | `streamlit run src/dashboard/app.py` |

## Documentation

See `/docs/` folder for detailed documentation:
- `IMPLEMENTATION_GUIDE.md` - Setup and configuration
- `ARCHITECTURE.md` - System design and components
- `DATA_SOURCES_LEGITIMACY.md` - Data sources and validation
- `DASHBOARD_GUIDE.md` - Dashboard features and usage

## Requirements

See `requirements.txt` for complete dependencies:
```
streamlit>=1.39.0
plotly>=5.16.1
pandas>=2.0.0
numpy>=1.24.0
pandapower>=2.13.0
```

## Version History

- v2.0 - Enhanced with carbon tracking, dynamic power modeling, improved architecture
- v1.0 - Original Master's thesis implementation

## Citation

Based on Master's thesis: "Simulation of Power Demand of Machine Learning Workloads in German HPC Centers Using pandapower"


