import { useState, useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';

const PADDING = { top: 10, right: 10, bottom: 20, left: 10 };

export default function PowerFlowChart() {
  const { results } = useSimulation();
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ width: 800, height: 200 });
  const [hoverIndex, setHoverIndex] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDims({ width: Math.max(200, width), height: Math.max(100, height) });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  if (!results || !results.demand_chart) return null;

  const chartData = results.demand_chart;
  const hours = chartData.hours || [];
  const activePower = chartData.optimized_mw || [];
  
  // Calculate reactive power (MVAr) ~ 0.3 * activePower
  const reactivePower = activePower.map(v => v * 0.3);
  
  // Calculate total losses (MW) ~ 0.035 * activePower
  const totalLosses = activePower.map(v => v * 0.035);

  const totalPoints = hours.length;
  if (totalPoints === 0) return null;

  // Y-axis max
  const maxActive = Math.max(...activePower, 1.0);
  const maxVal = Math.ceil(maxActive * 1.2);

  const chartW = dims.width - PADDING.left - PADDING.right;
  const chartH = dims.height - PADDING.top - PADDING.bottom;

  function scaleX(i) {
    return PADDING.left + (i / (totalPoints - 1)) * chartW;
  }

  function scaleY(v) {
    return PADDING.top + chartH - (v / maxVal) * chartH;
  }

  function buildAreaPath(data) {
    if (data.length === 0) return '';
    const points = data.map((v, i) => `${scaleX(i)},${scaleY(v)}`).join(' L');
    const baseline = `${scaleX(totalPoints - 1)},${PADDING.top + chartH} L${scaleX(0)},${PADDING.top + chartH}`;
    return `M${points} L${baseline} Z`;
  }

  function buildLinePath(data) {
    if (data.length === 0) return '';
    return 'M' + data.map((v, i) => `${scaleX(i)},${scaleY(v)}`).join(' L');
  }

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const relativeX = mouseX - PADDING.left;
    const pct = Math.max(0, Math.min(1, relativeX / chartW));
    const targetIdx = Math.round(pct * (totalPoints - 1));

    setHoverIndex(targetIdx);
    setTooltipPos({ x: mouseX, y: mouseY });
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const hoveredHour = hoverIndex !== null ? hours[hoverIndex] : null;
  const hoveredActive = hoverIndex !== null ? activePower[hoverIndex] : null;
  const hoveredReactive = hoverIndex !== null ? reactivePower[hoverIndex] : null;
  const hoveredLosses = hoverIndex !== null ? totalLosses[hoverIndex] : null;

  const legendItems = [
    { label: 'Active Power (MW)', color: 'var(--color-chart-blue)' },
    { label: 'Reactive Power (MVAr)', color: '#a78bfa' },
    { label: 'Total Losses (MW)', color: 'var(--color-chart-red)' },
  ];

  return (
    <div className="chart-placeholder" style={{ position: 'relative' }}>
      <div className="chart-placeholder-header">
        <span className="chart-placeholder-title">Time-Series Power Flow (24h)</span>
        <span className="chart-placeholder-id">SIM_GRID_01</span>
      </div>

      <div className="chart-area" ref={containerRef} style={{ overflow: 'visible' }}>
        <svg
          width="100%"
          height="100%"
          style={{ display: 'block', overflow: 'visible' }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onTouchMove={(e) => handleMouseMove(e.touches[0])}
          onTouchEnd={handleMouseLeave}
        >
          {/* Grid lines */}
          {Array.from({ length: 5 }, (_, idx) => (maxVal / 4) * idx).map((v) => (
            <line
              key={v}
              x1={PADDING.left}
              y1={scaleY(v)}
              x2={dims.width - PADDING.right}
              y2={scaleY(v)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Active Power area */}
          <path d={buildAreaPath(activePower)} fill="var(--color-chart-blue)" fillOpacity="0.12" style={{ transition: 'd 0.2s' }} />
          <path d={buildLinePath(activePower)} fill="none" stroke="var(--color-chart-blue)" strokeWidth="2" style={{ transition: 'd 0.2s' }} />

          {/* Reactive Power area */}
          <path d={buildAreaPath(reactivePower)} fill="#a78bfa" fillOpacity="0.1" style={{ transition: 'd 0.2s' }} />
          <path d={buildLinePath(reactivePower)} fill="none" stroke="#a78bfa" strokeWidth="2" style={{ transition: 'd 0.2s' }} />

          {/* Total Losses area */}
          <path d={buildAreaPath(totalLosses)} fill="var(--color-chart-red)" fillOpacity="0.15" style={{ transition: 'd 0.2s' }} />
          <path d={buildLinePath(totalLosses)} fill="none" stroke="var(--color-chart-red)" strokeWidth="1.5" style={{ transition: 'd 0.2s' }} />

          {/* Hover Crosshair & Circles */}
          {hoverIndex !== null && (
            <>
              {/* Tracker Line */}
              <line
                x1={scaleX(hoverIndex)}
                y1={PADDING.top}
                x2={scaleX(hoverIndex)}
                y2={PADDING.top + chartH}
                stroke="var(--color-muted-foreground)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />

              {/* Active Circle */}
              <circle
                cx={scaleX(hoverIndex)}
                cy={scaleY(hoveredActive)}
                r="4"
                fill="var(--color-chart-blue)"
                stroke="white"
                strokeWidth="1.5"
              />

              {/* Reactive Circle */}
              <circle
                cx={scaleX(hoverIndex)}
                cy={scaleY(hoveredReactive)}
                r="4"
                fill="#a78bfa"
                stroke="white"
                strokeWidth="1.5"
              />

              {/* Losses Circle */}
              <circle
                cx={scaleX(hoverIndex)}
                cy={scaleY(hoveredLosses)}
                r="4"
                fill="var(--color-chart-red)"
                stroke="white"
                strokeWidth="1.5"
              />
            </>
          )}

          {/* X-axis labels */}
          {hours.map((h, i) => {
            const showLabel = totalPoints <= 13 || i % Math.ceil(totalPoints / 8) === 0 || i === totalPoints - 1;
            if (!showLabel) return null;
            return (
              <text
                key={h}
                x={scaleX(i)}
                y={dims.height - 4}
                textAnchor="middle"
                fontSize="9"
                fill="var(--color-muted-foreground)"
                style={{ userSelect: 'none' }}
              >
                {`${String(h).padStart(2, '0')}:00`}
              </text>
            );
          })}
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

      {/* Floating Tooltip */}
      {hoverIndex !== null && (
        <div
          style={{
            position: 'absolute',
            pointerEvents: 'none',
            left: tooltipPos.x + 15,
            top: tooltipPos.y - 45,
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 12px',
            color: 'white',
            fontSize: 'var(--text-xs)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 100,
            minWidth: 160,
            transform: tooltipPos.x > dims.width - 180 ? 'translateX(-110%)' : 'none'
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 4, color: 'var(--color-muted-foreground)' }}>
            Hour: {String(hoveredHour).padStart(2, '0')}:00
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 2 }}>
            <span style={{ color: 'var(--color-chart-blue)' }}>Active Power:</span>
            <span style={{ fontWeight: 600 }}>{hoveredActive.toFixed(2)} MW</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 2 }}>
            <span style={{ color: '#a78bfa' }}>Reactive:</span>
            <span style={{ fontWeight: 600 }}>{hoveredReactive.toFixed(2)} MVAr</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
            <span style={{ color: 'var(--color-chart-red)' }}>Losses:</span>
            <span style={{ fontWeight: 600 }}>{hoveredLosses.toFixed(3)} MW</span>
          </div>
        </div>
      )}
    </div>
  );
}
