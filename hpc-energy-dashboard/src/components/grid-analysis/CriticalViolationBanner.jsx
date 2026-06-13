import { AlertCircle, ArrowRight } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export default function CriticalViolationBanner() {
  const { results } = useSimulation();

  if (!results) return null;

  // Search for voltage violation (<= 0.95 p.u.)
  const voltViolation = results.simulation_results_table?.find(
    (row) => parseFloat(row.voltage) <= 0.95
  );

  // Search for transformer load violation (>= 90%)
  const trafoLoad = results.grid_health?.transformer_load;
  const isTrafoViolation = trafoLoad >= 90.0;

  if (!voltViolation && !isTrafoViolation) {
    return null; // Don't show the banner if everything is healthy
  }

  let title = "Grid Violation Warning";
  let desc = "";

  if (voltViolation) {
    title = "Critical Voltage Violation";
    desc = `Voltage dropped below safety limit to ${voltViolation.voltage} at timestep ${voltViolation.timestep} (${voltViolation.time})`;
  } else if (isTrafoViolation) {
    title = "Critical Transformer Overload";
    desc = `Transformer loading reached critical levels at ${trafoLoad}% (limit: 90%)`;
  }

  return (
    <div className="violation-banner">
      <div className="violation-banner-content">
        <div className="violation-banner-icon">
          <AlertCircle size={16} />
        </div>
        <div>
          <div className="violation-banner-title">{title}</div>
          <div className="violation-banner-desc">{desc}</div>
        </div>
      </div>
      <button
        className="btn btn-danger"
        onClick={() => {
          // Scroll to the detailed results table
          const element = document.querySelector('.data-table');
          if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
          }
        }}
      >
        Jump to Details
        <ArrowRight size={13} />
      </button>
    </div>
  );
}

