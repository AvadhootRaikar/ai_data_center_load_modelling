import { Download, FileText } from 'lucide-react';
import CostMetricCards from '../components/cost-analysis/CostMetricCards';
import DemandChart from '../components/cost-analysis/DemandChart';
import CumulativeSavingsChart from '../components/cost-analysis/CumulativeSavingsChart';
import CostAnalysisPanel from '../components/cost-analysis/CostAnalysisPanel';
import EconomicProjectionPanel from '../components/cost-analysis/EconomicProjectionPanel';

export default function CostAnalysis() {
  return (
    <>
      {/* Page header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1>Synchronized Economic Timeline</h1>
          <div className="page-header-meta">
            <span>
              Power demand vs. <strong>Market Price Index (EUR/MWh)</strong>
            </span>
            <span>
              Source: <strong>EPEX SPOT (DE)</strong>
            </span>
          </div>
        </div>
        <div className="page-header-actions">
          <button className="btn" disabled style={{ opacity: 0.5 }}>
            <Download size={14} />
            Export Figure
          </button>
          <button className="btn">
            <FileText size={14} />
            Data Specs
          </button>
        </div>
      </div>

      {/* Split layout */}
      <div className="split-layout">
        {/* Main column */}
        <div className="split-main">
          <CostMetricCards />

          <DemandChart
            title="Baseline Demand & Pricing Overlay"
            id="SIM_BASE_01"
            color="#94a3b8"
          />

          <DemandChart
            title="Optimized Scenario & Pricing Overlay"
            id="SIM_OPT_04"
            color="#3b82f6"
          />

          <CumulativeSavingsChart />
        </div>

        {/* Right panel */}
        <div className="right-panel" style={{ width: 290 }}>
          <CostAnalysisPanel />
          <EconomicProjectionPanel />
        </div>
      </div>
    </>
  );
}
