import { useState, useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Clock } from 'lucide-react';

const PAD = { top: 15, right: 50, bottom: 26, left: 50 };

export default function DemandChart({ title, id, color = '#3b82f6' }) {
  const { results } = useSimulation();
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ width: 580, height: 180 });
  const [hoverIndex, setHoverIndex] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        // set dimensions (minimum bounds to prevent division by zero)
        setDims({ width: Math.max(200, width), height: Math.max(100, height) });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  const chartData = results?.demand_chart || {
    hours: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
    baseline_mw: [2.1, 1.8, 1.6, 2.4, 3.8, 5.1, 5.6, 5.3, 4.7, 3.9, 2.8, 2.2, 2.0],
    optimized_mw: [1.8, 1.5, 1.4, 2.0, 3.2, 4.2, 4.8, 4.5, 3.8, 3.0, 2.2, 1.8, 1.7],
    price_eur_mwh: [28, 28, 28, 34, 34, 42, 42, 42, 38, 38, 26, 26, 26],
  };

  const isBaseline = id.includes("BASE");
  const mwData = isBaseline ? chartData.baseline_mw : chartData.optimized_mw;

  const chartW = dims.width - PAD.left - PAD.right;
  const chartH = dims.height - PAD.top - PAD.bottom;

  function scaleX(hour) {
    return PAD.left + (hour / 24) * chartW;
  }

  // Auto-scale MW axis
  const maxMW = Math.max(...chartData.baseline_mw, ...chartData.optimized_mw, 2.0) * 1.2;
  const maxPrice = Math.max(...chartData.price_eur_mwh, 40) * 1.2;

  function scaleMW(mw) {
    return PAD.top + chartH - (mw / maxMW) * chartH;
  }

  function scalePrice(p) {
    return PAD.top + chartH - (p / maxPrice) * chartH;
  }

  const demandPoints = chartData.hours.map((hour, idx) => ({
    hour,
    mw: mwData[idx] || 0
  }));

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
  const pricePath = chartData.hours
    .map((h, i) => `${i === 0 ? 'M' : 'L'}${scaleX(h)},${scalePrice(chartData.price_eur_mwh[i] || 30)}`)
    .join(' ');

  // Y-axis ticks
  const mwTicks = [0, maxMW * 0.33, maxMW * 0.66, maxMW].map(v => Math.round(v * 10) / 10);
  const priceTicks = [0, maxPrice * 0.5, maxPrice].map(v => Math.round(v));
  const xTicks = [0, 6, 12, 18, 24];

  // Mouse Handlers
  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Calculate nearest hour index
    const relativeX = mouseX - PAD.left;
    const pct = Math.max(0, Math.min(1, relativeX / chartW));
    const targetHour = pct * 24;
    
    // Find closest index in hours array
    let minDiff = Infinity;
    let nearestIdx = 0;
    chartData.hours.forEach((h, i) => {
      const diff = Math.abs(h - targetHour);
      if (diff < minDiff) {
        minDiff = diff;
        nearestIdx = i;
      }
    });

    setHoverIndex(nearestIdx);
    setTooltipPos({ x: mouseX, y: mouseY });
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const hoveredHour = hoverIndex !== null ? chartData.hours[hoverIndex] : null;
  const hoveredMW = hoverIndex !== null ? mwData[hoverIndex] : null;
  const hoveredPrice = hoverIndex !== null ? chartData.price_eur_mwh[hoverIndex] : null;

  return (
    <div className="chart-placeholder" style={{ position: 'relative' }}>
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
          {mwTicks.map((t) => (
            <line
              key={`g-${t}`}
              x1={PAD.left}
              y1={scaleMW(t)}
              x2={dims.width - PAD.right}
              y2={scaleMW(t)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Area fill */}
          <path d={areaPath} fill={color} opacity="0.15" style={{ transition: 'd 0.2s' }} />

          {/* Demand line */}
          <path d={linePath} fill="none" stroke={color} strokeWidth="2" style={{ transition: 'd 0.2s' }} />

          {/* Price line */}
          <path d={pricePath} fill="none" stroke="var(--color-danger)" strokeWidth="1.5" strokeDasharray="4 2" style={{ transition: 'd 0.2s' }} />

          {/* Hover Crosshairs & Dots */}
          {hoverIndex !== null && (
            <>
              {/* Vertical line */}
              <line
                x1={scaleX(hoveredHour)}
                y1={PAD.top}
                x2={scaleX(hoveredHour)}
                y2={PAD.top + chartH}
                stroke="var(--color-muted-foreground)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              
              {/* Power marker */}
              <circle
                cx={scaleX(hoveredHour)}
                cy={scaleMW(hoveredMW)}
                r="4"
                fill={color}
                stroke="white"
                strokeWidth="1.5"
              />

              {/* Price marker */}
              <circle
                cx={scaleX(hoveredHour)}
                cy={scalePrice(hoveredPrice)}
                r="4"
                fill="var(--color-danger)"
                stroke="white"
                strokeWidth="1.5"
              />
            </>
          )}

          {/* Left y-axis labels — MW */}
          {mwTicks.map((t) => (
            <text
              key={`ml-${t}`}
              x={PAD.left - 8}
              y={scaleMW(t) + 3}
              textAnchor="end"
              fontSize="9"
              fill="var(--color-muted-foreground)"
              style={{ userSelect: 'none' }}
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
            style={{ userSelect: 'none' }}
          >
            Power (MW)
          </text>

          {/* Right y-axis labels — EUR/MWh */}
          {priceTicks.map((t) => (
            <text
              key={`pr-${t}`}
              x={dims.width - PAD.right + 8}
              y={scalePrice(t) + 3}
              textAnchor="start"
              fontSize="9"
              fill="var(--color-muted-foreground)"
              style={{ userSelect: 'none' }}
            >
              €{t}
            </text>
          ))}
          <text
            x={dims.width - 12}
            y={PAD.top + chartH / 2}
            textAnchor="middle"
            fontSize="8"
            fill="var(--color-muted-foreground)"
            transform={`rotate(90, ${dims.width - 12}, ${PAD.top + chartH / 2})`}
            style={{ userSelect: 'none' }}
          >
            EUR/MWh
          </text>

          {/* X-axis labels */}
          {xTicks.map((t) => (
            <text
              key={`x-${t}`}
              x={scaleX(t)}
              y={dims.height - 4}
              textAnchor="middle"
              fontSize="9"
              fill="var(--color-muted-foreground)"
              style={{ userSelect: 'none' }}
            >
              {String(t).padStart(2, '0')}:00
            </text>
          ))}
        </svg>
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
            minWidth: 120,
            transform: tooltipPos.x > dims.width - 150 ? 'translateX(-115%)' : 'none'
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 4, color: 'var(--color-muted-foreground)' }}>
            Hour: {String(hoveredHour).padStart(2, '0')}:00
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
            <span style={{ color: color }}>Power:</span>
            <span style={{ fontWeight: 600 }}>{hoveredMW.toFixed(2)} MW</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
            <span style={{ color: 'var(--color-danger)' }}>Grid Price:</span>
            <span style={{ fontWeight: 600 }}>€{hoveredPrice.toFixed(0)}/MWh</span>
          </div>
        </div>
      )}
    </div>
  );
}
