const WIDTH = 800;
const HEIGHT = 200;
const PADDING = { top: 10, right: 10, bottom: 20, left: 10 };

// 24 hourly data points (indices 0–23)
const hours = Array.from({ length: 24 }, (_, i) => i);

// Active Power (MW) — peaks around hour 14 at ~11 MW
const activePower = [
  3.2, 2.8, 2.5, 2.4, 2.6, 3.1, 4.5, 6.2, 7.8, 8.9,
  9.6, 10.2, 10.8, 11.0, 11.2, 10.5, 9.8, 8.4, 7.1, 5.9,
  5.0, 4.3, 3.8, 3.4,
];

// Reactive Power (MVAr) — peaks ~3.5
const reactivePower = [
  1.0, 0.9, 0.8, 0.7, 0.8, 1.0, 1.4, 2.0, 2.5, 2.8,
  3.0, 3.2, 3.4, 3.5, 3.4, 3.3, 3.0, 2.6, 2.2, 1.8,
  1.5, 1.3, 1.1, 1.0,
];

// Total Losses (MW) — peaks ~0.4
const totalLosses = [
  0.08, 0.06, 0.05, 0.05, 0.06, 0.08, 0.12, 0.18, 0.24, 0.28,
  0.31, 0.34, 0.37, 0.39, 0.40, 0.36, 0.32, 0.26, 0.20, 0.16,
  0.13, 0.11, 0.09, 0.08,
];

const maxVal = 12; // Y-axis max

function scaleX(i) {
  return PADDING.left + (i / 23) * (WIDTH - PADDING.left - PADDING.right);
}

function scaleY(v) {
  return HEIGHT - PADDING.bottom - (v / maxVal) * (HEIGHT - PADDING.top - PADDING.bottom);
}

function buildAreaPath(data) {
  const points = data.map((v, i) => `${scaleX(i)},${scaleY(v)}`).join(' L');
  const baseline = `${scaleX(23)},${scaleY(0)} L${scaleX(0)},${scaleY(0)}`;
  return `M${points} L${baseline} Z`;
}

function buildLinePath(data) {
  return 'M' + data.map((v, i) => `${scaleX(i)},${scaleY(v)}`).join(' L');
}

const legendItems = [
  { label: 'Active Power (MW)', color: 'var(--color-chart-blue)' },
  { label: 'Reactive Power (MVAr)', color: '#a78bfa' },
  { label: 'Total Losses (MW)', color: 'var(--color-chart-red)' },
];

export default function PowerFlowChart() {
  return (
    <div className="chart-placeholder">
      <div className="chart-placeholder-header">
        <span className="chart-placeholder-title">Time-Series Power Flow (24h)</span>
        <span className="chart-placeholder-id">SIM_GRID_01</span>
      </div>

      <div className="chart-area">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: '100%' }}
        >
          {/* Grid lines */}
          {[0, 3, 6, 9, 12].map((v) => (
            <line
              key={v}
              x1={PADDING.left}
              y1={scaleY(v)}
              x2={WIDTH - PADDING.right}
              y2={scaleY(v)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Active Power area */}
          <path d={buildAreaPath(activePower)} fill="var(--color-chart-blue)" fillOpacity="0.15" />
          <path d={buildLinePath(activePower)} fill="none" stroke="var(--color-chart-blue)" strokeWidth="2" />

          {/* Reactive Power area */}
          <path d={buildAreaPath(reactivePower)} fill="#a78bfa" fillOpacity="0.15" />
          <path d={buildLinePath(reactivePower)} fill="none" stroke="#a78bfa" strokeWidth="2" />

          {/* Total Losses area */}
          <path d={buildAreaPath(totalLosses)} fill="var(--color-chart-red)" fillOpacity="0.2" />
          <path d={buildLinePath(totalLosses)} fill="none" stroke="var(--color-chart-red)" strokeWidth="1.5" />

          {/* X-axis labels */}
          {[0, 4, 8, 12, 16, 20, 23].map((h) => (
            <text
              key={h}
              x={scaleX(h)}
              y={HEIGHT - 4}
              textAnchor="middle"
              fontSize="9"
              fill="var(--color-muted-foreground)"
            >
              {`${String(h).padStart(2, '0')}:00`}
            </text>
          ))}
        </svg>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, marginTop: 12, justifyContent: 'center' }}>
        {legendItems.map((item) => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: item.color,
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
