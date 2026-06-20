'use client'

import { useEffect, useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'
import { CheckCircle, AlertCircle, Zap, Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { SectionTitle, ChartTooltipContent, ChartSkeleton } from '../shared'
import { fetchGridHealth } from '@/lib/api'
import type { GridHealthResult, ApiStatus } from '@/lib/types'

// ─── Radial gauge (SVG) ───────────────────────────────────────────────────────

function GaugeArc({
  value,
  max,
  label,
  unit,
  color,
  danger,
}: {
  value: number
  max: number
  label: string
  unit: string
  color: string
  danger?: boolean
}) {
  const pct = Math.min(1, value / max)
  const r = 42
  const cx = 56
  const cy = 56
  const startAngle = -220
  const sweep = 260
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const arcPath = (pct: number) => {
    const end = startAngle + sweep * pct
    const x1 = cx + r * Math.cos(toRad(startAngle))
    const y1 = cy + r * Math.sin(toRad(startAngle))
    const x2 = cx + r * Math.cos(toRad(end))
    const y2 = cy + r * Math.sin(toRad(end))
    const large = sweep * pct > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={112} height={80} viewBox="0 0 112 80">
        {/* Background arc */}
        <path
          d={arcPath(1)}
          fill="none"
          stroke="oklch(1 0 0 / 8%)"
          strokeWidth={8}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={arcPath(pct)}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeLinecap="round"
        />
        {/* Value text */}
        <text x={cx} y={cy + 4} textAnchor="middle" fontSize={16} fontWeight={700} fill="oklch(0.94 0.005 240)" fontFamily="monospace">
          {value.toFixed(value < 10 ? 3 : 1)}
        </text>
        <text x={cx} y={cy + 18} textAnchor="middle" fontSize={9} fill="oklch(0.55 0.010 240)">
          {unit}
        </text>
      </svg>
      <span className="text-xs text-muted-foreground text-center leading-tight">{label}</span>
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function GridHealthTab() {
  const [data, setData] = useState<GridHealthResult | null>(null)
  const [status, setStatus] = useState<ApiStatus>('mock')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const res = await fetchGridHealth()
      setData(res.data)
      setStatus(res.status)
      setLoading(false)
    }
    load()
  }, [])

  const lossesData = data?.losses_series.map((p) => ({
    step: p.timestep,
    'Losses (kW)': p.losses_kw,
    'Line Loading (%)': p.loading_pct,
  })) ?? []

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Grid Health"
        subtitle="Pandapower load flow analysis — 707 timestep simulation"
        status={status}
      />

      {/* Convergence banner */}
      <Card className="bg-surface border border-emerald/20">
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-2">
              {data?.converged ? (
                <CheckCircle className="size-5 text-emerald-glow flex-shrink-0" />
              ) : (
                <AlertCircle className="size-5 text-amber-glow flex-shrink-0" />
              )}
              <span className="font-semibold text-sm">
                {data?.converged ? 'All timesteps converged' : 'Convergence warnings'}
              </span>
            </div>
            <div className="flex-1">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Convergence</span>
                <span className="font-mono text-emerald-glow">
                  {data ? `${data.converged_timesteps} / ${data.total_timesteps}` : '—'}
                </span>
              </div>
              <Progress
                value={data?.convergence_rate_pct ?? 0}
                className="h-1.5"
              />
            </div>
            <span className="font-mono font-bold text-emerald-glow text-lg">
              {data ? `${data.convergence_rate_pct.toFixed(1)}%` : '—'}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Gauge row */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Voltage &amp; Loading Gauges</CardTitle>
          <CardDescription>Average values across all buses and lines</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={120} />
          ) : (
            <div className="flex flex-wrap justify-around gap-6 py-2">
              <GaugeArc
                value={data?.avg_bus_voltage_pu ?? 1}
                max={1.1}
                label="Avg Bus Voltage"
                unit="pu"
                color="oklch(0.65 0.20 240)"
              />
              <GaugeArc
                value={data?.min_bus_voltage_pu ?? 0.95}
                max={1.1}
                label="Min Bus Voltage"
                unit="pu"
                color="oklch(0.70 0.18 155)"
              />
              <GaugeArc
                value={data?.max_bus_voltage_pu ?? 1.05}
                max={1.1}
                label="Max Bus Voltage"
                unit="pu"
                color="oklch(0.65 0.20 240)"
              />
              <GaugeArc
                value={data?.avg_line_loading_pct ?? 32}
                max={100}
                label="Avg Line Loading"
                unit="%"
                color="oklch(0.72 0.18 75)"
              />
              <GaugeArc
                value={data?.max_line_loading_pct ?? 58}
                max={100}
                label="Max Line Loading"
                unit="%"
                color="oklch(0.65 0.22 25)"
                danger
              />
              <GaugeArc
                value={data?.total_losses_kw ?? 2.1}
                max={10}
                label="Total Losses"
                unit="kW"
                color="oklch(0.70 0.18 155)"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Timesteps', value: data?.total_timesteps ?? '—', unit: '', icon: Activity, color: 'text-electric' },
          { label: 'Converged', value: data?.converged_timesteps ?? '—', unit: '', icon: CheckCircle, color: 'text-emerald-glow' },
          { label: 'Avg Losses', value: data ? `${data.total_losses_kw.toFixed(2)}` : '—', unit: 'kW', icon: Zap, color: 'text-amber-glow' },
        ].map(({ label, value, unit, icon: Icon, color }) => (
          <Card key={label} className="bg-surface border">
            <CardContent className="pt-4 pb-4 flex items-center gap-3">
              <Icon className={`size-5 flex-shrink-0 ${color}`} />
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={`font-bold font-mono text-lg ${color}`}>
                  {value}{unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Losses & loading time-series */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Losses &amp; Line Loading Over Time</CardTitle>
          <CardDescription>Sampled across 707 simulation timesteps</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={280} />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={lossesData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" />
                <XAxis
                  dataKey="step"
                  tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  label={{ value: 'Timestep', position: 'insideBottomRight', offset: -4, fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                />
                <YAxis
                  yAxisId="loss"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                  unit=" kW"
                />
                <YAxis
                  yAxisId="load"
                  orientation="right"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                  unit="%"
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Line
                  yAxisId="loss"
                  type="monotone"
                  dataKey="Losses (kW)"
                  stroke="oklch(0.70 0.18 155)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="load"
                  type="monotone"
                  dataKey="Line Loading (%)"
                  stroke="oklch(0.72 0.18 75)"
                  strokeWidth={1.5}
                  dot={false}
                  strokeDasharray="4 2"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
