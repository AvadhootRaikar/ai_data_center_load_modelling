import { Clock } from 'lucide-react';

function SliderRow({ label, value, unit, fillPercent }) {
  return (
    <div className="slider-row">
      <div className="slider-row-header">
        <span className="slider-row-label">{label}</span>
        <div className="slider-row-value">
          <span className="slider-row-value-num">{value}</span>
          {unit && <span className="slider-row-value-unit">{unit}</span>}
        </div>
      </div>
      <div className="slider-track">
        <div className="slider-fill" style={{ width: `${fillPercent}%` }} />
        <div className="slider-thumb" style={{ left: `calc(${fillPercent}% - 8px)` }} />
      </div>
    </div>
  );
}

export default function SchedulingPricingPanel() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Clock size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Scheduling & Pricing</span>
        </div>
      </div>
      <div className="card-body">
        <SliderRow
          label="Execution Window"
          value="24"
          unit="hrs"
          fillPercent={100}
        />
        <SliderRow
          label="Base Energy Rate"
          value="0.12"
          unit="EUR/kWh"
          fillPercent={30}
        />
      </div>
    </div>
  );
}
