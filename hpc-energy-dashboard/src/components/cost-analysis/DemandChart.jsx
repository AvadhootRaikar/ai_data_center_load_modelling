import { Clock } from 'lucide-react';

// Realistic demand data — higher midday, lower at night edges
const demandPoints = [
  { hour: 0, mw: 2.1 },
  { hour: 2, mw: 1.8 },
  { hour: 4, mw: 1.6 },
  { hour: 6, mw: 2.4 },
  { hour: 8, mw: 3.8 },
  { hour: 10, mw: 5.1 },
  { hour: 12, mw: 5.6 },
  { hour: 14, mw: 5.3 },
  { hour: 16, mw: 4.7 },
  { hour: 18, mw: 3.9 },
  { hour: 20, mw: 2.8 },
  { hour: 22, mw: 2.2 },
  { hour: 24, mw: 2.0 },
];

// 5-period EPEX SPOT-style stepped pricing
const priceSteps = [
  { start: 0, end: 5, price: 28 },
  { start: 5, end: 9, price: 34 },
  { start: 9, end: 15, price: 42 },
  { start: 15, end: 20, price: 38 },
  { start: 20, end: 24, price: 26 },
];

const W = 580;
const H = 180;
const PAD = { top: 10, right: 50, bottom: 26, left: 50 };
const chartW = W - PAD.left - PAD.right;
const chartH = H - PAD.top - PAD.bottom;

function scaleX(hour) {
  return PAD.left + (hour / 24) * chartW;
}

const maxMW = 6;
const maxPrice = 50;

function scaleMW(mw) {
  return PAD.top + chartH - (mw / maxMW) * chartH;
}

function scalePrice(p) {
  return PAD.top + chartH - (p / maxPrice) * chartH;
}

export default function DemandChart({ title, id, color = '#3b82f6' }) {
  // Build area path for demand
  const areaPath =
    demandPoints
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(p.hour)},${scaleMW(p.mw)}`)
      .join(' ') +
    ` L${scaleX(24)},${PAD.top + chartH} L${scaleX(0)},${PAD.top + chartH} Z`;

  const linePath = demandPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(p.hour)},${scaleMW(p.mw)}`)
    .join(' ');

  // Build stepped price line
  const pricePath = priceSteps
    .map(
      (s) =>
        `M${scaleX(s.start)},${scalePrice(s.price)} L${scaleX(s.end)},${scalePrice(s.price)}`
    )
    .join(' ');

  // Y-axis ticks
  const mwTicks = [0, 2, 4, 6];
  const priceTicks = [0, 20, 40];
  const xTicks = [0, 6, 12, 18, 24];

  return (
    <div className="chart-placeholder">
      <div className="chart-placeholder-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="chart-placeholder-title">{title}</span>
          <span className="chart-placeholder-id">{id}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block' }} />
            Power (MW)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
            <span style={{ width: 10, height: 2, background: 'var(--color-danger)', display: 'inline-block' }} />
            Price (EUR/MWh)
          </span>
          <Clock size={14} style={{ color: 'var(--color-muted-foreground)' }} />
        </div>
      </div>

      <div className="chart-area">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="none">
          {/* Grid lines */}
          {mwTicks.map((t) => (
            <line
              key={`g-${t}`}
              x1={PAD.left}
              y1={scaleMW(t)}
              x2={W - PAD.right}
              y2={scaleMW(t)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Area fill */}
          <path d={areaPath} fill={color} opacity="0.15" />

          {/* Demand line */}
          <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

          {/* Price stepped line */}
          <path d={pricePath} fill="none" stroke="var(--color-danger)" strokeWidth="1.5" strokeDasharray="4 2" />

          {/* Left y-axis labels — MW */}
          {mwTicks.map((t) => (
            <text
              key={`ml-${t}`}
              x={PAD.left - 8}
              y={scaleMW(t) + 3}
              textAnchor="end"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              {t}
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
            Power (MW)
          </text>

          {/* Right y-axis labels — EUR/MWh */}
          {priceTicks.map((t) => (
            <text
              key={`pr-${t}`}
              x={W - PAD.right + 8}
              y={scalePrice(t) + 3}
              textAnchor="start"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              €{t}
            </text>
          ))}
          <text
            x={W - 12}
            y={PAD.top + chartH / 2}
            textAnchor="middle"
            fontSize="8"
            fill="var(--color-muted-foreground)"
            transform={`rotate(90, ${W - 12}, ${PAD.top + chartH / 2})`}
          >
            EUR/MWh
          </text>

          {/* X-axis labels */}
          {xTicks.map((t) => (
            <text
              key={`x-${t}`}
              x={scaleX(t)}
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
