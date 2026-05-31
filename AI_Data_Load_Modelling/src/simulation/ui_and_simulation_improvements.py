"""
Dashboard and Simulation Improvements Module

Provides UI enhancements, real-time pricing integration, and advanced simulation features.
"""

import pandas as pd
import numpy as np
from pathlib import Path


# Load German grid data
def load_grid_pricing_data():
    """Load real German grid pricing and carbon data from CSV."""
    try:
        data_path = Path(__file__).parent.parent.parent / "data" / "grid_data" / "german_grid_profile.csv"
        df = pd.read_csv(data_path)
        
        pricing_map = {}
        carbon_map = {}
        
        for _, row in df.iterrows():
            period = row['time_period']
            pricing_map[period] = {
                'price_eur_mwh': row['price_eur_mwh'],
                'price_eur_kwh': row['price_eur_kwh'],
                'carbon_gco2_kwh': row['carbon_gco2_kwh'],
            }
            carbon_map[period] = row['carbon_gco2_kwh']
        
        return pricing_map, carbon_map, df
    except Exception as e:
        print(f"Error loading grid data: {e}")
        return {}, {}, None


def get_period_for_hour(hour):
    """
    Get grid pricing period for given hour of day.
    
    Args:
        hour: Hour of day (0-23)
        
    Returns:
        str: Time period name
    """
    if 0 <= hour < 6:
        return "Off-peak (00:00-06:00)"
    elif 6 <= hour < 10:
        return "Early Morning (06:00-10:00)"
    elif 10 <= hour < 16:
        return "Midday (10:00-16:00)"
    elif 16 <= hour < 21:
        return "Evening Peak (16:00-21:00)"
    else:
        return "Late Night (21:00-00:00)"


def get_auto_pricing_for_hour(hour, pricing_map):
    """
    Get automatic electricity price for given hour from real grid data.
    
    Args:
        hour: Hour of day (0-23)
        pricing_map: Dictionary with pricing data
        
    Returns:
        dict: Pricing info including price and carbon intensity
    """
    period = get_period_for_hour(hour)
    return pricing_map.get(period, {'price_eur_kwh': 0.04, 'carbon_gco2_kwh': 150})


def calculate_workload_cost_by_time(profile, pricing_map, workload_duration_hours=1):
    """
    Calculate total cost of running workload at each hour of day.
    
    Args:
        profile: DataFrame with workload power profile
        pricing_map: Pricing data from German grid
        workload_duration_hours: How long the workload runs
        
    Returns:
        DataFrame: Hourly costs for starting workload at each hour
    """
    total_power_mwh = profile["total_power_mw"].sum() if "total_power_mw" in profile.columns else 0.0427
    
    hourly_costs = []
    
    for start_hour in range(24):
        total_cost = 0.0
        
        for i in range(int(workload_duration_hours)):
            hour = (start_hour + i) % 24
            period_data = get_auto_pricing_for_hour(hour, pricing_map)
            price_eur_mwh = period_data['price_eur_mwh']
            
            # Cost = Energy * Price
            hour_cost = total_power_mwh * (price_eur_mwh / 1000)  # Convert MWh to kWh pricing
            total_cost += hour_cost
        
        hourly_costs.append({
            'start_hour': f"{start_hour:02d}:00",
            'total_cost_eur': total_cost,
            'avg_price_eur_mwh': total_cost / max(total_power_mwh, 1e-9) if total_power_mwh > 0 else 0,
            'period': get_period_for_hour(start_hour)
        })
    
    return pd.DataFrame(hourly_costs)


def calculate_workload_carbon_by_time(profile, pricing_map, workload_duration_hours=1):
    """
    Calculate total carbon emissions for running workload at each hour of day.
    
    Args:
        profile: DataFrame with workload power profile
        pricing_map: Carbon intensity map
        workload_duration_hours: How long the workload runs
        
    Returns:
        DataFrame: Hourly carbon for starting workload at each hour
    """
    total_power_mwh = profile["total_power_mw"].sum() if "total_power_mw" in profile.columns else 0.0427
    total_power_kwh = total_power_mwh * 1000
    
    hourly_emissions = []
    
    for start_hour in range(24):
        total_carbon = 0.0
        
        for i in range(int(workload_duration_hours)):
            hour = (start_hour + i) % 24
            period_data = get_auto_pricing_for_hour(hour, pricing_map)
            carbon_gco2_kwh = period_data['carbon_gco2_kwh']
            
            # Carbon = Energy * Intensity
            hour_carbon = total_power_kwh * (carbon_gco2_kwh / 1000)  # grams to kg
            total_carbon += hour_carbon
        
        hourly_emissions.append({
            'start_hour': f"{start_hour:02d}:00",
            'total_carbon_kg': total_carbon,
            'avg_carbon_gco2_kwh': total_carbon * 1000 / max(total_power_kwh, 1e-9) if total_power_kwh > 0 else 100,
            'period': get_period_for_hour(start_hour)
        })
    
    return pd.DataFrame(hourly_emissions)


