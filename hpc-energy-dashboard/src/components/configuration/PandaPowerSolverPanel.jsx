import { useSimulation } from '../../context/SimulationContext';
import { GitBranch } from 'lucide-react';

const solverModes = [
  { label: 'AC (Newton-Raphson)', value: false },
  { label: 'DC (Linear Flow)', value: true }
];

const gridBackends = [
  'Synthetic HPC grid',
  'SimBench German benchmark grid'
];

export default function PandaPowerSolverPanel() {
  const { fastMode, setFastMode, gridBackend, setGridBackend } = useSimulation();

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <GitBranch size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">PandaPower Solver</span>
        </div>
      </div>
      <div className="card-body">
        <div style={{ marginBottom: 8 }}>
          <span className="slider-row-label">Solver Mode</span>
        </div>
        <div className="segmented-control" style={{ marginBottom: 16, flexDirection: 'column', gap: 6, background: 'none', padding: 0 }}>
          {solverModes.map((opt) => (
            <button
              key={opt.label}
              className={`segmented-btn ${fastMode === opt.value ? 'active' : ''}`}
              onClick={() => setFastMode(opt.value)}
              style={{ width: '100%', borderRadius: 'var(--radius-md)', padding: '8px 12px' }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div style={{ marginBottom: 8 }}>
          <span className="slider-row-label">Grid Topology Backend</span>
        </div>
        <select 
          value={gridBackend}
          onChange={(e) => setGridBackend(e.target.value)}
          className="input-field"
          style={{ width: '100%', padding: '6px 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', background: 'var(--color-input)' }}
        >
          {gridBackends.map((backend) => (
            <option key={backend} value={backend}>{backend}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

