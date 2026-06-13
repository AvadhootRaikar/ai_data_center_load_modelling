import { Zap, Gauge, Activity, TrendingUp } from 'lucide-react';

const snapshots = [
  { label: 'Active Power', value: '11.2', unit: 'MW', icon: Zap },
  { label: 'Reactive Power', value: '3.4', unit: 'MVAr', icon: Activity },
  { label: 'Min Voltage', value: '0.96', unit: 'p.u.', icon: Gauge },
  { label: 'Max Line Load', value: '87.2', unit: '%', icon: TrendingUp },
];

export default function PeakSnapshotSummary() {
  return (
    <div className="peak-snapshot">
      {snapshots.map((item) => (
        <div key={item.label} className="peak-snapshot-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 4 }}>
            <item.icon size={13} style={{ color: 'var(--color-primary)', opacity: 0.7 }} />
            <div className="peak-snapshot-label">{item.label}</div>
          </div>
          <span className="peak-snapshot-value">{item.value}</span>{' '}
          <span className="peak-snapshot-unit">{item.unit}</span>
        </div>
      ))}
    </div>
  );
}
