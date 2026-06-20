'use client'

import { useEffect, useState } from 'react'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  Cell,
} from 'recharts'
import { TrendingDown, Clock, Leaf, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { SectionTitle, ChartTooltipContent, ChartSkeleton, DataStatusBadge } from '../shared'
import { fetchSmardPricing, fetchCarbon } from '@/lib/api'
import type { SmardPricing, CarbonAnalysis, ApiStatus } from '@/lib/types'

function classifyHour(price: number, low: number, high: number): 'low' | 'mid' | 'high' {
  if (price <= low) return 'low'
  if (price >= high) return 'high'
  return 'mid'
}

const COLOR_MAP = {
  low: 'oklch(0.70 0.18 155 / 80%)',
  mid: 'oklch(0.65 0.20 240 / 70%)',
  high: 'oklch(0.72 0.18 75 / 85%)',
}

export default function GridPricingTab() {
  const [pricing, setPricing] = useState<SmardPricing | null>(null)
  const [carbon, setCarbon] = useState<CarbonAnalysis | null>(null)
  const [status, setStatus] = useState<ApiStatus>('mock')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const [p, c] = await Promise.all([fetchSmardPricing(), fetchCarbon()])
      setPricing(p.data)
      setCarbon(c.data)
      setStatus(p.status)
      setLoading(false)
    }
    load()
  }, [])

  const prices = pricing?.day_ahead_prices ?? []
  const priceValues = prices.map((p) => p.price_eur_mwh)
  const minP = priceValues.length ? Math.min(...priceValues) : 20
  const maxP = priceValues.length ? Math.max(...priceValues) : 80
  const range = maxP - minP
  const low = minP + range * 0.35
  const high = minP + range * 0.65

  const priceData = prices.map((p) => ({
    hour: `${p.hour.toString().padStart(2, '0')}:00`,
    price: p.price_eur_mwh,
    classification: classifyHour(p.price_eur_mwh, low, high),
  }))

  const carbonData = carbon?.intensity_series.map((c) => ({
    hour: `${c.hour.toString().padStart(2, '0')}:00`,
    'CO₂ (g/kWh)': c.intensity_g_kwh,
    'Renewable (%)': c.renewable_pct,
  })) ?? []

  const combinedData = priceData.map((p, i) => ({
    ...p,
    'CO₂ (g/kWh)': carbonData[i]?.['CO₂ (g/kWh)'] ?? 0,
    'Renewable (%)': carbonData[i]?.['Renewable (%)'] ?? 0,
  }))

  const optimalHour = carbon?.optimal_start_hour ?? 2
  const windowLabel = `${optimalHour.toString().padStart(2, '0')}:00 – ${((optimalHour + 6) % 24).toString().padStart(2, '0')}:00`

  const touBadgeMap = {
    green_window: { label: 'Green Window', variant: 'secondary' as const, icon: Leaf, color: 'text-emerald-glow' },
    amber_window: { label: 'Amber Window', variant: 'secondary' as const, icon: Clock, color: 'text-amber-glow' },
    peak_window: { label: 'Peak Window', variant: 'destructive' as const, icon: AlertTriangle, color: 'text-destructive' },
  }
  const tou = touBadgeMap[carbon?.tou_recommendation ?? 'green_window']

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Grid & Pricing"
        subtitle="German SMARD day-ahead prices and carbon intensity"
        status={status}
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Current Price',
            value: pricing ? `${pricing.current_price_eur_mwh.toFixed(1)} €/MWh` : '—',
            sub: `${pricing?.price_percentile ?? '—'}th percentile`,
            color: 'text-electric',
          },
          {
            label: 'Grid CO₂ Intensity',
            value: carbon ? `${carbon.grid_intensity_g_kwh} g/kWh` : '—',
            sub: 'German average',
            color: 'text-amber-glow',
          },
          {
            label: 'Optimal Window',
            value: windowLabel,
            sub: 'Cheapest 6-hour slot',
            color: 'text-emerald-glow',
          },
          {
            label: 'Current Status',
            value: tou.label,
            sub: 'Time-of-use class',
            color: tou.color,
          },
        ].map(({ label, value, sub, color }) => (
          <Card key={label} className="bg-surface border">
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground mb-1">{label}</p>
              <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Day-ahead price heatmap / bar */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Day-Ahead Price Heatmap</CardTitle>
          <CardDescription>
            24-hour SMARD prices — green = buy window, amber = peak
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={240} />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={priceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" vertical={false} />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                  unit=" €"
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Bar dataKey="price" name="Price (€/MWh)" radius={[3, 3, 0, 0]}>
                  {priceData.map((entry, index) => (
                    <Cell key={index} fill={COLOR_MAP[entry.classification]} />
                  ))}
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
          )}
          <div className="flex gap-4 mt-3">
            {[
              { color: COLOR_MAP.low, label: 'Low price (buy)' },
              { color: COLOR_MAP.mid, label: 'Mid price' },
              { color: COLOR_MAP.high, label: 'Peak price' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="text-xs text-muted-foreground">{label}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Carbon intensity + renewable mix */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Carbon Intensity &amp; Renewable Mix</CardTitle>
          <CardDescription>Hourly grid CO₂ intensity vs. renewable generation share</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={260} />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={combinedData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  yAxisId="co2"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  unit=" g"
                />
                <YAxis
                  yAxisId="re"
                  orientation="right"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                  unit="%"
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 12, color: 'oklch(0.55 0.010 240)' }} />
                <Area
                  yAxisId="co2"
                  type="monotone"
                  dataKey="CO₂ (g/kWh)"
                  fill="oklch(0.72 0.18 75 / 20%)"
                  stroke="oklch(0.72 0.18 75)"
                  strokeWidth={2}
                />
                <Line
                  yAxisId="re"
                  type="monotone"
                  dataKey="Renewable (%)"
                  stroke="oklch(0.70 0.18 155)"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* TOU recommendation */}
      <Card className="bg-surface border border-emerald/20">
        <CardContent className="pt-5 pb-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <tou.icon className={`size-5 ${tou.color}`} />
              <span className="font-semibold text-sm">Scheduling Recommendation</span>
            </div>
            <div className="flex-1 text-sm text-muted-foreground">
              Best window to run heavy GPU training is{' '}
              <span className="text-emerald-glow font-mono font-medium">{windowLabel}</span> —
              lowest spot prices and highest renewable share on the German grid.
              Potential saving:{' '}
              <span className="text-electric font-mono">36.7%</span> vs. unoptimised 24/7 operation.
            </div>
            <TrendingDown className="size-5 text-emerald-glow flex-shrink-0" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
