import { useSimulation } from '../../context/SimulationContext';
import { BarChart2 } from 'lucide-react';

const workloadTypes = [
  { label: 'TRAINING', value: 'Training Run' },
  { label: 'INFERENCE', value: 'Inference Run' },
  { label: 'SIMULTANEOUS', value: 'Simultaneous Training + Inference' }
];

export default function WorkloadScenarioPanel() {
  const { workloadMode, setWorkloadMode } = useSimulation();

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
        <div className="segmented-control" style={{ flexDirection: 'column', gap: 6, background: 'none', padding: 0 }}>
          {workloadTypes.map((type) => (
            <button
              key={type.value}
              className={`segmented-btn ${workloadMode === type.value ? 'active' : ''}`}
              onClick={() => setWorkloadMode(type.value)}
              style={{ width: '100%', borderRadius: 'var(--radius-md)', padding: '8px 12px' }}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

