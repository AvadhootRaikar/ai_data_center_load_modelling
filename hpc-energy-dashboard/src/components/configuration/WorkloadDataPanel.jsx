import { useState } from 'react';
import { HardDrive } from 'lucide-react';

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

export default function WorkloadDataPanel() {
  const [advanced, setAdvanced] = useState(false);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <HardDrive size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Workload Data</span>
        </div>
        <div className="advanced-toggle" onClick={() => setAdvanced(!advanced)}>
          <span className="advanced-toggle-label">Advanced</span>
          <div className={`toggle-track ${advanced ? 'active' : ''}`}>
            <div className="toggle-knob" />
          </div>
        </div>
      </div>
      <div className="card-body">
        <div className="info-box">
          <p>Trace Source: <strong>llm_training_v4.csv</strong></p>
          <p>Total Datapoints: <strong>86,400</strong> (24h @ 1s)</p>
        </div>

        <SliderRow
          label="Scaling Factor"
          value="1"
          unit="x"
          fillPercent={20}
        />
        <SliderRow
          label="Compute Utilization"
          value="85"
          unit="%"
          fillPercent={85}
        />
      </div>
    </div>
  );
}
