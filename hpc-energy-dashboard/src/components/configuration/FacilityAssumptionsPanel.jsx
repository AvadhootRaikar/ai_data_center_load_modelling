import { useSimulation } from '../../context/SimulationContext';
import { Server } from 'lucide-react';

const coolingOptions = ['Air', 'Liquid', 'Hybrid'];

const coolingPueMap = {
  Air: 1.40,
  Liquid: 1.25,
  Hybrid: 1.30,
};

export default function FacilityAssumptionsPanel() {
  const { targetPue, setTargetPue, coolingType, setCoolingType } = useSimulation();

  const handleCoolingChange = (opt) => {
    setCoolingType(opt);
    setTargetPue(coolingPueMap[opt]);
  };

  // Convert PUE to percentage for slider (range 1.10 to 2.00)
  const percent = Math.min(100, Math.max(0, ((targetPue - 1.10) / (2.00 - 1.10)) * 100));

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
              <span className="slider-row-value-num">{targetPue.toFixed(2)}</span>
            </div>
          </div>
          <div className="slider-track" style={{ position: 'relative' }}>
            <div className="slider-fill" style={{ width: `${percent}%` }} />
            <div className="slider-thumb" style={{ left: `calc(${percent}% - 8px)` }} />
            <input 
              type="range"
              min="1.10"
              max="2.00"
              step="0.05"
              value={targetPue}
              onChange={(e) => setTargetPue(parseFloat(e.target.value))}
              style={{
                position: 'absolute',
                top: 0, left: 0, width: '100%', height: '100%',
                opacity: 0, cursor: 'pointer'
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: 4 }}>
          <span className="slider-row-label">Cooling Type</span>
        </div>
        <div className="segmented-control">
          {coolingOptions.map((opt) => (
            <button
              key={opt}
              className={`segmented-btn ${coolingType === opt ? 'active' : ''}`}
              onClick={() => handleCoolingChange(opt)}
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

