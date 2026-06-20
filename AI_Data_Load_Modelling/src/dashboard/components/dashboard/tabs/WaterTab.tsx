'use client'

import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import { Droplets, Thermometer, DollarSign } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { SectionTitle, ChartTooltipContent, ChartSkeleton } from '../shared'
import { fetchWater } from '@/lib/api'
import type { WaterAnalysis, ApiStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

const PIE_COLORS = [
  'oklch(0.65 0.20 240)',
  'oklch(0.70 0.18 155)',
  'oklch(0.72 0.18 75)',
]

export default function WaterTab() {
  const [data, setData] = useState<WaterAnalysis | null>(null)
  const [status, setStatus] = useState<ApiStatus>('mock')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const res = await fetchWater()
      setData(res.data)
      setStatus(res.status)
      setLoading(false)
    }
    load()
  }, [])

  const pueData = data?.pue_curve.map((p) => ({
    hour: `${p.hour.toString().padStart(2, '0')}:00`,
    PUE: p.pue,
    'Cooling (kW)': p.cooling_kw,
  })) ?? []

  const thermalData = data?.thermal_schedule.map((p) => ({
    hour: `${p.hour.toString().padStart(2, '0')}:00`,
    'Power (kW)': p.power_kw,
    'Temp (°C)': p.temp_c,
    recommended: p.recommended,
  })) ?? []

  const costPieData = data
    ? [
        { name: 'Water Supply', value: data.cost_breakdown.water_supply_eur },
        { name: 'Wastewater', value: data.cost_breakdown.wastewater_eur },
        { name: 'Treatment', value: data.cost_breakdown.treatment_eur },
      ]
    : []

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Water & Cooling"
        subtitle="Annual water consumption, WUE, PUE curve, and thermal schedule"
        status={status}
      />

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Annual Water Use',
            value: data ? `${data.annual_m3.toFixed(0)} m³` : '—',
            sub: 'Per year',
            icon: Droplets,
            color: 'text-emerald-glow',
          },
          {
            label: 'Daily Water Use',
            value: data ? `${data.daily_m3.toFixed(2)} m³` : '—',
            sub: 'Per day avg.',
            icon: Droplets,
            color: 'text-emerald-glow',
          },
          {
            label: 'WUE',
            value: data ? data.wue.toFixed(2) : '—',
            sub: 'L/kWh (target < 0.5)',
            icon: Thermometer,
            color: 'text-electric',
          },
          {
            label: 'Annual Water Cost',
            value: data ? `€${data.annual_cost_eur.toLocaleString()}` : '—',
            sub: 'Supply + treatment',
            icon: DollarSign,
            color: 'text-amber-glow',
          },
        ].map(({ label, value, sub, icon: Icon, color }) => (
          <Card key={label} className="bg-surface border">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-muted-foreground">{label}</p>
                <Icon className={`size-4 ${color}`} />
              </div>
              <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* PUE curve */}
        <Card className="bg-surface border">
          <CardHeader>
            <CardTitle className="text-base">24-Hour PUE Curve</CardTitle>
            <CardDescription>Power Usage Effectiveness over the day — target PUE &lt; 1.3</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <ChartSkeleton height={220} />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={pueData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" />
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                    tickLine={false}
                    interval={3}
                  />
                  <YAxis
                    yAxisId="pue"
                    domain={[1.1, 1.5]}
                    tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                    tickLine={false}
                    axisLine={false}
                    width={36}
                  />
                  <YAxis
                    yAxisId="cool"
                    orientation="right"
                    tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                    unit=" kW"
                  />
                  <Tooltip content={<ChartTooltipContent />} />
                  <Line
                    yAxisId="pue"
                    type="monotone"
                    dataKey="PUE"
                    stroke="oklch(0.65 0.20 240)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="cool"
                    type="monotone"
                    dataKey="Cooling (kW)"
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

        {/* Cost breakdown donut */}
        <Card className="bg-surface border">
          <CardHeader>
            <CardTitle className="text-base">Annual Water Cost Breakdown</CardTitle>
            <CardDescription>Supply, wastewater, and treatment costs</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <ChartSkeleton height={220} />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={costPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {costPieData.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v) => `€${Number(v).toLocaleString()}`}
                    contentStyle={{
                      backgroundColor: 'oklch(0.14 0.010 240)',
                      border: '1px solid oklch(1 0 0 / 8%)',
                      borderRadius: '8px',
                      fontSize: 12,
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12, color: 'oklch(0.55 0.010 240)' }}
                    formatter={(value, entry) => (
                      <span style={{ color: 'oklch(0.94 0.005 240)' }}>{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Thermal schedule */}
      <Card className="bg-surface border">
        <CardHeader>
          <CardTitle className="text-base">Thermal Schedule Recommendation</CardTitle>
          <CardDescription>
            Green bars = recommended operating windows (low price + low ambient temp)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton height={240} />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={thermalData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 6%)" vertical={false} />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 10, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  yAxisId="pw"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                  unit=" kW"
                  domain={[0, 55]}
                />
                <YAxis
                  yAxisId="tmp"
                  orientation="right"
                  tick={{ fontSize: 11, fill: 'oklch(0.55 0.010 240)' }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                  unit="°C"
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Bar yAxisId="pw" dataKey="Power (kW)" radius={[3, 3, 0, 0]}>
                  {thermalData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        entry.recommended
                          ? 'oklch(0.70 0.18 155 / 80%)'
                          : 'oklch(0.55 0.010 240 / 40%)'
                      }
                    />
                  ))}
                </Bar>
                <Line
                  yAxisId="tmp"
                  type="monotone"
                  dataKey="Temp (°C)"
                  stroke="oklch(0.72 0.18 75)"
                  strokeWidth={1.5}
                  dot={false}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="flex gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm" style={{ backgroundColor: 'oklch(0.70 0.18 155 / 80%)' }} />
              <span className="text-xs text-muted-foreground">Recommended window</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm" style={{ backgroundColor: 'oklch(0.55 0.010 240 / 40%)' }} />
              <span className="text-xs text-muted-foreground">Off window</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
