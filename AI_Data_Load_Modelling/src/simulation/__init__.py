"""
Enhanced HPC Workload & Power Grid Simulation Framework

This package extends the Master thesis project with:
- Real-world electricity price integration
- Carbon intensity tracking
- Dynamic PUE modeling with environmental factors
- Multi-GPU and distributed workload support
- Renewable energy profile integration
- Advanced optimization scenarios
- Production-grade reactive power handling
"""

__version__ = "2.0.0"
__author__ = "Enhanced from Master Thesis"

from . import profile_builder
from . import power_model
from . import grid_model
from . import run_simulation
from . import cost_model
from . import carbon_model
from . import energy_projection

__all__ = [
    "profile_builder",
    "power_model",
    "grid_model",
    "run_simulation",
    "cost_model",
    "carbon_model",
    "energy_projection",
]
