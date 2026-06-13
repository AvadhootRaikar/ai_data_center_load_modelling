import { Shield } from 'lucide-react';

const contingencyData = [
  {
    element: 'Trafo HV/MV',
    type: '110→20 kV Transformer',
    metric: 'Loading',
    preFault: '42.1%',
    postFault: '78.3%',
    margin: '21.7%',
    status: 'PASS',
  },
  {
    element: 'Line MV-01',
    type: '20 kV Cable',
    metric: 'Loading',
    preFault: '34.5%',
    postFault: '67.2%',
    margin: '32.8%',
    status: 'PASS',
  },
  {
    element: 'Line MV-02',
    type: '20 kV Cable',
    metric: 'Loading',
    preFault: '28.9%',
    postFault: '89.1%',
    margin: '10.9%',
    status: 'WARN',
  },
  {
    element: 'Trafo MV/LV-1',
    type: '20→0.4 kV Transformer',
    metric: 'Loading',
    preFault: '56.7%',
    postFault: '92.4%',
    margin: '7.6%',
    status: 'WARN',
  },
  {
    element: 'External Grid',
    type: 'Grid Connection',
    metric: 'Voltage',
    preFault: '1.00 p.u.',
    postFault: '0.97 p.u.',
    margin: '0.03 p.u.',
    status: 'PASS',
  },
];

export default function SecurityChecksTable() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Shield size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">N-1 Security Contingency Analysis</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
          5 elements evaluated
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
