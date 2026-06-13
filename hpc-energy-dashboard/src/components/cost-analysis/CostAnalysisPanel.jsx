import { useSimulation } from '../../context/SimulationContext';
import { PieChart } from 'lucide-react';

// Build SVG donut arc segments
function polarToCartesian(cx, cy, r, angle) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export default function CostAnalysisPanel() {
  const { results, targetPue, enableCoolingUpgrade } = useSimulation();

  const metrics = results?.metrics || {
    current_cost: 11250,
    baseline_cost: 15000,
    current_energy: 124.5
  };

  const currentPue = enableCoolingUpgrade ? Math.max(1.10, targetPue - 0.15) : targetPue;
  const itPct = Math.round((1.0 / currentPue) * 78);
  const coolingPct = Math.round(((currentPue - 1.0) / currentPue) * 78);
  const carbonPct = 14;
  const otherPct = Math.max(2, 100 - itPct - coolingPct - carbonPct);

  const segments = [
    { label: 'Energy (IT)', pct: itPct, color: '#3b82f6' },
    { label: 'Cooling (PUE)', pct: coolingPct, color: '#8b5cf6' },
    { label: 'Carbon Tax', pct: carbonPct, color: '#f59e0b' },
    { label: 'Other Aux', pct: otherPct, color: '#94a3b8' },
  ];

  const cx = 70;
  const cy = 70;
  const r = 52;
  const strokeW = 16;

  let currentAngle = 0;
  const arcs = segments.map((seg) => {
    const startAngle = currentAngle;
    const sweep = (seg.pct / 100) * 360;
    currentAngle += sweep;
    return {
      ...seg,
      path: describeArc(cx, cy, r, startAngle, startAngle + sweep - 0.5),
    };
  });

  const dailyTotal = metrics.current_cost;
  const avgRate = dailyTotal / Math.max(0.1, metrics.current_energy);
  const annualProjection = dailyTotal * 365;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <PieChart size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">Cost Breakdown</span>
        </div>
      </div>
      <div className="card-body">
        {/* Donut chart */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
          <svg width="140" height="140" viewBox="0 0 140 140">
            {arcs.map((a) => (
              <path
                key={a.label}
                d={a.path}
                fill="none"
                stroke={a.color}
                strokeWidth={strokeW}
                strokeLinecap="round"
              />
            ))}
            <text
              x={cx}
              y={cy - 4}
              textAnchor="middle"
              fontSize="14"
              fontWeight="700"
              fill="var(--color-foreground)"
            >
              €{dailyTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </text>
            <text
              x={cx}
              y={cy + 12}
              textAnchor="middle"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              Daily Total
            </text>
          </svg>
        </div>

        {/* Legend items */}
        {segments.map((seg) => (
          <div key={seg.label} className="cost-breakdown-item">
            <div className="cost-breakdown-item-left">
              <span className="cost-breakdown-dot" style={{ background: seg.color }} />
              <span className="cost-breakdown-label">{seg.label}</span>
            </div>
            <span className="cost-breakdown-value">{seg.pct}%</span>
          </div>
        ))}

        {/* Divider */}
        <div style={{ borderTop: '1px solid var(--color-border)', margin: '12px 0' }} />

        {/* Summary rows */}
        <div className="cost-breakdown-item">
          <span className="cost-breakdown-label">Avg EUR/MWh</span>
          <span className="cost-breakdown-value">€{avgRate.toFixed(2)}</span>
        </div>
        <div className="cost-breakdown-item">
          <span className="cost-breakdown-label">Annual Projection</span>
          <span className="cost-breakdown-value">€{annualProjection.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
      </div>
    </div>
  );
}

