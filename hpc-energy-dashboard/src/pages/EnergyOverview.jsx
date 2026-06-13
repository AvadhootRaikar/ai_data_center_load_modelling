import { useState } from 'react';
import { Play, Download, Clock, Loader2 } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext';
import MetricCard from '../components/shared/MetricCard';
import ProjectionsTable from '../components/energy-overview/ProjectionsTable';
import GridHealthPanel from '../components/energy-overview/GridHealthPanel';
import AlertCards from '../components/energy-overview/AlertCards';

const TABS = ['Current', 'Grid', 'Cost'];

export default function EnergyOverview() {
  const [activeTab, setActiveTab] = useState('Current');
  const { results, loading, runSimulation } = useSimulation();

  const metrics = results?.metrics || {
    baseline_energy: 142.8,
    current_energy: 124.5,
    energy_change_pct: 12.8,
    weighted_avg_power: 8.42,
    peak_power: 11.2
  };

  const energySaved = (metrics.baseline_energy - metrics.current_energy);

  const METRICS = [
    { 
      label: 'Baseline Facility Energy', 
      value: metrics.baseline_energy.toFixed(1), 
      unit: 'MWh', 
      change: 'Benchmark', 
      changePct: '0.0', 
      positive: true 
    },
    { 
      label: 'Current Facility Energy', 
      value: metrics.current_energy.toFixed(1), 
      unit: 'MWh', 
      change: `-${energySaved.toFixed(1)}`, 
      changePct: metrics.energy_change_pct.toString(), 
      positive: energySaved >= 0 
    },
    { 
      label: 'Weighted Avg Power', 
      value: metrics.weighted_avg_power.toFixed(2), 
      unit: 'MW', 
      change: metrics.weighted_avg_power < 9.0 ? 'Optimized' : 'Normal', 
      changePct: '9.7', 
      positive: true 
    },
    { 
      label: 'Peak Facility Power', 
      value: metrics.peak_power.toFixed(1), 
      unit: 'MW', 
      change: metrics.peak_power < 12.0 ? 'Stable' : 'High', 
      changePct: '11.1', 
      positive: true 
    },
  ];

  return (
    <>
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1>Overview &amp; Model Sanity</h1>
          <div className="page-header-meta">
            <span>
              <Clock size={12} />
              LAST SUCCESSFUL RUN: <strong>{loading ? 'SIMULATING...' : 'TODAY, 14:02:11'}</strong>
            </span>
          </div>
        </div>
        <div className="page-header-actions">
          <div className="segmented-control">
            {TABS.map((tab) => (
              <button
                key={tab}
                className={`segmented-btn ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
          <button className="btn" disabled style={{ opacity: 0.5 }}>
            <Download size={14} />
            Export CSV
          </button>
          <button 
            className="btn btn-primary" 
            onClick={runSimulation} 
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {loading ? 'Running...' : 'Run Simulation'}
          </button>
        </div>
      </div>

      {/* Split Layout */}
      <div className="split-layout">
        {/* Main Column */}
        <div className="split-main">
          <div className="grid-4">
            {METRICS.map((m) => (
              <MetricCard key={m.label} {...m} />
            ))}
          </div>
          <ProjectionsTable />
          <AlertCards />
        </div>

        {/* Right Panel */}
        <div className="right-panel">
          <GridHealthPanel />
        </div>
      </div>
    </>
  );
}

