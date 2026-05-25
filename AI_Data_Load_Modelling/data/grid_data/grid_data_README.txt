GERMAN GRID DATA - Documentation
=====================================

File: german_grid_profile.csv
Description: Time-of-use pricing and carbon intensity for German electricity grid

Data Sources:
- EPEX SPOT (electricity exchange): Day-ahead prices for DE-LU zone
- SMARD.de (German grid operator): Generation mix data
- ENTSO-E: Carbon intensity calculations

Fields:
- time_period: Time window for tariff (5 daily windows)
- price_eur_mwh: Price in EUR per MWh
- price_eur_kwh: Price in EUR per kWh (for calculations)
- carbon_gco2_kwh: Carbon intensity in grams CO2 per kWh
- wind_pct: Wind power percentage of generation mix
- solar_pct: Solar power percentage
- fossil_pct: Fossil fuel percentage (coal+gas+oil)
- hydro_pct: Hydropower percentage
- biomass_pct: Biomass percentage

Usage in Framework:
Our scenario analysis uses these values to calculate:
- Cost impact of workload shifting (time-of-use pricing)
- Carbon impact of shifting workloads (carbon intensity varies by hour)
- Energy optimization strategies

Update Frequency:
- Update prices monthly from: https://www.epexspot.com/
- Update generation mix weekly from: https://www.smard.de/
- Recalculate carbon intensity with generation mix updates

Current Data Date: May 19, 2026
Data Validation Status: Compared against real EPEX SPOT and SMARD data - OK

Note: These are based on realistic German grid patterns but simplified to
5 time periods for clarity in analysis. Real grid has more granular hourly data.
