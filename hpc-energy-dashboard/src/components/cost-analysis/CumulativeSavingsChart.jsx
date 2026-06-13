import { TrendingUp } from 'lucide-react';

// Cumulative savings curve — rises gradually, steeper during peak hours
const savingsData = [
  { hour: 0, eur: 0 },
  { hour: 2, eur: 18 },
  { hour: 4, eur: 42 },
  { hour: 6, eur: 85 },
  { hour: 8, eur: 168 },
  { hour: 10, eur: 312 },
  { hour: 12, eur: 465 },
  { hour: 14, eur: 586 },
  { hour: 16, eur: 692 },
  { hour: 18, eur: 778 },
  { hour: 20, eur: 838 },
  { hour: 22, eur: 872 },
  { hour: 24, eur: 892 },
];

const W = 580;
const H = 180;
const PAD = { top: 12, right: 20, bottom: 26, left: 50 };
const chartW = W - PAD.left - PAD.right;
const chartH = H - PAD.top - PAD.bottom;

const maxEur = 1000;

function sx(hour) {
  return PAD.left + (hour / 24) * chartW;
}
function sy(eur) {
  return PAD.top + chartH - (eur / maxEur) * chartH;
}

export default function CumulativeSavingsChart() {
  const linePath = savingsData
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.hour)},${sy(p.eur)}`)
    .join(' ');

  const areaPath =
    linePath +
    ` L${sx(24)},${PAD.top + chartH} L${sx(0)},${PAD.top + chartH} Z`;

  const yTicks = [0, 250, 500, 750, 1000];
  const xTicks = [0, 6, 12, 18, 24];

  return (
    <div className="chart-placeholder">
      <div className="chart-placeholder-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={16} style={{ color: 'var(--color-success)' }} />
          <span className="chart-placeholder-title">Cumulative Cost Savings (24h)</span>
        </div>
        <span
          className="metric-card-badge positive"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          +€892 today
        </span>
      </div>

      <div className="chart-area">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="none">
          {/* Horizontal grid */}
          {yTicks.map((t) => (
            <line
              key={t}
              x1={PAD.left}
              y1={sy(t)}
              x2={W - PAD.right}
              y2={sy(t)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Area fill */}
          <path d={areaPath} fill="var(--color-success)" opacity="0.12" />

          {/* Line */}
          <path d={linePath} fill="none" stroke="var(--color-success)" strokeWidth="2" />

          {/* End-point dot */}
          <circle cx={sx(24)} cy={sy(892)} r="3.5" fill="var(--color-success)" />

          {/* End-point label */}
          <text
            x={sx(24) - 6}
            y={sy(892) - 8}
            textAnchor="end"
            fontSize="10"
            fontWeight="700"
            fill="var(--color-success-foreground)"
          >
            €892
          </text>

          {/* Y-axis labels */}
          {yTicks.map((t) => (
            <text
              key={`y-${t}`}
              x={PAD.left - 8}
              y={sy(t) + 3}
              textAnchor="end"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              €{t}
            </text>
          ))}
          <text
            x={12}
            y={PAD.top + chartH / 2}
            textAnchor="middle"
            fontSize="8"
            fill="var(--color-muted-foreground)"
            transform={`rotate(-90, 12, ${PAD.top + chartH / 2})`}
          >
            Savings (EUR)
          </text>

          {/* X-axis labels */}
          {xTicks.map((t) => (
            <text
              key={`x-${t}`}
              x={sx(t)}
              y={H - 4}
              textAnchor="middle"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              {String(t).padStart(2, '0')}:00
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
