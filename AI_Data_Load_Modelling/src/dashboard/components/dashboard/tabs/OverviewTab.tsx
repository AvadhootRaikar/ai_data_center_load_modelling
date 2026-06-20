'use client'

import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { Zap, DollarSign, Wind, Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { KpiCard, SectionTitle, ChartTooltipContent, ChartSkeleton } from '../shared'
import { fetchBaseline, fetchEnergy, fetchPowerSeries } from '@/lib/api'
import type { BaselineResult, EnergyConsumption, PowerTimeSeries, ApiStatus } from '@/lib/types'

const PERIODS = ['1h', '6h', '24h', '30d'] as const
type Period = (typeof PERIODS)[number]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function OverviewTab() {
  const [baseline, setBaseline] = useState<BaselineResult | null>(null)
  const [energy, setEnergy] = useState<EnergyConsumption | null>(null)
  const [series, setSeries] = useState<PowerTimeSeries | null>(null)
  const [period, setPeriod] = useState<Period>('24h')
  const [status, setStatus] = useState<ApiStatus>('mock')
  const [loading, setLoading] = useState(true)

  // Load baseline + series on mount
  useEffect(() => {
    async function load() {
      setLoading(true)
      const [b, s] = await Promise.all([fetchBaseline(), fetchPowerSeries()])
      setBaseline(b.data)
      setSeries(s.data)
      setStatus(b.status)
      setLoading(false)
    }
    load()
  }, [])

  // Load energy when period changes
  useEffect(() => {
    async function loadEnergy() {
      const e = await fetchEnergy(period)
      setEnergy(e.data)
    }
    loadEnergy()
  }, [period])

  const chartData = series?.points.map((p) => ({
    time: formatTime(p.timestamp),
    'Total (kW)': p.total_kw,
    'IT Load (kW)': p.it_load_kw,
    'Cooling (kW)': p.cooling_kw,
    'Price (€/MWh)': p.price_eur_mwh,
  }))

  // Projection bars: project 24h consumption across periods
  const projectionData = [
    { period: '1h', kwh: 40.5, cost: 0.52 },
    { period: '6h', kwh: 243, cost: 3.14 },
    { period: '24h', kwh: 972, cost: 12.57 },
    { period: '30d', kwh: 29160, cost: 377.1 },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* KPI row */}
      <SectionTitle
        title="System Overview"
        subtitle="Real-time baseline from simulation engine"
        status={status}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Power Draw"
          value={baseline ? baseline.total_power_kw.toFixed(1) : '—'}
          unit="kW"
          delta="Baseline load"
          trend="neutral"
          icon={Zap}
          accent="electric"
          loading={loading}
        />
        <KpiCard
          title="IT Load"
          value={baseline ? baseline.it_load_kw.toFixed(1) : '—'}
          unit="kW"
          delta="GPU + CPU + network"
          trend="neutral"
          icon={Activity}
          accent="electric"
          loading={loading}
        />
        <KpiCard
          title="Cooling Power"
          value={baseline ? baseline.cooling_kw.toFixed(1) : '—'}
          unit="kW"
          delta={baseline ? `PUE ${baseline.pue.toFixed(2)}` : '—'}
          trend="neutral"
          icon={Wind}
          accent="amber"
          loading={loading}
        />
        <KpiCard
          title="Daily Cost"
          value={energy ? `€${energy.cost_eur.toFixed(2)}` : '—'}
          unit=""
          delta={energy ? `${energy.avg_price_eur_mwh} €/MWh avg` : '—'}
          trend="neutral"
          icon={DollarSign}
          accent="emerald"
          loading={loading || !energy}
        />
      </div>

      {/* Power time-series chart */}
      <Card className="bg-surface border">
        <CardHeader>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="text-base">24-Hour Power Time-Series</CardTitle>
              <CardDescription>IT load, cooling, and total draw at 10-min resolution (144 points)</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading || !chartData ? (
            <ChartSkeleton height={320} />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  interval={17}
                />
                <YAxis
                  yAxisId="kw"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                  unit=" kW"
                />
                <YAxis
                  yAxisId="price"
                  orientation="right"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={50}
                  unit=" €"
                />
                <Tooltip
                  content={
                    <ChartTooltipContent
                      labelFormatter={(l) => l}
                    />
                  }
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: 'oklch(0.55 0.010 240)' }}
                />
                <Line
                  yAxisId="kw"
                  type="monotone"
                  dataKey="Total (kW)"
                  stroke="oklch(0.65 0.20 240)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
                <Line
                  yAxisId="kw"
                  type="monotone"
                  dataKey="IT Load (kW)"
                  stroke="oklch(0.70 0.18 155)"
                  strokeWidth={1.5}
                  dot={false}
                  strokeDasharray="4 2"
                />
                <Line
                  yAxisId="kw"
                  type="monotone"
                  dataKey="Cooling (kW)"
                  stroke="oklch(0.72 0.18 75)"
                  strokeWidth={1.5}
                  dot={false}
                  strokeDasharray="4 2"
                />
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="Price (€/MWh)"
                  stroke="oklch(0.65 0.22 25)"
                  strokeWidth={1}
                  dot={false}
                  strokeOpacity={0.6}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Energy projection + period selector */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="bg-surface border">
          <CardHeader>
            <CardTitle className="text-base">Energy Projection</CardTitle>
            <CardDescription>Consumption &amp; cost by time window</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={projectionData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" vertical={false} />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 12, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  yAxisId="kwh"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                />
                <Tooltip
                  content={<ChartTooltipContent />}
                />
                <Bar
                  yAxisId="kwh"
                  dataKey="kwh"
                  name="Energy (kWh)"
                  fill="oklch(0.65 0.20 240 / 70%)"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Period details card */}
        <Card className="bg-surface border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Period Details</CardTitle>
                <CardDescription>Select a time window</CardDescription>
              </div>
              <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
                <TabsList className="h-8">
                  {PERIODS.map((p) => (
                    <TabsTrigger key={p} value={p} className="text-xs px-2 h-6">
                      {p}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            {!energy ? (
              <div className="flex flex-col gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <ChartSkeleton key={i} height={20} />
                ))}
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {[
                  { label: 'Energy consumed', value: `${energy.energy_kwh.toLocaleString()} kWh` },
                  { label: 'Average power', value: `${energy.avg_power_kw.toFixed(1)} kW` },
                  { label: 'Peak power', value: `${energy.peak_power_kw.toFixed(1)} kW` },
                  { label: 'Electricity cost', value: `€${energy.cost_eur.toFixed(2)}` },
                  { label: 'Avg price', value: `${energy.avg_price_eur_mwh} €/MWh` },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between items-center border-b border-border pb-2 last:border-0 last:pb-0">
                    <span className="text-sm text-muted-foreground">{label}</span>
                    <span className="text-sm font-mono font-medium text-foreground">{value}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
