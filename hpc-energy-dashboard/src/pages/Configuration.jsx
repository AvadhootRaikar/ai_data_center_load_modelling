import { useState } from 'react';
import { Save, Upload, Play, ChevronDown, ChevronRight, Clock } from 'lucide-react';

import ConfigSnapshotBar from '../components/configuration/ConfigSnapshotBar';
import WorkloadDataPanel from '../components/configuration/WorkloadDataPanel';
import FacilityAssumptionsPanel from '../components/configuration/FacilityAssumptionsPanel';
import WorkloadScenarioPanel from '../components/configuration/WorkloadScenarioPanel';
import SchedulingPricingPanel from '../components/configuration/SchedulingPricingPanel';
import PandaPowerSolverPanel from '../components/configuration/PandaPowerSolverPanel';
import CapacityAnalysisPanel from '../components/configuration/CapacityAnalysisPanel';
import ProjectionForecastingSection from '../components/configuration/ProjectionForecastingSection';

export default function Configuration() {
  const [delayedOpen, setDelayedOpen] = useState(false);

  return (
    <>
      {/* ── Toolbar ── */}
      <div className="toolbar">
        <div className="toolbar-left">
          <button className="btn" disabled title="Coming Soon" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
            <Save size={14} />
            Save Preset
          </button>
          <button className="btn" disabled title="Coming Soon" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
            <Upload size={14} />
            Load Preset
          </button>
        </div>
        <div className="toolbar-right">
          <div className="toolbar-status">
            <div className="toolbar-status-label">Status</div>
            <div className="toolbar-status-value">Ready to Run</div>
          </div>
          <button className="btn btn-primary btn-lg">
            <Play size={14} />
            Run Simulation
          </button>
        </div>
      </div>

      {/* ── Scrollable body ── */}
      <div className="scrollable-body">
        {/* Configuration Snapshot */}
        <div>
          <div className="section-label">Configuration Snapshot</div>
          <ConfigSnapshotBar />
        </div>

        {/* Row 1: Workload Data | Facility Assumptions | Workload Scenario */}
        <div className="grid-3">
          <WorkloadDataPanel />
          <FacilityAssumptionsPanel />
          <WorkloadScenarioPanel />
        </div>

        {/* Row 2: Scheduling & Pricing | PandaPower Solver | Capacity Analysis */}
        <div className="grid-3">
          <SchedulingPricingPanel />
          <PandaPowerSolverPanel />
          <CapacityAnalysisPanel />
        </div>

        {/* Projection & Forecasting */}
        <ProjectionForecastingSection />

        {/* Delayed Training Policy (collapsed) */}
        <div className="collapsible">
          <div className="collapsible-header" onClick={() => setDelayedOpen(!delayedOpen)}>
            <div className="collapsible-header-left">
              <Clock size={14} style={{ color: 'var(--color-muted-foreground)' }} />
              <span className="card-title">Delayed Training Policy</span>
            </div>
            {delayedOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </div>
          {delayedOpen && (
            <div className="card-body" style={{ borderTop: '1px solid var(--color-border)' }}>
              <div className="info-box">
                <p>
                  Configure policies to defer non-urgent training workloads to off-peak pricing windows.
                  Settings will be available after the first simulation run.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
