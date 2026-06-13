export default function MetricCard({ label, value, unit, change, changePct, positive }) {
  const arrow = positive ? '▲' : '▼';
  const badgeClass = `metric-card-badge ${positive ? 'positive' : 'negative'}`;

  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <span className="metric-card-label">{label}</span>
        <span className={badgeClass}>
          {arrow} {change} ({changePct}%)
        </span>
      </div>
      <div className="metric-card-value">
        <span className="metric-card-number">{value}</span>
        <span className="metric-card-unit">{unit}</span>
      </div>
    </div>
  );
}
