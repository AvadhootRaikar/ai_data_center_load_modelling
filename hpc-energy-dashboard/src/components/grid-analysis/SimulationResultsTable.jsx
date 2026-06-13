import { Table } from 'lucide-react';

const simulationData = [
  { timestep: 0,   voltage: 1.00, lineLoad: 22.4, trafoLoad: 35.1, activePower: 3.2,  reactivePower: 1.0 },
  { timestep: 100, voltage: 0.99, lineLoad: 45.6, trafoLoad: 48.3, activePower: 6.2,  reactivePower: 2.0 },
  { timestep: 200, voltage: 0.98, lineLoad: 62.1, trafoLoad: 58.7, activePower: 8.9,  reactivePower: 2.8 },
  { timestep: 300, voltage: 0.97, lineLoad: 74.3, trafoLoad: 67.2, activePower: 10.2, reactivePower: 3.2 },
  { timestep: 400, voltage: 0.96, lineLoad: 87.2, trafoLoad: 78.3, activePower: 11.2, reactivePower: 3.4 },
  { timestep: 500, voltage: 0.97, lineLoad: 71.8, trafoLoad: 64.9, activePower: 9.8,  reactivePower: 3.0 },
  { timestep: 600, voltage: 0.98, lineLoad: 53.4, trafoLoad: 51.2, activePower: 7.1,  reactivePower: 2.2 },
  { timestep: 700, voltage: 0.99, lineLoad: 38.9, trafoLoad: 42.6, activePower: 5.0,  reactivePower: 1.5 },
];

export default function SimulationResultsTable() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Table size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">Detailed Simulation Results</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
          8 timesteps · 720 total
        </span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Timestep</th>
            <th className="text-right">Voltage (p.u.)</th>
            <th className="text-right">Line Load (%)</th>
            <th className="text-right">Trafo Load (%)</th>
            <th className="text-right">Active Power (MW)</th>
            <th className="text-right">Reactive Power (MVAr)</th>
          </tr>
        </thead>
        <tbody>
          {simulationData.map((row) => {
            const isViolation = row.voltage <= 0.96;
            const isHighLoad = row.lineLoad >= 80;
            return (
              <tr key={row.timestep}>
                <td className="font-medium">{row.timestep}</td>
                <td className="text-right" style={isViolation ? { color: 'var(--color-danger)', fontWeight: 600 } : undefined}>
                  {row.voltage.toFixed(2)}
                </td>
                <td className="text-right" style={isHighLoad ? { color: 'var(--color-danger)', fontWeight: 600 } : undefined}>
                  {row.lineLoad.toFixed(1)}
                </td>
                <td className="text-right">{row.trafoLoad.toFixed(1)}</td>
                <td className="text-right">{row.activePower.toFixed(1)}</td>
                <td className="text-right">{row.reactivePower.toFixed(1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
