import { useSimulation } from '../../context/SimulationContext';

export default function ProjectionsTable() {
  const { results } = useSimulation();
  
  const projections = results?.projections_table || [];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <span className="card-title">Estimated Energy Projections</span>
        </div>
      </div>
      <div style={{ padding: '0 20px 4px' }}>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)', margin: '12px 0 0' }}>
          Comparative analysis of simulation results vs. baseline scenario.
        </p>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Parameter Category</th>
            <th className="text-right">Estimated</th>
            <th className="text-right">Baseline</th>
            <th className="text-right">Deviation</th>
            <th className="text-right">Sanity Status</th>
          </tr>
        </thead>
        <tbody>
          {projections.map((row) => (
            <tr key={row.category}>
              <td className="font-medium">{row.category}</td>
              <td className="text-right">{row.estimated}</td>
              <td className="text-right muted">{row.historical || row.baseline}</td>
              <td className="text-right" style={{ fontWeight: 600 }}>{row.deviation}</td>
              <td className="text-right">
                <span className={`status-badge ${row.statusType || row.status.toLowerCase()}`}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

