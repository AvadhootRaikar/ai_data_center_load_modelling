"""
AI Data Center Load Modelling — FastAPI Server
=============================================
Drop this file into your project root and run:
  uvicorn fastapi_server.main:app --reload --port 8000

The frontend reads NEXT_PUBLIC_API_URL=http://localhost:8000 from .env.local
and automatically falls back to mock data when this server is offline.

Adjust the imports below to match the exact module paths in your repo.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Import your simulation modules
# Adjust these paths to match your project structure, e.g.:
#   from AI_Data_Load_Modelling.src.simulation.run_simulation import run_full_simulation
# ---------------------------------------------------------------------------
try:
    from AI_Data_Load_Modelling.src.simulation.run_simulation import run_full_simulation
    from AI_Data_Load_Modelling.src.simulation.power_model import PowerModel
    from AI_Data_Load_Modelling.src.simulation.cost_model import CostModel
    from AI_Data_Load_Modelling.src.simulation.carbon_model import CarbonModel
    from AI_Data_Load_Modelling.src.simulation.water_model import WaterModel
    from AI_Data_Load_Modelling.src.simulation.optimization_scenarios import run_all_scenarios
    from AI_Data_Load_Modelling.src.simulation.energy_projection import EnergyProjection
    from AI_Data_Load_Modelling.src.simulation.smard_api_integration import SmardApiClient
    from AI_Data_Load_Modelling.src.simulation.profile_builder import ProfileBuilder
    MODULES_LOADED = True
except ImportError as e:
    print(f"[warn] Could not import simulation modules: {e}")
    MODULES_LOADED = False

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Data Center Load Modelling API",
    description="REST API wrapping the pandapower simulation engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Response models (mirrors lib/types.ts on the frontend)
# ---------------------------------------------------------------------------

class BaselineResponse(BaseModel):
    total_power_kw: float
    it_load_kw: float
    cooling_power_kw: float
    pue: float
    daily_cost_eur: float
    avg_price_eur_mwh: float
    co2_kg_per_month: float
    water_m3_per_month: float
    location: str = "Frankfurt, DE"
    timesteps_converged: int
    total_timesteps: int

class TimeseriesPoint(BaseModel):
    timestamp: str
    it_load_kw: float
    cooling_kw: float
    total_kw: float
    price_eur_mwh: float

class TimeseriesResponse(BaseModel):
    points: list[TimeseriesPoint]
    resolution_minutes: int = 10

class PricePoint(BaseModel):
    hour: int
    price_eur_mwh: float
    is_cheap_window: bool

class PricesResponse(BaseModel):
    prices: list[PricePoint]
    optimal_window_start: int
    optimal_window_end: int
    current_price_eur_mwh: float
    current_percentile: int

class CarbonResponse(BaseModel):
    co2_intensity_g_kwh: list[dict]
    total_co2_kg_per_month: float
    avg_intensity: float

class ScenarioResult(BaseModel):
    name: str
    strategy: str
    optimised_power_kw: float
    baseline_power_kw: float
    savings_pct: float
    daily_savings_eur: float
    co2_savings_pct: float
    description: str

class ScenariosResponse(BaseModel):
    scenarios: list[ScenarioResult]
    best_scenario: str
    max_savings_pct: float

class GridHealthResponse(BaseModel):
    converged_timesteps: int
    total_timesteps: int
    avg_bus_voltage_pu: float
    min_bus_voltage_pu: float
    max_bus_voltage_pu: float
    avg_line_loading_pct: float
    max_line_loading_pct: float
    total_losses_kw: float
    losses_series: list[dict]

class ProjectionPeriod(BaseModel):
    label: str
    hours: float
    energy_kwh: float
    cost_eur: float
    peak_kw: float

class ProjectionResponse(BaseModel):
    projections: list[ProjectionPeriod]

class WaterResponse(BaseModel):
    annual_water_m3: float
    daily_water_m3: float
    wue: float
    annual_cost_eur: float
    cost_breakdown: dict
    pue_curve: list[dict]
    thermal_schedule: list[dict]

class SimulationRequest(BaseModel):
    load_profile: Optional[str] = "baseline"
    timesteps: Optional[int] = 707

class SimulationJobResponse(BaseModel):
    job_id: str
    status: str  # queued | running | complete

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_modules():
    if not MODULES_LOADED:
        raise HTTPException(
            status_code=503,
            detail="Simulation modules not loaded. Check your Python imports."
        )

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "modules_loaded": MODULES_LOADED}


@app.get("/api/baseline", response_model=BaselineResponse)
def get_baseline():
    """
    Returns the pre-computed baseline simulation result.
    Fast — does NOT re-run pandapower; reads cached output.
    """
    _require_modules()
    t0 = time.perf_counter()
    # TODO: replace with actual call, e.g.:
    #   result = run_full_simulation(timesteps=707)
    #   return BaselineResponse(
    #       total_power_kw=result["total_power_kw"],
    #       ...
    #   )
    raise HTTPException(status_code=501, detail="Connect your run_full_simulation() here")


@app.get("/api/timeseries", response_model=TimeseriesResponse)
def get_timeseries(hours: int = 24):
    """24-hour (or custom) power time-series at 10-min resolution."""
    _require_modules()
    raise HTTPException(status_code=501, detail="Connect your timeseries data here")


@app.get("/api/prices", response_model=PricesResponse)
def get_prices():
    """SMARD day-ahead electricity prices for the next 24 hours."""
    _require_modules()
    # Example:
    #   client = SmardApiClient()
    #   prices = client.get_day_ahead_prices()
    raise HTTPException(status_code=501, detail="Connect SmardApiClient here")


@app.get("/api/carbon", response_model=CarbonResponse)
def get_carbon():
    """Monthly CO2 intensity and total emissions."""
    _require_modules()
    raise HTTPException(status_code=501, detail="Connect CarbonModel here")


@app.get("/api/scenarios", response_model=ScenariosResponse)
def get_scenarios():
    """
    Runs (or returns cached) results for all 10 optimisation scenarios.
    """
    _require_modules()
    # Example:
    #   results = run_all_scenarios()
    #   return ScenariosResponse(scenarios=[...], ...)
    raise HTTPException(status_code=501, detail="Connect run_all_scenarios() here")


@app.get("/api/grid-health", response_model=GridHealthResponse)
def get_grid_health():
    """Pandapower load-flow convergence, bus voltages, and line loadings."""
    _require_modules()
    raise HTTPException(status_code=501, detail="Connect pandapower grid results here")


@app.get("/api/projections", response_model=ProjectionResponse)
def get_projections():
    """Energy and cost projections for 1h / 6h / 24h / 30d windows."""
    _require_modules()
    raise HTTPException(status_code=501, detail="Connect EnergyProjection here")


@app.get("/api/water", response_model=WaterResponse)
def get_water():
    """Water consumption, WUE, PUE curve, and thermal schedule."""
    _require_modules()
    raise HTTPException(status_code=501, detail="Connect WaterModel here")


@app.post("/api/simulation/run", response_model=SimulationJobResponse)
def run_simulation(params: SimulationRequest):
    """
    Trigger a fresh simulation run. For long runs (>1s) consider
    returning a job_id and polling /api/simulation/status/{job_id}.
    """
    _require_modules()
    # Example synchronous run:
    #   result = run_full_simulation(
    #       load_profile=params.load_profile,
    #       timesteps=params.timesteps,
    #   )
    #   return SimulationJobResponse(job_id="sync", status="complete")
    raise HTTPException(status_code=501, detail="Connect run_full_simulation() here")
