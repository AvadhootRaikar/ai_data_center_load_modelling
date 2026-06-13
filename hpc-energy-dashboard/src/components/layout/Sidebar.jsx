import { HardDrive, Server, GitBranch, Clock, Play, ChevronRight } from 'lucide-react';

export default function Sidebar() {
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
          <p>Upload historical trace (.csv)</p>
          <div className="input-field" style={{ textAlign: 'center', color: 'var(--color-muted-foreground)', cursor: 'pointer' }}>
            Select File
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
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>1.25</span>
            </div>
            <div className="slider-track">
              <div className="slider-fill" style={{ width: '62%' }}></div>
              <div className="slider-thumb" style={{ left: 'calc(62% - 8px)' }}></div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-foreground)' }}>Hosting Mode</span>
            <div className="toggle-track active">
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
            PandaPower Solver: Enabled
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
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted-foreground)' }}>Method:</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>ASAP</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted-foreground)' }}>Optimization:</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-foreground)' }}>Cost-First</span>
            </div>
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <button className="btn btn-primary btn-block btn-lg">
          <Play size={13} />
          Run Simulation
        </button>
      </div>
    </aside>
  );
}
