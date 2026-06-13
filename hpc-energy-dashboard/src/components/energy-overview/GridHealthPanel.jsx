import { useSimulation } from '../../context/SimulationContext';
import { Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function GridHealthPanel() {
  const { results } = useSimulation();

  const gh = results?.grid_health || {
    voltage_stability: 99.2,
    transformer_load: 84.0,
    solver_load: 76,
    stability_status: 'Healthy',
    insight_message: 'The current scenario shows a 12.8% energy reduction compared to the baseline, primarily driven by PUE optimization and scheduled training delays.'
  };

  const HEALTH_ROWS = [
    { 
      label: 'Voltage Stability', 
      sublabel: 'Bus voltage deviation', 
      value: `${gh.voltage_stability.toFixed(1)}%`, 
      status: gh.voltage_stability > 95 ? 'pass' : 'warn' 
    },
    { 
      label: 'Transformer Load', 
      sublabel: 'Peak capacity usage', 
      value: `${gh.transformer_load.toFixed(1)}%`, 
      status: gh.transformer_load < 80 ? 'pass' : (gh.transformer_load < 95 ? 'warn' : 'fail') 
    },
    { 
      label: 'Solver CPU Load', 
      sublabel: 'PandaPower load', 
      value: `${gh.solver_load}%`, 
      status: gh.solver_load < 50 ? 'pass' : 'warn' 
    },
  ];

  const STATUS_LABELS = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' };

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
            {gh.insight_message}
          </p>
          <Link to="/grid-analysis">View Detailed Grid Analysis →</Link>
        </div>
      </div>
    </div>
  );
}
