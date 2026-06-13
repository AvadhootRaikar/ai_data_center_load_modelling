import { useState } from 'react';
import { Play, Download, Clock } from 'lucide-react';
import MetricCard from '../components/shared/MetricCard';
import ProjectionsTable from '../components/energy-overview/ProjectionsTable';
import GridHealthPanel from '../components/energy-overview/GridHealthPanel';
import AlertCards from '../components/energy-overview/AlertCards';

const TABS = ['Current', 'Grid', 'Cost'];

const METRICS = [
  { label: 'Baseline Facility Energy', value: '142.8', unit: 'MWh', change: '+2.4', changePct: '1.7', positive: false },
  { label: 'Current Facility Energy', value: '124.5', unit: 'MWh', change: '-18.3', changePct: '12.8', positive: true },
  { label: 'Weighted Avg Power', value: '8.42', unit: 'MW', change: '-0.91', changePct: '9.7', positive: true },
  { label: 'Peak Facility Power', value: '11.2', unit: 'MW', change: '-1.4', changePct: '11.1', positive: true },
];

export default function EnergyOverview() {
  const [activeTab, setActiveTab] = useState('Current');

  return (
    <>
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1>Overview &amp; Model Sanity</h1>
          <div className="page-header-meta">
            <span>
              <Clock size={12} />
              LAST SUCCESSFUL RUN: <strong>TODAY, 14:02:11</strong>
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
          <button className="btn">
            <Download size={14} />
            Export CSV
          </button>
          <button className="btn btn-primary">
            <Play size={14} />
            Run Simulation
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
