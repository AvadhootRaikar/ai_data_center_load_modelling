import { Shield } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export default function SecurityChecksTable() {
  const { results } = useSimulation();
  
  const contingencyData = results?.security_checks || [];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Shield size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">N-1 Security Contingency Analysis</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
          {contingencyData.length} elements evaluated
        </span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Element</th>
            <th>Type</th>
            <th className="text-right">Pre-Fault Value</th>
            <th className="text-right">Post-Fault Value</th>
            <th className="text-right">Margin</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {contingencyData.map((row) => (
            <tr key={row.element}>
              <td className="font-medium">{row.element}</td>
              <td className="muted">{row.type}</td>
              <td className="text-right">{row.preFault}</td>
              <td className="text-right">{row.postFault}</td>
              <td className="text-right">{row.margin}</td>
              <td>
                <span className={`status-badge ${row.status === 'PASS' ? 'pass' : row.status === 'WARN' ? 'warn' : 'fail'}`}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
