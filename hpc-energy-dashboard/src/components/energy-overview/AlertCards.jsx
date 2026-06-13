import { useSimulation } from '../../context/SimulationContext';
import { CheckCircle, AlertTriangle, Info } from 'lucide-react';

export default function AlertCards() {
  const { results } = useSimulation();
  
  const transformerLoad = results?.grid_health?.transformer_load || 84.0;
  const isWarning = transformerLoad >= 80.0;
  const isCritical = transformerLoad >= 90.0;

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

      {/* Warning/Info Card */}
      <div
        className="card"
        style={{
          flex: 1,
          background: isCritical ? 'var(--color-danger-bg)' : (isWarning ? 'var(--color-warning-bg)' : 'var(--color-success-bg)'),
          borderColor: isCritical ? 'var(--color-danger)' : (isWarning ? 'var(--color-warning)' : 'var(--color-success)'),
        }}
      >
        <div className="card-body" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          {isWarning ? (
            <AlertTriangle size={20} style={{ color: isCritical ? 'var(--color-danger-foreground)' : 'var(--color-warning-foreground)', flexShrink: 0, marginTop: 2 }} />
          ) : (
            <Info size={20} style={{ color: 'var(--color-success-foreground)', flexShrink: 0, marginTop: 2 }} />
          )}
          <div>
            <div style={{ 
              fontWeight: 700, 
              fontSize: 'var(--text-sm)', 
              color: isCritical ? 'var(--color-danger-foreground)' : (isWarning ? 'var(--color-warning-foreground)' : 'var(--color-success-foreground)'), 
              marginBottom: 4 
            }}>
              {isCritical ? 'Transformer Overload Critical' : (isWarning ? 'Transformer Load Warning' : 'Transformer Load Healthy')}
            </div>
            <p style={{ 
              fontSize: 'var(--text-xs)', 
              color: isCritical ? 'var(--color-danger-foreground)' : (isWarning ? 'var(--color-warning-foreground)' : 'var(--color-success-foreground)'), 
              lineHeight: 1.6 
            }}>
              {isCritical 
                ? `Transformer load critical at ${transformerLoad.toFixed(1)}%. Immediate power flow limiting or load shifting required.`
                : (isWarning 
                  ? `Transformer loading at ${transformerLoad.toFixed(1)}% capacity. Monitor during peak demand periods.`
                  : `Transformer load is stable at ${transformerLoad.toFixed(1)}%. Operating within healthy grid tolerances.`
                )
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

