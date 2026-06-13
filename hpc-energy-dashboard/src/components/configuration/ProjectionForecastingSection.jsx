import { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { TrendingUp, ChevronDown, ChevronRight, Info } from 'lucide-react';

export default function ProjectionForecastingSection() {
  const [open, setOpen] = useState(true);
  const { forecastHorizon, setForecastHorizon } = useSimulation();

  // Convert forecastHorizon to percentage for slider (range 7 to 365 days)
  const percent = Math.min(100, Math.max(0, ((forecastHorizon - 7) / (365 - 7)) * 100));

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
                <span className="slider-row-value-num">{forecastHorizon}</span>
                <span className="slider-row-value-unit">days</span>
              </div>
            </div>
            <div className="slider-track" style={{ position: 'relative' }}>
              <div className="slider-fill" style={{ width: `${percent}%` }} />
              <div className="slider-thumb" style={{ left: `calc(${percent}% - 8px)` }} />
              <input 
                type="range"
                min="7"
                max="365"
                step="1"
                value={forecastHorizon}
                onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
                style={{
                  position: 'absolute',
                  top: 0, left: 0, width: '100%', height: '100%',
                  opacity: 0, cursor: 'pointer'
                }}
              />
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
