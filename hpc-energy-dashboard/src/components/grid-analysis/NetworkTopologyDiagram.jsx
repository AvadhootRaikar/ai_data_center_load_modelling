import { Network } from 'lucide-react';

const nodeStyle = (bg, border, textColor) => ({
  padding: '8px 16px',
  borderRadius: 'var(--radius-md)',
  border: `2px solid ${border}`,
  background: bg,
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
  color: textColor,
  textAlign: 'center',
  minWidth: 110,
});

const connectorV = {
  width: 2,
  height: 28,
  background: 'var(--color-border)',
  margin: '0 auto',
};

const connectorH = {
  height: 2,
  background: 'var(--color-border)',
  flex: 1,
};

const busStyle = {
  height: 4,
  borderRadius: 2,
  margin: '0 auto',
};

export default function NetworkTopologyDiagram() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <Network size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="card-title">Network Topology</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted-foreground)' }}>
          PandaPower Grid Model
        </span>
      </div>
      <div className="card-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0, paddingTop: 24, paddingBottom: 24 }}>

        {/* External Grid */}
        <div style={nodeStyle('var(--color-danger-bg)', 'var(--color-danger)', 'var(--color-danger-foreground)')}>
          External Grid
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>110 kV</div>
        </div>

        <div style={connectorV} />

        {/* HV/MV Transformer */}
        <div style={nodeStyle('var(--color-warning-bg)', 'var(--color-warning)', 'var(--color-warning-foreground)')}>
          Trafo HV/MV
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>110 → 20 kV</div>
        </div>

        <div style={connectorV} />

        {/* 20 kV Bus */}
        <div style={{ width: '100%', maxWidth: 520, textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-primary)', marginBottom: 4, letterSpacing: '0.05em' }}>
            20 kV BUS
          </div>
          <div style={{ ...busStyle, width: '100%', background: 'var(--color-primary)' }} />
        </div>

        {/* Branching connectors */}
        <div style={{ display: 'flex', width: '100%', maxWidth: 520, justifyContent: 'center', gap: 0 }}>
          {/* Left branch */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={nodeStyle('var(--color-warning-bg)', 'var(--color-warning)', 'var(--color-warning-foreground)')}>
              Trafo MV/LV-1
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>20 → 0.4 kV</div>
            </div>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={{ width: 140, textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-success-foreground)', marginBottom: 4, letterSpacing: '0.05em' }}>
                0.4 kV BUS
              </div>
              <div style={{ ...busStyle, width: '100%', background: 'var(--color-success)' }} />
            </div>
            <div style={{ ...connectorV, height: 16 }} />
            <div style={nodeStyle('var(--color-secondary)', 'var(--color-primary)', 'var(--color-primary)')}>
              HPC Load A
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>5.6 MW</div>
            </div>
          </div>

          {/* Center connector */}
          <div style={{ display: 'flex', alignItems: 'flex-start', paddingTop: 10 }}>
            <div style={connectorH} />
          </div>

          {/* Center branch */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={nodeStyle('var(--color-warning-bg)', 'var(--color-warning)', 'var(--color-warning-foreground)')}>
              Trafo MV/LV-2
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>20 → 0.4 kV</div>
            </div>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={{ width: 140, textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-success-foreground)', marginBottom: 4, letterSpacing: '0.05em' }}>
                0.4 kV BUS
              </div>
              <div style={{ ...busStyle, width: '100%', background: 'var(--color-success)' }} />
            </div>
            <div style={{ ...connectorV, height: 16 }} />
            <div style={nodeStyle('var(--color-secondary)', 'var(--color-primary)', 'var(--color-primary)')}>
              HPC Load B
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>3.4 MW</div>
            </div>
          </div>

          {/* Right connector */}
          <div style={{ display: 'flex', alignItems: 'flex-start', paddingTop: 10 }}>
            <div style={connectorH} />
          </div>

          {/* Right branch */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={nodeStyle('var(--color-warning-bg)', 'var(--color-warning)', 'var(--color-warning-foreground)')}>
              Trafo MV/LV-3
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>20 → 0.4 kV</div>
            </div>
            <div style={{ ...connectorV, height: 20 }} />
            <div style={{ width: 140, textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-success-foreground)', marginBottom: 4, letterSpacing: '0.05em' }}>
                0.4 kV BUS
              </div>
              <div style={{ ...busStyle, width: '100%', background: 'var(--color-success)' }} />
            </div>
            <div style={{ ...connectorV, height: 16 }} />
            <div style={nodeStyle('var(--color-secondary)', 'var(--color-primary)', 'var(--color-primary)')}>
              HPC Load C
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 400, marginTop: 2 }}>2.2 MW</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
