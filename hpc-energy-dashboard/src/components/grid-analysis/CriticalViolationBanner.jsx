import { AlertCircle, ArrowRight } from 'lucide-react';

export default function CriticalViolationBanner() {
  return (
    <div className="violation-banner">
      <div className="violation-banner-content">
        <div className="violation-banner-icon">
          <AlertCircle size={16} />
        </div>
        <div>
          <div className="violation-banner-title">Critical Violation Detected</div>
          <div className="violation-banner-desc">
            Voltage dropped below 0.95 p.u. at timestep 420 (peak demand period)
          </div>
        </div>
      </div>
      <button className="btn btn-danger">
        Jump to Violation
        <ArrowRight size={13} />
      </button>
    </div>
  );
}
