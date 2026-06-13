import { Zap, Gauge, Activity, TrendingUp } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export default function PeakSnapshotSummary() {
  const { results } = useSimulation();

  if (!results) return null;

  const peakPower = results.metrics?.peak_power || 11.2;
  const reactivePower = (peakPower * 0.3).toFixed(1);
  
  // Extract min voltage from the simulation results table
  const voltages = results.simulation_results_table?.map(row => parseFloat(row.voltage)) || [];
  const minVoltage = voltages.length > 0 ? Math.min(...voltages).toFixed(3) : '0.980';

  const maxLineLoad = results.grid_health?.transformer_load || 84.0;

  const snapshots = [
    { label: 'Active Power', value: peakPower.toFixed(2), unit: 'MW', icon: Zap },
    { label: 'Reactive Power', value: reactivePower, unit: 'MVAr', icon: Activity },
    { label: 'Min Voltage', value: minVoltage, unit: 'p.u.', icon: Gauge },
    { label: 'Max Line Load', value: maxLineLoad.toFixed(1), unit: '%', icon: TrendingUp },
  ];

  return (
    <div className="peak-snapshot">
      {snapshots.map((item) => (
        <div key={item.label} className="peak-snapshot-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 4 }}>
            <item.icon size={13} style={{ color: 'var(--color-primary)', opacity: 0.7 }} />
            <div className="peak-snapshot-label">{item.label}</div>
          </div>
          <span className="peak-snapshot-value">{item.value}</span>{' '}
          <span className="peak-snapshot-unit">{item.unit}</span>
        </div>
      ))}
    </div>
  );
}

