import { Calculator } from 'lucide-react';

const projections = [
  { label: 'Monthly Cost', value: '€56,028', type: 'cost' },
  { label: 'Quarterly Cost', value: '€168,083', type: 'cost' },
  { label: 'Annual Cost', value: '€672,330', type: 'cost' },
];

const savings = [
  { label: 'Monthly Savings', value: '€32,556', type: 'saving' },
  { label: 'Annual Savings', value: '€390,672', type: 'saving' },
];

export default function EconomicProjectionPanel() {
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