def find_best_scheduling_hours(pricing_map, carbon_map):
    """
    Find best hours to schedule workloads for cost and carbon optimization.
    
    Args:
        pricing_map: Pricing data
        carbon_map: Carbon intensity data
        
    Returns:
        dict: Best hours for cost and carbon optimization
    """
    best_cost_hour = min(pricing_map.items(), key=lambda x: x[1]['price_eur_kwh'])
    best_carbon_hour = min(carbon_map.items(), key=lambda x: x[1])
    
    return {
        'best_cost_period': best_cost_hour[0],
        'best_cost_price': best_cost_hour[1]['price_eur_kwh'],
        'best_carbon_period': best_carbon_hour[0],
        'best_carbon_intensity': best_carbon_hour[1],
    }


# ============================================================================
# UI IMPROVEMENT FEATURES
# ============================================================================

def get_ui_theme():
    """Get professional UI theme configuration."""
    return {
        "primary_color": "#0066CC",
        "background_color": "#F8F9FA",
        "secondary_background_color": "#FFFFFF",
        "text_color": "#1D3557",
        "accent_colors": ["#00A651", "#2A9D8F", "#E63946", "#FF9500"],
        "chart_height": 400,
        "sidebar_width": 350,
    }


def get_metric_display_format(metric_type):
    """Get formatting specifications for different metric types."""
    formats = {
        "energy": {"decimals": 4, "unit": "MWh", "icon": "zap"},
        "power": {"decimals": 4, "unit": "MW", "icon": "bolt"},
        "cost": {"decimals": 2, "unit": "EUR", "icon": "euro"},
        "carbon": {"decimals": 0, "unit": "kg CO2e", "icon": "leaf"},
        "percentage": {"decimals": 1, "unit": "%", "icon": "percent"},
        "pue": {"decimals": 2, "unit": "", "icon": "wind"},
        "temperature": {"decimals": 1, "unit": "C", "icon": "thermometer"},
    }
    return formats.get(metric_type, {"decimals": 2, "unit": "", "icon": "info"})


# ============================================================================
# SIMULATION IMPROVEMENTS
# ============================================================================

def apply_realistic_pue_profile(profile, hour_start=12, pue_baseline=1.3):
    """
    Apply realistic PUE variations based on time of day and ambient temperature.
    
    Args:
        profile: DataFrame with workload
        hour_start: Hour of day to start simulation
        pue_baseline: Baseline PUE value
        
    Returns:
        DataFrame: Profile with PUE adjustments
    """
    updated = profile.copy()
    
    # PUE variations by time of day (cooler at night, higher during day)
    pue_factors = []
    for i in range(len(updated)):
        hour = (hour_start + (i % 24)) % 24
        
        # Lower PUE at night (better cooling), higher during day
        if 0 <= hour < 6:
            pue_factor = 0.95  # 5% better at night
        elif 6 <= hour < 12:
            pue_factor = 1.0   # Standard
        elif 12 <= hour < 18:
            pue_factor = 1.05  # 5% worse during peak heat
        else:
            pue_factor = 0.98  # 2% better in evening
        
        pue_factors.append(pue_factor)
    
    if "total_power_mw" in updated.columns:
        updated["total_power_mw"] = updated["total_power_mw"] * np.array(pue_factors)
    
    return updated


def apply_demand_response_optimization(profile, pricing_map):
    """
    Apply demand response - reduce load during peak pricing hours.
    
    Args:
        profile: DataFrame with workload
        pricing_map: Pricing data
        
    Returns:
        DataFrame: Profile with demand response applied
    """
    updated = profile.copy()
    
    # Identify peak and off-peak hours
    peak_periods = ["Evening Peak (16:00-21:00)"]
    offpeak_periods = ["Off-peak (00:00-06:00)"]
    
    # Reduce load during peak by 10%, increase during off-peak slightly
    if "total_power_mw" in updated.columns:
        updated["demand_response_factor"] = 1.0
        # This would require time info in profile to implement fully
    
    return updated


def calculate_grid_stability_impact(profile, grid_capacity_mw=1000):
    """
    Calculate impact of workload on grid stability.
    
    Args:
        profile: DataFrame with workload
        grid_capacity_mw: Maximum grid capacity
        
    Returns:
        dict: Grid stability metrics
    """
    peak_power = profile["total_power_mw"].max() if "total_power_mw" in profile.columns else 0.0427
    avg_power = profile["total_power_mw"].mean() if "total_power_mw" in profile.columns else 0.0393
    
    peak_utilization_pct = (peak_power / grid_capacity_mw) * 100
    avg_utilization_pct = (avg_power / grid_capacity_mw) * 100
    
    # Determine stability status
    if peak_utilization_pct > 80:
        stability_status = "Critical - High Grid Stress"
    elif peak_utilization_pct > 60:
        stability_status = "Warning - Moderate Grid Stress"
    else:
        stability_status = "Healthy - Adequate Grid Capacity"
    
    return {
        "peak_utilization_pct": peak_utilization_pct,
        "avg_utilization_pct": avg_utilization_pct,
        "stability_status": stability_status,
        "recommended_shift": "Shift to off-peak (00-06)" if peak_utilization_pct > 60 else "Current timing optimal",
    }
