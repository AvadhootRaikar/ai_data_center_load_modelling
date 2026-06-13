import { useSimulation } from '../../context/SimulationContext';
import { Clock } from 'lucide-react';

const goals = [
  'Minimize Cost',
  'Minimize Carbon',
  'Balanced'
];

export default function SchedulingPricingPanel() {
  const { 
    optimizationGoal, setOptimizationGoal,
    enableGpuLimiting, setEnableGpuLimiting,
    enableSmartScheduling, setEnableSmartScheduling,
    enableLoadBalancing, setEnableLoadBalancing
  } = useSimulation();

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Clock size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Scheduling & Pricing</span>
        </div>
      </div>
      <div className="card-body">
        <div style={{ marginBottom: 8 }}>
          <span className="slider-row-label" style={{ fontWeight: 600 }}>Optimization Goal</span>
        </div>
        <div className="segmented-control" style={{ flexDirection: 'column', gap: 6, background: 'none', padding: 0, marginBottom: 16 }}>
          {goals.map((goal) => (
            <button
              key={goal}
              className={`segmented-btn ${optimizationGoal === goal ? 'active' : ''}`}
              onClick={() => setOptimizationGoal(goal)}
              style={{ width: '100%', borderRadius: 'var(--radius-md)', padding: '8px 12px' }}
            >
              {goal.toUpperCase()}
            </button>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 16 }}>
          <span className="slider-row-label" style={{ display: 'block', marginBottom: 12, fontWeight: 600 }}>
            Optimization Strategies
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="toggle" onClick={() => setEnableGpuLimiting(!enableGpuLimiting)}>
              <div className={`toggle-track ${enableGpuLimiting ? 'active' : ''}`}>
                <div className="toggle-knob" />
              </div>
              <span className="toggle-label">GPU Power Capping (20%)</span>
            </div>

            <div className="toggle" onClick={() => setEnableSmartScheduling(!enableSmartScheduling)}>
              <div className={`toggle-track ${enableSmartScheduling ? 'active' : ''}`}>
                <div className="toggle-knob" />
              </div>
              <span className="toggle-label">Smart Workload Scheduling</span>
            </div>

            <div className="toggle" onClick={() => setEnableLoadBalancing(!enableLoadBalancing)}>
              <div className={`toggle-track ${enableLoadBalancing ? 'active' : ''}`}>
                <div className="toggle-knob" />
              </div>
              <span className="toggle-label">Center-Level Load Balancing</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

