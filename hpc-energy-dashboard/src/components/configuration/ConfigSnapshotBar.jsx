import { Cpu, Zap, Layers, Clock } from 'lucide-react';

const items = [
  {
    icon: Cpu,
    label: 'Total Compute Nodes',
    value: '64 × 8 = 512 Nodes',
  },
  {
    icon: Zap,
    label: 'Current Target PUE',
    value: '1.08',
  },
  {
    icon: Layers,
    label: 'Simulation Mode',
    value: 'Static Load Trace',
  },
  {
    icon: Clock,
    label: 'Pricing Method',
    value: 'EPEX SPOT (DE)',
  },
];

export default function ConfigSnapshotBar() {
  return (
    <div className="snapshot-bar">
      {items.map((item) => (
        <div className="snapshot-bar-item" key={item.label}>
          <div className="snapshot-bar-icon">
            <item.icon size={16} />
          </div>
          <div>
            <div className="snapshot-bar-label">{item.label}</div>
            <div className="snapshot-bar-value">{item.value}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
