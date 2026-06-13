const PROJECTIONS = [
  { category: 'IT Load', estimated: '92.4 MWh', baseline: '95.1 MWh', deviation: '-2.8%', status: 'pass' },
  { category: 'Cooling System', estimated: '28.1 MWh', baseline: '22.4 MWh', deviation: '+25.4%', status: 'warn' },
  { category: 'Power Distribution Losses', estimated: '4.2 MWh', baseline: '3.9 MWh', deviation: '+7.6%', status: 'pass' },
  { category: 'UPS Parasitic Load', estimated: '1.8 MWh', baseline: '2.5 MWh', deviation: '-28.0%', status: 'fail' },
  { category: 'Lighting & Auxiliary', estimated: '0.9 MWh', baseline: '0.8 MWh', deviation: '+12.5%', status: 'pass' },
];

const STATUS_LABELS = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' };

export default function ProjectionsTable() {
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
          {PROJECTIONS.map((row) => (
            <tr key={row.category}>
              <td className="font-medium">{row.category}</td>
              <td className="text-right">{row.estimated}</td>
              <td className="text-right muted">{row.baseline}</td>
              <td className="text-right" style={{ fontWeight: 600 }}>{row.deviation}</td>
              <td className="text-right">
                <span className={`status-badge ${row.status}`}>
                  {STATUS_LABELS[row.status]}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
