"""
Water Usage Model for AI Data Center Cooling Systems
=======================================================
Calculates water consumption based on GPU power and cooling type.
Integrates with dynamic PUE and thermal-aware scheduling.

Water Usage Formula:
    Water Lost (L/hour) = GPU Power (kW) / 2.4  [for wet cooling]
    Water Lost (L/hour) = 0  [for dry cooling]
    
Ambient Temperature Impact:
    Dynamic PUE = 1.2 + (0.08 * (ambient_temp - 20))
    Higher temps → higher cooling power → more water
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class WaterUsageModel:
    """Calculate water consumption for HPC facilities with wet/dry cooling."""
    
    def __init__(self, cooling_type='wet', facility_efficiency=0.92):
        """
        Args:
            cooling_type: 'wet' (evaporative) or 'dry' (radiator-based)
            facility_efficiency: Cooling system efficiency (0.85-0.95)
        """
        self.cooling_type = cooling_type
        self.facility_efficiency = facility_efficiency
        
    def calculate_dynamic_pue(self, it_power_kw, ambient_temp_celsius=20, base_pue=1.3):
        """
        Calculate PUE dynamically based on ambient temperature and IT load.
        
        Formula:
            Cooling Power = IT Power * (PUE - 1)
            Dynamic PUE = 1.2 + 0.08 * (ambient_temp - 20)
            
        Args:
            it_power_kw: Total IT equipment power (kW)
            ambient_temp_celsius: Outside air temperature
            base_pue: Base PUE at 20°C (default 1.3)
            
        Returns:
            dict with 'pue', 'cooling_power_kw', 'total_power_kw'
        """
        # Dynamic PUE based on temperature
        temp_offset = (ambient_temp_celsius - 20)
        dynamic_pue = base_pue + (0.08 * temp_offset)
        
        # Clamp PUE to realistic range (1.1 - 2.5)
        dynamic_pue = max(1.1, min(2.5, dynamic_pue))
        
        # Calculate cooling power
        cooling_power_kw = it_power_kw * (dynamic_pue - 1)
        total_facility_power_kw = it_power_kw + cooling_power_kw
        
        return {
            'pue': round(dynamic_pue, 3),
            'cooling_power_kw': round(cooling_power_kw, 2),
            'total_power_kw': round(total_facility_power_kw, 2),
            'it_power_kw': it_power_kw,
            'ambient_temp': ambient_temp_celsius
        }
    
    def calculate_water_usage(self, cooling_power_kw, ambient_temp=20):
        """
        Calculate water consumption for wet cooling systems.
        
        Formula (empirical from industry data):
            Water Lost (L/hour) = Cooling Power (kW) / 2.4
            
        Accounts for:
            - Evaporative loss in cooling towers
            - Bleed-off to prevent mineral buildup
            - Make-up water to maintain system
            
        Args:
            cooling_power_kw: Thermal load to remove (kW)
            ambient_temp: Outside temperature (affects efficiency)
            
        Returns:
            dict with water metrics (L/hour, L/day, L/year)
        """
        if self.cooling_type == 'dry':
            # Dry cooling uses no water
            return {
                'water_type': 'dry',
                'water_liters_per_hour': 0,
                'water_liters_per_day': 0,
                'water_liters_per_year': 0,
                'water_m3_per_year': 0
            }
        
        # Wet cooling water consumption
        # Industry standard: ~0.4-0.5 L/h per kW of cooling capacity
        # Using 0.417 L/h per kW (= 1 L/hour per 2.4 kW)
        water_efficiency_liters_per_kw_hour = 1 / 2.4
        
        water_per_hour = cooling_power_kw * water_efficiency_liters_per_kw_hour
        water_per_day = water_per_hour * 24
        water_per_year = water_per_day * 365.25
        water_m3_per_year = water_per_year / 1000
        
        return {
            'water_type': 'wet',
            'cooling_power_kw': round(cooling_power_kw, 2),
            'water_liters_per_hour': round(water_per_hour, 1),
            'water_liters_per_day': round(water_per_day, 0),
            'water_liters_per_year': round(water_per_year, 0),
            'water_m3_per_year': round(water_m3_per_year, 1),
            'ambient_temp': ambient_temp
        }
    
    def calculate_water_cost(self, water_liters_per_year, cost_per_m3=2.0):
        """
        Estimate water cost for facility (German regional average: €1.5-2.5/m³).
        
        Args:
            water_liters_per_year: Annual water consumption
            cost_per_m3: Cost per cubic meter (€2.0 = German average)
            
        Returns:
            dict with water cost metrics
        """
        water_m3 = water_liters_per_year / 1000
        annual_cost_eur = water_m3 * cost_per_m3
        monthly_cost_eur = annual_cost_eur / 12
        
        return {
            'water_m3_per_year': round(water_m3, 1),
            'cost_per_m3_eur': cost_per_m3,
            'annual_cost_eur': round(annual_cost_eur, 2),
            'monthly_cost_eur': round(monthly_cost_eur, 2),
            'daily_cost_eur': round(annual_cost_eur / 365.25, 2)
        }
    
    def thermal_aware_scheduling_score(self, ambient_temp, hour_of_day, is_carbon_low=False):
        """
        Score an hour for workload scheduling based on cooling efficiency.
        
        Combines:
            - Temperature (cooler = better for cooling)
            - Hour of day (typical patterns)
            - Carbon intensity (if provided)
            
        Returns:
            score 0-100 (higher = better for thermal scheduling)
        """
        # Temperature score (cooler is better)
        # Optimal: 5-15°C, Worse: >25°C
        if ambient_temp <= 5:
            temp_score = 90
        elif ambient_temp <= 15:
            temp_score = 100
        elif ambient_temp <= 20:
            temp_score = 85
        elif ambient_temp <= 25:
            temp_score = 70
        else:
            temp_score = max(40, 100 - (ambient_temp - 25) * 3)
        
        # Time of day pattern (typical German weather)
        # Coldest: 3-6 AM, Warmest: 2-4 PM
        hour_scores = {
            0: 95, 1: 95, 2: 98, 3: 100, 4: 100, 5: 98,  # Coldest hours
            6: 85, 7: 75, 8: 65, 9: 55,
            10: 50, 11: 45, 12: 40, 13: 35, 14: 30, 15: 35,  # Hottest
            16: 40, 17: 50, 18: 60, 19: 70, 20: 80,
            21: 85, 22: 90, 23: 93
        }
        hour_score = hour_scores.get(hour_of_day, 50)
        
        # Carbon bonus if also low-carbon hour
        carbon_bonus = 15 if is_carbon_low else 0
        
        # Combined score (weighted: 50% temp, 40% hour, 10% carbon bonus)
        final_score = (temp_score * 0.5 + hour_score * 0.4) + carbon_bonus
        
        return round(min(100, final_score), 1)


class ThermalAwareScheduler:
    """Recommends optimal hours for workload execution based on cooling efficiency."""
    
    def __init__(self, water_model):
        self.water_model = water_model
    
    def get_hourly_recommendations(self, ambient_temps_by_hour, carbon_intensity_by_hour=None):
        """
        Generate hourly thermal-aware scheduling recommendations.
        
        Args:
            ambient_temps_by_hour: Dict {hour: temp_celsius} for 24-hour cycle
            carbon_intensity_by_hour: Dict {hour: g_CO2/kWh} (optional)
            
        Returns:
            DataFrame with recommendations for each hour
        """
        if carbon_intensity_by_hour is None:
            carbon_intensity_by_hour = {}
        
        recommendations = []
        
        for hour in range(24):
            temp = ambient_temps_by_hour.get(hour, 20)
            carbon = carbon_intensity_by_hour.get(hour, 150)
            is_low_carbon = carbon < 120  # German grid average
            
            score = self.water_model.thermal_aware_scheduling_score(
                temp, hour, is_carbon_low=is_low_carbon
            )
            
            # Recommendation tier
            if score >= 90:
                recommendation = "🟢 Optimal - Run heavy workloads"
            elif score >= 75:
                recommendation = "🟢 Good - Suitable for execution"
            elif score >= 60:
                recommendation = "🟡 Fair - Consider if urgent"
            else:
                recommendation = "🔴 Poor - Avoid if possible"
            
            recommendations.append({
                'hour': hour,
                'ambient_temp': temp,
                'carbon_intensity': carbon,
                'thermal_score': score,
                'recommendation': recommendation
            })
        
        return pd.DataFrame(recommendations)


# ============================================================================
# Integration with existing models
# ============================================================================

def integrate_water_model_with_results(results_df, cooling_type='wet', it_power_column='energy_mwh'):
    """
    Add water usage metrics to existing simulation results.
    
    Args:
        results_df: Existing results DataFrame from simulation
        cooling_type: 'wet' or 'dry'
        it_power_column: Column name containing IT power (kW or MWh)
        
    Returns:
        Enhanced DataFrame with water columns
    """
    water_model = WaterUsageModel(cooling_type=cooling_type)
    
    # Assume ambient temperature from 20°C baseline (can be enhanced with weather data)
    ambient_temp = 20
    
    # Calculate water usage for each row
    water_usage_list = []
    
    for idx, row in results_df.iterrows():
        # Convert energy to power if needed
        it_power_kw = row[it_power_column] * 1000 if it_power_column == 'energy_mwh' else row[it_power_column]
        
        # Calculate dynamic PUE
        pue_data = water_model.calculate_dynamic_pue(it_power_kw, ambient_temp)
        
        # Calculate water usage
        water_data = water_model.calculate_water_usage(pue_data['cooling_power_kw'], ambient_temp)
        
        water_usage_list.append({
            'pue': pue_data['pue'],
            'cooling_power_kw': pue_data['cooling_power_kw'],
            'water_liters_per_hour': water_data['water_liters_per_hour'],
            'water_liters_per_day': water_data['water_liters_per_day']
        })
    
    water_df = pd.DataFrame(water_usage_list)
    results_df = pd.concat([results_df, water_df], axis=1)
    
    return results_df


if __name__ == '__main__':
    # Example usage
    water_model = WaterUsageModel(cooling_type='wet')
    
    print("=" * 70)
    print("WATER USAGE MODEL - EXAMPLE CALCULATION")
    print("=" * 70)
    
    # Scenario: 100 kW IT load, 20°C ambient
    it_power = 100
    ambient = 20
    
    pue_result = water_model.calculate_dynamic_pue(it_power, ambient)
    print(f"\n📊 PUE Calculation (IT Power: {it_power} kW, Ambient: {ambient}°C)")
    print(f"   Dynamic PUE: {pue_result['pue']}")
    print(f"   Cooling Power: {pue_result['cooling_power_kw']} kW")
    print(f"   Total Facility Power: {pue_result['total_power_kw']} kW")
    
    water_result = water_model.calculate_water_usage(pue_result['cooling_power_kw'], ambient)
    print(f"\n💧 Water Usage (Wet Cooling)")
    print(f"   Per Hour: {water_result['water_liters_per_hour']} L")
    print(f"   Per Day: {water_result['water_liters_per_day']:,.0f} L")
    print(f"   Per Year: {water_result['water_liters_per_year']:,.0f} L ({water_result['water_m3_per_year']} m³)")
    
    cost_result = water_model.calculate_water_cost(water_result['water_liters_per_year'])
    print(f"\n💰 Water Cost (German average: €{cost_result['cost_per_m3_eur']}/m³)")
    print(f"   Annual: €{cost_result['annual_cost_eur']:,.2f}")
    print(f"   Monthly: €{cost_result['monthly_cost_eur']:,.2f}")
    
    print("\n" + "=" * 70)
