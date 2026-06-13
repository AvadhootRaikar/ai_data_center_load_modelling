import { useState } from 'react';
import { TrendingUp } from 'lucide-react';

export default function CapacityAnalysisPanel() {
  const [expansion, setExpansion] = useState(false);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <TrendingUp size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Capacity Analysis</span>
        </div>
      </div>
      <div className="card-body">
        <div className="toggle" onClick={() => setExpansion(!expansion)} style={{ marginBottom: 16 }}>
          <div className={`toggle-track ${expansion ? 'active' : ''}`}>
            <div className="toggle-knob" />
          </div>
          <span className="toggle-label">Expansion Mode</span>
        </div>

        <div className="slider-row">
          <div className="slider-row-header">
            <span className="slider-row-label">Transformer Headroom</span>
            <div className="slider-row-value">
              <span className="slider-row-value-num">1.2</span>
              <span className="slider-row-value-unit">x</span>
            </div>
          </div>
          <div className="slider-track">
            <div className="slider-fill" style={{ width: '40%' }} />
            <div className="slider-thumb" style={{ left: 'calc(40% - 8px)' }} />
          </div>
        </div>
      </div>
    </div>
  );
}
