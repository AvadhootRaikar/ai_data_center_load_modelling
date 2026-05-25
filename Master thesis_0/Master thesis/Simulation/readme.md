# HPC Training Energy Simulation with Pandapower

This project simulates measured MLPerf GPU training workload traces as scalable HPC-center loads and evaluates their grid impact with pandapower.

## What is included

- `Dashboard/app.py` Streamlit dashboard
- `simulation/` modeling and pandapower modules
- `data/raw_runs/training/` four measured MLPerf training CSV files:
  - `train_run_1.csv`
  - `train_run_2.csv`
  - `train_run_4.csv`
  - `train_run_5.csv`
data/raw_runs/inference/` four measured MLPerf inference CSV files:
  - `inference_run_1.csv`
  - `inference_run_2.csv`
  - `inference_run_4.csv`
  - `inference_run_5.csv`

## Input data

The included MLPerf CSV files contain:

- `timestamp`
- `gpu_power_w`
- `gpu_util_percent`
- `total_gpu_power_w`
- `cpu_util_percent`
- `num_gpus`


The app builds a representative trace by aligning the runs, averaging GPU power/utilization, and using real timestamp intervals for energy integration.

## Run

```bash
pip install -r requirements.txt
streamlit run Dashboard/app.py
```

On Windows:

```bash
pip install -r requirements.txt
streamlit run Dashboard\app.py
```

## Default training folder

The sidebar default is:

```text
data/raw_runs/training
```

This works when the app is started from the project root.

## Thesis interpretation

Measured data:
- MLPerf GPU power trace
- GPU utilization
- sample timestamps

Model assumptions:
- CPU/RAM/storage/network power per node
- PUE
- number of nodes/centers
- grid backend and topology
- reactive power factor approximation

Pandapower outputs:
- bus voltages
- line loading and losses
- transformer loading and losses
- external grid supply
- convergence status
