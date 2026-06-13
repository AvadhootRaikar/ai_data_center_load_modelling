import { Zap } from 'lucide-react';

const HEALTH_ROWS = [
  { label: 'Voltage Stability', sublabel: 'Bus voltage deviation', value: '99.2%', status: 'pass' },
  { label: 'Transformer Load', sublabel: 'Peak capacity usage', value: '84.0%', status: 'warn' },
  { label: 'Convergence Rate', sublabel: 'Solver iterations', value: '100%', status: 'pass' },
];

const STATUS_LABELS = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' };

export default function GridHealthPanel() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Zap size={14} />
          <span className="card-title">Electrical Grid Health</span>
        </div>
      </div>
      <div className="card-body">
        {HEALTH_ROWS.map((row) => (
          <div className="grid-health-row" key={row.label}>
            <div className="grid-health-row-left">
              <div>
                <div className="grid-health-row-label">{row.label}</div>
                <div className="grid-health-row-sublabel">{row.sublabel}</div>
              </div>
            </div>
            <div className="grid-health-row-right">
              <div className="grid-health-row-value">
                <div className="grid-health-row-num">{row.value}</div>
              </div>
              <span className={`status-badge ${row.status}`}>
                {STATUS_LABELS[row.status]}
              </span>
            </div>
          </div>
        ))}

        <div className="insight-panel" style={{ marginTop: 16 }}>
          <div className="insight-panel-label">Simulation Insight</div>
          <p>
            The current scenario shows a <strong>12.8% energy reduction</strong> compared
            to the baseline, primarily driven by PUE optimization and scheduled training
            delays during off-peak pricing.
          </p>
          <a href="#grid-analysis">View Detailed Grid Analysis →</a>
        </div>
      </div>
    </div>
  );
}
