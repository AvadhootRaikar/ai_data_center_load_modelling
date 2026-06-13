import { Zap, TrendingDown, Leaf, PiggyBank } from 'lucide-react';

const metrics = [
  {
    label: 'Daily Energy Cost',
    value: '1,842',
    unit: 'EUR',
    delta: '+3.2%',
    deltaType: 'negative',
    icon: Zap,
  },
  {
    label: 'Peak Demand Charge',
    value: '426',
    unit: 'EUR',
    delta: '−1.8%',
    deltaType: 'positive',
    icon: TrendingDown,
  },
  {
    label: 'Carbon Tax Exposure',
    value: '312',
    unit: 'EUR',
    delta: '−4.1%',
    deltaType: 'positive',
    icon: Leaf,
  },
  {
    label: 'Net Savings',
    value: '892',
    unit: 'EUR',
    delta: '+12.6%',
    deltaType: 'positive',
    icon: PiggyBank,
  },
];

export default function CostMetricCards() {
  return (
    <div className="grid-4">
      {metrics.map((m) => {
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
