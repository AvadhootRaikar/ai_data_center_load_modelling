import { useState } from 'react';
import { GitBranch } from 'lucide-react';

const solverModes = ['AC', 'DC'];

export default function PandaPowerSolverPanel() {
  const [mode, setMode] = useState('AC');

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
        <div className="segmented-control" style={{ marginBottom: 16 }}>
          {solverModes.map((opt) => (
            <button
              key={opt}
              className={`segmented-btn ${mode === opt ? 'active' : ''}`}
              onClick={() => setMode(opt)}
            >
              {opt}
            </button>
          ))}
        </div>

        <div className="slider-row">
          <div className="slider-row-header">
            <span className="slider-row-label">Max Iterations</span>
            <div className="slider-row-value">
              <span className="slider-row-value-num">10</span>
            </div>
          </div>
          <div className="slider-track">
            <div className="slider-fill" style={{ width: '50%' }} />
            <div className="slider-thumb" style={{ left: 'calc(50% - 8px)' }} />
          </div>
        </div>
      </div>
    </div>
  );
}
