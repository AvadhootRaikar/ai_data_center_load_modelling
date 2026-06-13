import { useSimulation } from '../../context/SimulationContext';
import { Cpu, Zap, Layers, Clock } from 'lucide-react';

export default function ConfigSnapshotBar() {
  const { nodesPerCenter, numberOfCenters, targetPue, enableCoolingUpgrade, workloadMode } = useSimulation();
  
  const currentPue = enableCoolingUpgrade ? Math.max(1.10, targetPue - 0.15) : targetPue;
  const totalNodes = nodesPerCenter * numberOfCenters;

  const items = [
    {
      icon: Cpu,
      label: 'Total Compute Nodes',
      value: `${nodesPerCenter} × ${numberOfCenters} = ${totalNodes} Nodes`,
    },
    {
      icon: Zap,
      label: 'Current Target PUE',
      value: currentPue.toFixed(2),
    },
    {
      icon: Layers,
      label: 'Simulation Mode',
      value: workloadMode,
    },
    {
      icon: Clock,
      label: 'Pricing Method',
      value: 'EPEX SPOT (DE)',
    },
  ];

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

