'use client'

import { cn } from '@/lib/utils'
import { Wifi, WifiOff, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { ApiStatus } from '@/lib/types'

// ─── Live / Mock status pill ──────────────────────────────────────────────────

export function DataStatusBadge({ status }: { status: ApiStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-mono font-medium',
        status === 'live'
          ? 'bg-emerald-glow/15 text-emerald-glow border border-emerald/40'
          : 'bg-muted text-muted-foreground border border-border',
      )}
    >
      {status === 'live' ? (
        <Wifi className="size-3" />
      ) : (
        <WifiOff className="size-3" />
      )}
      {status === 'live' ? 'Live' : 'Mock data'}
    </span>
  )
}

// ─── KPI card ─────────────────────────────────────────────────────────────────

type Trend = 'up' | 'down' | 'neutral'

interface KpiCardProps {
  title: string
  value: string
  unit?: string
  delta?: string
  trend?: Trend
  icon: React.ElementType
  accent?: 'electric' | 'emerald' | 'amber'
  loading?: boolean
}

const accentMap = {
  electric: {
    icon: 'text-electric',
    border: 'border-electric/20',
    glow: 'glow-electric',
  },
  emerald: {
    icon: 'text-emerald-glow',
    border: 'border-emerald/20',
    glow: 'glow-emerald',
  },
  amber: {
    icon: 'text-amber-glow',
    border: 'border-amber/20',
    glow: 'glow-amber',
  },
}

export function KpiCard({
  title,
  value,
  unit,
  delta,
  trend = 'neutral',
  icon: Icon,
  accent = 'electric',
  loading = false,
}: KpiCardProps) {
  const a = accentMap[accent]
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor =
    trend === 'up' ? 'text-electric' : trend === 'down' ? 'text-amber-glow' : 'text-muted-foreground'

  return (
    <Card className={cn('bg-surface border', a.border)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className={cn('size-4', a.icon)} />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        ) : (
          <>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-foreground">{value}</span>
              {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
            </div>
            {delta && (
              <div className={cn('flex items-center gap-1 mt-1 text-xs', trendColor)}>
                <TrendIcon className="size-3" />
                <span>{delta}</span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Section title row ────────────────────────────────────────────────────────

export function SectionTitle({
  title,
  subtitle,
  status,
  children,
}: {
  title: string
  subtitle?: string
  status?: ApiStatus
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {status && <DataStatusBadge status={status} />}
        {children}
      </div>
    </div>
  )
}

// ─── Chart tooltip ────────────────────────────────────────────────────────────

export function ChartTooltipContent({
  active,
  payload,
  label,
  labelFormatter,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string; unit?: string }>
  label?: string
  labelFormatter?: (label: string) => string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-popover px-3 py-2 shadow-lg">
      <p className="text-xs text-muted-foreground mb-1.5 font-mono">
        {labelFormatter ? labelFormatter(label ?? '') : label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 text-xs">
          <span className="size-2 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
          <span className="text-muted-foreground">{p.name}</span>
          <span className="ml-auto font-mono font-medium text-foreground pl-4">
            {p.value}
            {p.unit ?? ''}
          </span>
        </div>
      ))}
    </div>
  )
}

// ─── Empty / error state ──────────────────────────────────────────────────────

export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return <Skeleton className="w-full rounded-xl" style={{ height }} />
}
