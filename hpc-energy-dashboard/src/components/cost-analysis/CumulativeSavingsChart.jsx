import { useState, useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { TrendingUp } from 'lucide-react';

const PAD = { top: 15, right: 20, bottom: 26, left: 50 };

export default function CumulativeSavingsChart() {
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
        setDims({ width: Math.max(200, width), height: Math.max(100, height) });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  const savings = results?.cumulative_savings || {
    hours: Array.from({ length: 24 }, (_, i) => i),
    savings_eur: Array.from({ length: 24 }, (_, i) => i * 37)
  };

  const finalSavings = savings.savings_eur[savings.savings_eur.length - 1] || 0;
  const maxEur = Math.max(...savings.savings_eur, 100) * 1.15;

  const chartW = dims.width - PAD.left - PAD.right;
  const chartH = dims.height - PAD.top - PAD.bottom;

  function sx(hour) {
    return PAD.left + (hour / 23) * chartW;
  }

  function sy(eur) {
    return PAD.top + chartH - (eur / maxEur) * chartH;
  }

  const linePath = savings.hours
    .map((hour, i) => `${i === 0 ? 'M' : 'L'}${sx(hour)},${sy(savings.savings_eur[i] || 0)}`)
    .join(' ');

  const areaPath =
    linePath +
    ` L${sx(23)},${PAD.top + chartH} L${sx(0)},${PAD.top + chartH} Z`;

  const yTicks = [0, maxEur * 0.25, maxEur * 0.50, maxEur * 0.75, maxEur].map(v => Math.round(v));
  const xTicks = [0, 6, 12, 18, 23];

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const relativeX = mouseX - PAD.left;
    const pct = Math.max(0, Math.min(1, relativeX / chartW));
    const targetHour = pct * 23;

    let nearestIdx = Math.round(targetHour);
    nearestIdx = Math.max(0, Math.min(savings.hours.length - 1, nearestIdx));

    setHoverIndex(nearestIdx);
    setTooltipPos({ x: mouseX, y: mouseY });
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const hoveredHour = hoverIndex !== null ? savings.hours[hoverIndex] : null;
  const hoveredSavings = hoverIndex !== null ? savings.savings_eur[hoverIndex] : null;

  return (
    <div className="chart-placeholder" style={{ position: 'relative' }}>
      <div className="chart-placeholder-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={16} style={{ color: 'var(--color-success)' }} />
          <span className="chart-placeholder-title">Cumulative Cost Savings (24h)</span>
        </div>
        <span
          className="metric-card-badge positive"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          +€{finalSavings.toLocaleString(undefined, { maximumFractionDigits: 0 })} today
        </span>
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
          {/* Horizontal grid */}
          {yTicks.map((t) => (
            <line
              key={t}
              x1={PAD.left}
              y1={sy(t)}
              x2={dims.width - PAD.right}
              y2={sy(t)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Area fill */}
          <path d={areaPath} fill="var(--color-success)" opacity="0.12" style={{ transition: 'd 0.2s' }} />

          {/* Line */}
          <path d={linePath} fill="none" stroke="var(--color-success)" strokeWidth="2" style={{ transition: 'd 0.2s' }} />

          {/* Hover tracker crosshairs */}
          {hoverIndex !== null && (
            <>
              {/* Vertical line */}
              <line
                x1={sx(hoveredHour)}
                y1={PAD.top}
                x2={sx(hoveredHour)}
                y2={PAD.top + chartH}
                stroke="var(--color-muted-foreground)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />

              {/* Savings marker */}
              <circle
                cx={sx(hoveredHour)}
                cy={sy(hoveredSavings)}
                r="4"
                fill="var(--color-success)"
                stroke="white"
                strokeWidth="1.5"
              />
            </>
          )}

          {/* End-point dot */}
          {hoverIndex === null && (
            <circle cx={sx(23)} cy={sy(finalSavings)} r="3.5" fill="var(--color-success)" />
          )}

          {/* End-point label */}
          {hoverIndex === null && (
            <text
              x={sx(23) - 6}
              y={sy(finalSavings) - 8}
              textAnchor="end"
              fontSize="10"
              fontWeight="700"
              fill="var(--color-success-foreground)"
              style={{ userSelect: 'none' }}
            >
              €{finalSavings.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </text>
          )}

          {/* Y-axis labels */}
          {yTicks.map((t) => (
            <text
              key={`y-${t}`}
              x={PAD.left - 8}
              y={sy(t) + 3}
              textAnchor="end"
              fontSize="9"
              fill="var(--color-muted-foreground)"
              style={{ userSelect: 'none' }}
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
            style={{ userSelect: 'none' }}
          >
            Savings (EUR)
          </text>

          {/* X-axis labels */}
          {xTicks.map((t) => (
            <text
              key={`x-${t}`}
              x={sx(t)}
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
            <span style={{ color: 'var(--color-success-foreground)' }}>Net Savings:</span>
            <span style={{ fontWeight: 600 }}>€{hoveredSavings.toFixed(0)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
