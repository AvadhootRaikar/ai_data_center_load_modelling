import { useState } from 'react';
import { TrendingUp, ChevronDown, ChevronRight, Info } from 'lucide-react';

export default function ProjectionForecastingSection() {
  const [open, setOpen] = useState(true);

  return (
    <div className="collapsible">
      <div className="collapsible-header" onClick={() => setOpen(!open)}>
        <div className="collapsible-header-left">
          <TrendingUp size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Projection Window & Forecasting</span>
        </div>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>
      {open && (
        <div className="card-body" style={{ borderTop: '1px solid var(--color-border)' }}>
          <div className="slider-row">
            <div className="slider-row-header">
              <span className="slider-row-label">Forecast Horizon</span>
              <div className="slider-row-value">
                <span className="slider-row-value-num">30</span>
                <span className="slider-row-value-unit">days</span>
              </div>
            </div>
            <div className="slider-track">
              <div className="slider-fill" style={{ width: '33%' }} />
              <div className="slider-thumb" style={{ left: 'calc(33% - 8px)' }} />
            </div>
          </div>

          <div className="info-box" style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <Info size={14} style={{ color: 'var(--color-muted-foreground)', flexShrink: 0, marginTop: 1 }} />
            <p>
              Projections use linear scaling from single-run simulation results.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
