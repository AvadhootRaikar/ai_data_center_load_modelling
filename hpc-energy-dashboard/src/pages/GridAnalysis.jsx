import { Activity, Clock, Cpu } from 'lucide-react';
import PeakSnapshotSummary from '../components/grid-analysis/PeakSnapshotSummary';
import SecurityChecksTable from '../components/grid-analysis/SecurityChecksTable';
import PowerFlowChart from '../components/grid-analysis/PowerFlowChart';
import NetworkTopologyDiagram from '../components/grid-analysis/NetworkTopologyDiagram';
import SimulationResultsTable from '../components/grid-analysis/SimulationResultsTable';
import CriticalViolationBanner from '../components/grid-analysis/CriticalViolationBanner';

export default function GridAnalysis() {
  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1>Grid Analysis Report</h1>
          <div className="page-header-meta">
            <span>
              <Activity size={12} />
              Analytical deep-dive into the electrical physical constraints
            </span>
            <span>
              <Cpu size={12} />
              Solver engine: <strong>PandaPower v2.13.1</strong>
            </span>
            <span>
              <Clock size={12} />
              Last run: <strong>13 Jun 2026, 16:38</strong>
            </span>
          </div>
        </div>
      </div>

      <div className="scrollable-body">
        <CriticalViolationBanner />
        <PeakSnapshotSummary />
        <SecurityChecksTable />
        <PowerFlowChart />
        <NetworkTopologyDiagram />
        <SimulationResultsTable />
      </div>
    </>
  );
}
