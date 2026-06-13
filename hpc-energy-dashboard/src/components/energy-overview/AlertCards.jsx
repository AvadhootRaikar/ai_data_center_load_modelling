import { CheckCircle, AlertTriangle } from 'lucide-react';

export default function AlertCards() {
  return (
    <div className="flex-row">
      {/* Success Card */}
      <div
        className="card"
        style={{
          flex: 1,
          background: 'var(--color-success-bg)',
          borderColor: 'var(--color-success)',
        }}
      >
        <div className="card-body" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <CheckCircle size={20} style={{ color: 'var(--color-success-foreground)', flexShrink: 0, marginTop: 2 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--color-success-foreground)', marginBottom: 4 }}>
              Compute Integrity Check
            </div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success-foreground)', lineHeight: 1.6 }}>
              Workload distribution remains within 5% of theoretical maximum. Memory-to-Compute ratio is optimized.
            </p>
          </div>
        </div>
      </div>

      {/* Warning Card */}
      <div
        className="card"
        style={{
          flex: 1,
          background: 'var(--color-warning-bg)',
          borderColor: 'var(--color-warning)',
        }}
      >
        <div className="card-body" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <AlertTriangle size={20} style={{ color: 'var(--color-warning-foreground)', flexShrink: 0, marginTop: 2 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--color-warning-foreground)', marginBottom: 4 }}>
              Transformer Load Warning
            </div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning-foreground)', lineHeight: 1.6 }}>
              Transformer loading at 84% capacity. Monitor during peak demand periods. Consider capacity expansion above 90%.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
