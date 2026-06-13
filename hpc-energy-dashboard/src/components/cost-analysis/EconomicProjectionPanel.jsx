import { useSimulation } from '../../context/SimulationContext';
import { Calculator } from 'lucide-react';

export default function EconomicProjectionPanel() {
  const { results, forecastHorizon } = useSimulation();

  const metrics = results?.metrics || {
    baseline_cost: 15000,
    current_cost: 11250,
    annual_cost_saved: 3750 * 365
  };

  const dailyCost = metrics.current_cost;
  const dailySavings = Math.max(0, metrics.baseline_cost - metrics.current_cost);

  const projections = [
    { label: 'Monthly Cost (30 days)', value: `€${(dailyCost * 30).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: 'Quarterly Cost (90 days)', value: `€${(dailyCost * 90).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: `${forecastHorizon}-Day Cost`, value: `€${(dailyCost * forecastHorizon).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: 'Annual Cost (365 days)', value: `€${(dailyCost * 365).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
  ];

  const savings = [
    { label: 'Monthly Savings (30 days)', value: `€${(dailySavings * 30).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: `${forecastHorizon}-Day Savings`, value: `€${(dailySavings * forecastHorizon).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: 'Annual Savings (365 days)', value: `€${(dailySavings * 365).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Calculator size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">Economic Projection</span>
        </div>
      </div>
      <div className="card-body" style={{ padding: '12px 20px 20px' }}>
        {/* Cost rows */}
        {projections.map((row) => (
          <div
            key={row.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 0',
              borderBottom: '1px solid var(--color-border)',
            }}
          >
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted-foreground)' }}>
              {row.label}
            </span>
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-foreground)' }}>
              {row.value}
            </span>
          </div>
        ))}

        {/* Savings section */}
        <div
          style={{
            marginTop: 16,
            padding: '12px',
            background: 'var(--color-success-bg)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <span
            style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--color-success-foreground)',
              display: 'block',
              marginBottom: 8,
            }}
          >
            Projected Savings
          </span>
          {savings.map((row) => (
            <div
              key={row.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 0',
              }}
            >
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-success-foreground)' }}>
                {row.label}
              </span>
              <span
                style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 700,
                  color: 'var(--color-success-foreground)',
                }}
              >
                {row.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

