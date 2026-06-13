import { useState } from 'react';
import { Server } from 'lucide-react';

const coolingOptions = ['Air', 'Liquid', 'Hybrid'];

const coolingPueMap = {
  Air: { pue: '1.40', percent: 80 },
  Liquid: { pue: '1.25', percent: 62 },
  Hybrid: { pue: '1.30', percent: 70 },
};

export default function FacilityAssumptionsPanel() {
  const [cooling, setCooling] = useState('Liquid');
  const { pue, percent } = coolingPueMap[cooling];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Server size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Facility Assumptions</span>
        </div>
      </div>
      <div className="card-body">
        <div className="slider-row">
          <div className="slider-row-header">
            <span className="slider-row-label">Target PUE</span>
            <div className="slider-row-value">
              <span className="slider-row-value-num">{pue}</span>
            </div>
          </div>
          <div className="slider-track">
            <div className="slider-fill" style={{ width: `${percent}%` }} />
            <div className="slider-thumb" style={{ left: `calc(${percent}% - 8px)` }} />
          </div>
        </div>

        <div style={{ marginBottom: 4 }}>
          <span className="slider-row-label">Cooling Type</span>
        </div>
        <div className="segmented-control">
          {coolingOptions.map((opt) => (
            <button
              key={opt}
              className={`segmented-btn ${cooling === opt ? 'active' : ''}`}
              onClick={() => setCooling(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
        <p style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-muted-foreground)',
          marginTop: 8,
        }}>
          Cooling type auto-adjusts the Target PUE value.
        </p>
      </div>
    </div>
  );
}
