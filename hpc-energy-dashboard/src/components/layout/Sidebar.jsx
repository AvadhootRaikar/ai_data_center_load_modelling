import { useSimulation } from '../../context/SimulationContext';
import { HardDrive, Server, GitBranch, Clock, Play, ChevronRight, Loader2 } from 'lucide-react';

export default function Sidebar() {
  const {
    workloadMode,
    trainingFile,
    inferenceFile,
    targetPue, setTargetPue,
    enableCoolingUpgrade, setEnableCoolingUpgrade,
    runSimulation,
    loading,
    optimizationGoal,
    hasRun
  } = useSimulation();

  const currentPue = enableCoolingUpgrade ? Math.max(1.10, targetPue - 0.15) : targetPue;
  const percent = Math.min(100, Math.max(0, ((currentPue - 1.10) / (2.00 - 1.10)) * 100));

  const activeWorkloadFile = workloadMode === 'Training Run' ? trainingFile : (workloadMode === 'Inference Run' ? inferenceFile : `${trainingFile} + ${inferenceFile}`);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-header-title">Simulation Engine</span>
        <ChevronRight size={14} style={{ color: 'var(--color-muted-foreground)' }} />
      </div>

      <div className="sidebar-body">
        {/* Workload Data */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <HardDrive size={13} style={{ color: 'var(--color-muted-foreground)' }} />
            <span className="sidebar-section-title">Workload Data</span>
          </div>
          <p>Active Workload: <strong>{workloadMode}</strong></p>
          <div className="input-field" style={{ textAlign: 'center', color: 'var(--color-foreground)', fontSize: 'var(--text-xs)' }}>
            {activeWorkloadFile}
          </div>
        </div>

        {/* HPC Facility */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <Server size={13} style={{ color: 'var(--color-muted-foreground)' }} />
            <span className="sidebar-section-title">HPC Facility</span>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-foreground)' }}>Target PUE</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>{currentPue.toFixed(2)}</span>
            </div>
            <div className="slider-track" style={{ position: 'relative' }}>
              <div className="slider-fill" style={{ width: `${percent}%` }}></div>
              <div className="slider-thumb" style={{ left: `calc(${percent}% - 8px)` }}></div>
              <input 
                type="range"
                min="1.10"
                max="2.00"
                step="0.05"
                value={currentPue}
                onChange={(e) => setTargetPue(parseFloat(e.target.value))}
                style={{
                  position: 'absolute',
                  top: 0, left: 0, width: '100%', height: '100%',
                  opacity: 0, cursor: 'pointer'
                }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-foreground)' }}>Liquid Cooling</span>
            <div 
              className={`toggle-track ${enableCoolingUpgrade ? 'active' : ''}`}
              onClick={() => setEnableCoolingUpgrade(!enableCoolingUpgrade)}
              style={{ cursor: 'pointer' }}
            >
              <div className="toggle-knob"></div>
            </div>
          </div>
        </div>

        {/* Grid Topology */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <GitBranch size={13} style={{ color: 'var(--color-muted-foreground)' }} />
            <span className="sidebar-section-title">Grid Topology</span>
          </div>
          <div className="input-field" style={{ color: 'var(--color-foreground)' }}>
            PandaPower Solver: Active
          </div>
        </div>

        {/* Scheduling */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <Clock size={13} style={{ color: 'var(--color-muted-foreground)' }} />
            <span className="sidebar-section-title">Scheduling</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted-foreground)' }}>Goal:</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>{optimizationGoal}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted-foreground)' }}>Status:</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>{loading ? 'Simulating...' : (hasRun ? 'Calculated' : 'Idle')}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <button 
          className="btn btn-primary btn-block btn-lg" 
          onClick={runSimulation} 
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {loading ? 'Running...' : 'Run Simulation'}
        </button>
      </div>
    </aside>
  );
}

