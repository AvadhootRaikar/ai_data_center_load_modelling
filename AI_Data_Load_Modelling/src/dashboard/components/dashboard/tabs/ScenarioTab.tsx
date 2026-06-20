'use client'

import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Trophy, Leaf, TrendingDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { SectionTitle, ChartTooltipContent, ChartSkeleton } from '../shared'
import { fetchOptimization } from '@/lib/api'
import type { OptimizationSummary, ScenarioResult, ApiStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

const FEASIBILITY_COLORS: Record<string, string> = {
  high: 'oklch(0.70 0.18 155)',
  medium: 'oklch(0.65 0.20 240)',
  low: 'oklch(0.72 0.18 75)',
}

const FEASIBILITY_BADGE: Record<string, string> = {
  high: 'text-emerald-glow border-emerald/40 bg-emerald-glow/10',
  medium: 'text-electric border-electric/40 bg-electric/10',
  low: 'text-amber-glow border-amber/40 bg-amber-glow/10',
}

type SortKey = 'reduction_pct' | 'savings_eur_day' | 'co2_savings_kg_day'

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'reduction_pct', label: 'Power Reduction' },
  { key: 'savings_eur_day', label: 'Cost Savings' },
  { key: 'co2_savings_kg_day', label: 'CO₂ Savings' },
]

export default function ScenarioTab() {
  const [data, setData] = useState<OptimizationSummary | null>(null)
  const [status, setStatus] = useState<ApiStatus>('mock')
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('reduction_pct')

  useEffect(() => {
    async function load() {
      setLoading(true)
      const res = await fetchOptimization()
      setData(res.data)
      setStatus(res.status)
      setLoading(false)
    }
    load()
  }, [])

  const sorted = data
    ? [...data.scenarios].sort((a, b) => b[sortKey] - a[sortKey])
    : []

  const chartData = sorted.map((s) => ({
    name: s.name.replace(' Optimization', ' Opt.').replace('Consolidation', 'Consol.'),
    'Baseline (kW)': s.baseline_kw,
    'Optimised (kW)': s.optimized_kw,
    'Saving (%)': s.reduction_pct,
    scenario_id: s.scenario_id,
    feasibility: s.feasibility,
  }))

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Optimization Scenarios"
        subtitle="10 strategies evaluated by the simulation engine"
        status={status}
      />

      {/* Summary highlights */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Card className="bg-surface border border-electric/20">
            <CardContent className="pt-4 pb-4 flex items-start gap-3">
              <Trophy className="size-5 text-electric mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Best single scenario</p>
                <p className="font-semibold text-sm mt-0.5">
                  {data.scenarios.find((s) => s.scenario_id === data.best_scenario_id)?.name}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-surface border border-emerald/20">
            <CardContent className="pt-4 pb-4 flex items-start gap-3">
              <TrendingDown className="size-5 text-emerald-glow mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Max daily savings</p>
                <p className="font-bold font-mono text-emerald-glow text-lg">
                  €{data.max_savings_eur_day.toFixed(2)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-surface border border-amber/20 col-span-2 md:col-span-1">
            <CardContent className="pt-4 pb-4 flex items-start gap-3">
              <Leaf className="size-5 text-amber-glow mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Max power reduction</p>
                <p className="font-bold font-mono text-amber-glow text-lg">
                  {data.max_reduction_pct.toFixed(1)}%
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Sort selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">Sort by:</span>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setSortKey(opt.key)}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium border transition-colors',
              sortKey === opt.key
                ? 'border-electric/60 text-electric bg-electric/10'
                : 'border-border text-muted-foreground hover:text-foreground',
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Comparison bar chart */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Baseline vs. Optimised Power</CardTitle>
          <CardDescription>Sorted by {SORT_OPTIONS.find((o) => o.key === sortKey)?.label}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={320} />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 4, right: 48, left: 8, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  unit=" kW"
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 11, color: 'oklch(0.55 0.010 240)' }} />
                <Bar
                  dataKey="Baseline (kW)"
                  fill="oklch(0.55 0.010 240 / 40%)"
                  radius={[0, 3, 3, 0]}
                />
                <Bar dataKey="Optimised (kW)" radius={[0, 3, 3, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={FEASIBILITY_COLORS[entry.feasibility]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Scenario detail table */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Scenario Details</CardTitle>
          <CardDescription>All 10 optimization strategies with feasibility ratings</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {['Scenario', 'Power saving', 'Cost / day', 'CO₂ / day', 'Feasibility'].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i} className="border-b border-border">
                        {Array.from({ length: 5 }).map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 bg-muted rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : sorted.map((s) => (
                      <tr
                        key={s.scenario_id}
                        className={cn(
                          'border-b border-border last:border-0 transition-colors hover:bg-surface-raised',
                          s.scenario_id === data?.best_scenario_id && 'bg-electric/5',
                        )}
                      >
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            {s.scenario_id === data?.best_scenario_id && (
                              <Trophy className="size-3 text-electric flex-shrink-0" />
                            )}
                            <div>
                              <div className="font-medium text-foreground text-sm leading-snug">{s.name}</div>
                              <div className="text-xs text-muted-foreground mt-1 leading-relaxed whitespace-normal">
                                {s.description}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          <span
                            className={
                              s.reduction_pct > 0 ? 'text-emerald-glow' : 'text-muted-foreground'
                            }
                          >
                            {s.reduction_pct > 0 ? `−${s.reduction_pct.toFixed(1)}%` : '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          <span className={s.savings_eur_day > 0 ? 'text-electric' : 'text-muted-foreground'}>
                            {s.savings_eur_day > 0 ? `€${s.savings_eur_day.toFixed(2)}` : '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          <span className={s.co2_savings_kg_day > 0 ? 'text-amber-glow' : 'text-muted-foreground'}>
                            {s.co2_savings_kg_day > 0 ? `−${s.co2_savings_kg_day.toFixed(1)} kg` : '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant="outline"
                            className={cn('text-xs capitalize', FEASIBILITY_BADGE[s.feasibility])}
                          >
                            {s.feasibility}
                          </Badge>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
