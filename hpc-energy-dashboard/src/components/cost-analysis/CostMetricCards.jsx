import { useSimulation } from '../../context/SimulationContext';
import { Zap, TrendingDown, Leaf, PiggyBank } from 'lucide-react';

export default function CostMetricCards() {
  const { results } = useSimulation();

  const metrics = results?.metrics || {
    baseline_cost: 15000,
    current_cost: 11250,
    cost_change_pct: 25.0,
    baseline_carbon: 2219,
    current_carbon: 710
  };

  const baselineCost = metrics.baseline_cost;
  const currentCost = metrics.current_cost;
  const costChangePct = metrics.cost_change_pct;
  const carbonTax = metrics.current_carbon * 0.05; // 0.05 EUR per kg CO2
  const baselineCarbonTax = metrics.baseline_carbon * 0.05;
  const netSavings = Math.max(0, baselineCost - currentCost);

  const displayMetrics = [
    {
      label: 'Daily Energy Cost',
      value: currentCost.toLocaleString(undefined, { maximumFractionDigits: 0 }),
      unit: 'EUR',
      delta: `${costChangePct >= 0 ? '-' : '+'}${Math.abs(costChangePct).toFixed(1)}%`,
      deltaType: costChangePct >= 0 ? 'positive' : 'negative',
      icon: Zap,
    },
    {
      label: 'Peak Demand Charge',
      value: (currentCost * 0.15).toLocaleString(undefined, { maximumFractionDigits: 0 }),
      unit: 'EUR',
      delta: costChangePct >= 0 ? '−1.8%' : '+1.2%',
      deltaType: costChangePct >= 0 ? 'positive' : 'negative',
      icon: TrendingDown,
    },
    {
      label: 'Carbon Tax Exposure',
      value: carbonTax.toLocaleString(undefined, { maximumFractionDigits: 0 }),
      unit: 'EUR',
      delta: `−${((baselineCarbonTax - carbonTax) / Math.max(1, baselineCarbonTax) * 100).toFixed(1)}%`,
      deltaType: carbonTax < baselineCarbonTax ? 'positive' : 'negative',
      icon: Leaf,
    },
    {
      label: 'Net Savings',
      value: netSavings.toLocaleString(undefined, { maximumFractionDigits: 0 }),
      unit: 'EUR',
      delta: `+${costChangePct.toFixed(1)}%`,
      deltaType: 'positive',
      icon: PiggyBank,
    },
  ];

  return (
    <div className="grid-4">
      {displayMetrics.map((m) => {
        const Icon = m.icon;
        return (
          <div key={m.label} className="metric-card">
            <div className="metric-card-header">
              <span className="metric-card-label">{m.label}</span>
              <span className={`metric-card-badge ${m.deltaType}`}>
                {m.delta}
              </span>
            </div>
            <div className="metric-card-value">
              <span className="metric-card-number">€{m.value}</span>
              <span className="metric-card-unit">{m.unit}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon size={14} style={{ color: 'var(--color-muted-foreground)' }} />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
                {m.deltaType === 'positive' ? '↓' : '↑'} vs. Baseline
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

