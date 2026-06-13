import { Table } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export default function SimulationResultsTable() {
  const { results } = useSimulation();

  const simulationData = results?.simulation_results_table || [];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Table size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">Detailed Simulation Results</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
          {simulationData.length} timesteps displayed
        </span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Timestep</th>
            <th>Time</th>
            <th className="text-right">Voltage (p.u.)</th>
            <th className="text-right">Trafo Load (%)</th>
            <th className="text-right">Active Power (MW)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {simulationData.map((row) => {
            const voltVal = parseFloat(row.voltage);
            const isViolation = voltVal <= 0.95;
            const loadVal = parseFloat(row.loading);
            const isHighLoad = loadVal >= 80;
            
            return (
              <tr key={row.timestep}>
                <td className="font-medium">{row.timestep}</td>
                <td className="muted">{row.time}</td>
                <td className="text-right" style={isViolation ? { color: 'var(--color-danger)', fontWeight: 600 } : undefined}>
                  {row.voltage}
                </td>
                <td className="text-right" style={isHighLoad ? { color: 'var(--color-danger)', fontWeight: 600 } : undefined}>
                  {row.loading}
                </td>
                <td className="text-right">{row.power}</td>
                <td>
                  <span className={`status-badge ${row.status === 'PASS' ? 'pass' : 'fail'}`}>
                    {row.status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

