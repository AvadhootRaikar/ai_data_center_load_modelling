import { useSimulation } from '../../context/SimulationContext';
import { TrendingUp } from 'lucide-react';

export default function CapacityAnalysisPanel() {
  const {
    expansionMode, setExpansionMode,
    transformerHeadroom, setTransformerHeadroom
  } = useSimulation();

  // Convert headroom to percentage for slider (range 1.0 to 2.0)
  const percent = Math.min(100, Math.max(0, ((transformerHeadroom - 1.0) / (2.0 - 1.0)) * 100));

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <TrendingUp size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Capacity Analysis</span>
        </div>
      </div>
      <div className="card-body">
        <div className="toggle" onClick={() => setExpansionMode(!expansionMode)} style={{ marginBottom: 16 }}>
          <div className={`toggle-track ${expansionMode ? 'active' : ''}`}>
            <div className="toggle-knob" />
          </div>
          <span className="toggle-label">Expansion Mode</span>
        </div>

        <div className="slider-row">
          <div className="slider-row-header">
            <span className="slider-row-label">Transformer Headroom</span>
            <div className="slider-row-value">
              <span className="slider-row-value-num">{transformerHeadroom.toFixed(1)}</span>
              <span className="slider-row-value-unit">x</span>
            </div>
          </div>
          <div className="slider-track" style={{ position: 'relative' }}>
            <div className="slider-fill" style={{ width: `${percent}%` }} />
            <div className="slider-thumb" style={{ left: `calc(${percent}% - 8px)` }} />
            <input 
              type="range"
              min="1.0"
              max="2.0"
              step="0.1"
              value={transformerHeadroom}
              onChange={(e) => setTransformerHeadroom(parseFloat(e.target.value))}
              style={{
                position: 'absolute',
                top: 0, left: 0, width: '100%', height: '100%',
                opacity: 0, cursor: 'pointer'
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
