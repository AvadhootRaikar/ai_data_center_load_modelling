import { useState } from 'react';
import { BarChart2 } from 'lucide-react';

const workloadTypes = ['Training', 'Inference'];

export default function WorkloadScenarioPanel() {
  const [activeType, setActiveType] = useState('Training');

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <BarChart2 size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Workload Scenario</span>
        </div>
      </div>
      <div className="card-body">
        <div style={{ marginBottom: 8 }}>
          <span className="slider-row-label">Workload Type</span>
        </div>
        <div className="segmented-control">
          {workloadTypes.map((type) => (
            <button
              key={type}
              className={`segmented-btn ${activeType === type ? 'active' : ''}`}
              onClick={() => setActiveType(type)}
            >
              {type.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
