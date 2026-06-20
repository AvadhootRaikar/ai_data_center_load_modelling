'use client'

import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import Link from 'next/link'
import {
  Cpu,
  Zap,
  Droplets,
  Wind,
  BarChart3,
  ArrowRight,
  Server,
  Thermometer,
  Activity,
  Globe,
  Leaf,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

// ─── Section fade-in wrapper ──────────────────────────────────────────────────

function FadeSection({
  children,
  className = '',
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px 0px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ─── Animated stat bubble ─────────────────────────────────────────────────────

function StatBubble({
  value,
  label,
  color = 'electric',
}: {
  value: string
  label: string
  color?: 'electric' | 'emerald' | 'amber'
}) {
  const colorMap = {
    electric: 'border-electric text-electric',
    emerald: 'border-emerald text-emerald-glow',
    amber: 'border-amber text-amber-glow',
  }
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border bg-surface p-4 gap-1 ${colorMap[color]}`}
    >
      <span className="text-2xl font-bold font-mono leading-none">{value}</span>
      <span className="text-xs text-muted-foreground text-center leading-tight">{label}</span>
    </div>
  )
}

// ─── Flow diagram node ────────────────────────────────────────────────────────

function FlowNode({
  icon: Icon,
  label,
  color = 'electric',
}: {
  icon: React.ElementType
  label: string
  color?: 'electric' | 'emerald' | 'amber'
}) {
  const colorMap = {
    electric: 'text-electric border-electric glow-electric',
    emerald: 'text-emerald-glow border-emerald glow-emerald',
    amber: 'text-amber-glow border-amber glow-amber',
  }
  return (
    <div
      className={`flex flex-col items-center gap-2 rounded-xl border bg-surface p-4 w-24 ${colorMap[color]}`}
    >
      <Icon className="size-7" />
      <span className="text-xs text-center text-foreground leading-tight font-medium">{label}</span>
    </div>
  )
}

function FlowArrow() {
  return (
    <div className="flex items-center">
      <div className="h-px w-6 bg-border" />
      <ArrowRight className="size-4 text-muted-foreground" />
    </div>
  )
}

// ─── Section header ───────────────────────────────────────────────────────────

function SectionHeader({
  step,
  title,
  subtitle,
}: {
  step: string
  title: string
  subtitle: string
}) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-xs font-mono text-electric uppercase tracking-widest">{step}</span>
      <h2 className="text-3xl md:text-4xl font-bold text-foreground text-balance leading-tight">
        {title}
      </h2>
      <p className="text-muted-foreground text-base leading-relaxed max-w-xl">{subtitle}</p>
    </div>
  )
}

// ─── Main walkthrough ─────────────────────────────────────────────────────────

export default function WalkthroughPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center min-h-screen px-6 py-24 text-center overflow-hidden">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              'linear-gradient(oklch(0.65 0.20 240) 1px, transparent 1px), linear-gradient(90deg, oklch(0.65 0.20 240) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
          className="relative z-10 flex flex-col items-center gap-6 max-w-3xl"
        >
          <div className="flex items-center gap-2 rounded-full border border-electric px-4 py-1.5 text-xs text-electric font-mono uppercase tracking-widest">
            <Activity className="size-3" />
            AI Data Center — Live Energy Dashboard
          </div>

          <h1 className="text-5xl md:text-7xl font-bold text-foreground text-balance leading-[1.1]">
            The Hidden Cost of<br />
            <span className="text-electric">AI Compute</span>
          </h1>

          <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl text-balance">
            Every GPU training run, every inference call, every model weight loaded — it all consumes
            real electricity, generates heat, and uses water. This dashboard shows you exactly how
            much, and how to optimise it.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            <StatBubble value="40.5 kW" label="Baseline load" color="electric" />
            <StatBubble value="6,080 kg" label="CO₂ / month" color="amber" />
            <StatBubble value="109.6 m³" label="Water / month" color="emerald" />
            <StatBubble value="1.36" label="PUE" color="electric" />
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="flex gap-3 mt-4"
          >
            <Button
              size="lg"
              render={<Link href="/dashboard" />}
              className="bg-electric text-background font-semibold hover:brightness-110 glow-electric"
            >
              Open Dashboard
              <ArrowRight data-icon="inline-end" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              render={<a href="#power" />}
            >
              Learn how it works
            </Button>
          </motion.div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1"
        >
          <span className="text-xs text-muted-foreground font-mono">scroll to explore</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 1.4, ease: 'easeInOut' }}
            className="w-px h-8 bg-electric/40"
          />
        </motion.div>
      </section>

      {/* ── Section 1: Power consumption ──────────────────────────────────────── */}
      <section id="power" className="px-6 py-24 max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <FadeSection>
            <SectionHeader
              step="01 / Power"
              title="Where does the electricity go?"
              subtitle="A typical AI data center draws power across three main subsystems. Understanding each is the first step to optimisation."
            />
            <div className="mt-8 flex flex-col gap-3">
              {[
                {
                  icon: Cpu,
                  label: 'IT Load',
                  value: '29.8 kW',
                  desc: 'GPUs, CPUs, networking switches — the actual compute.',
                  color: 'electric' as const,
                },
                {
                  icon: Wind,
                  label: 'Cooling',
                  value: '10.7 kW',
                  desc: 'CRAC units, chillers, and fans that remove heat.',
                  color: 'amber' as const,
                },
                {
                  icon: Zap,
                  label: 'Overhead',
                  value: '~1–2 kW',
                  desc: 'UPS losses, lighting, power distribution.',
                  color: 'emerald' as const,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-start gap-4 rounded-xl border bg-surface p-4"
                >
                  <div className={`mt-0.5 ${item.color === 'electric' ? 'text-electric' : item.color === 'amber' ? 'text-amber-glow' : 'text-emerald-glow'}`}>
                    <item.icon className="size-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm">{item.label}</span>
                      <span className="font-mono text-sm text-electric">{item.value}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </FadeSection>

          <FadeSection delay={0.2}>
            <div className="rounded-2xl border bg-surface p-6 flex flex-col gap-6">
              <div className="text-sm font-mono text-electric uppercase tracking-wider">
                Power Flow
              </div>
              <div className="flex items-center justify-center gap-1 flex-wrap">
                <FlowNode icon={Zap} label="Grid 230 V" color="amber" />
                <FlowArrow />
                <FlowNode icon={Server} label="UPS / PDU" color="electric" />
                <FlowArrow />
                <FlowNode icon={Cpu} label="8× GPU Nodes" color="electric" />
              </div>
              <div className="flex items-center justify-center gap-1 flex-wrap">
                <FlowNode icon={Thermometer} label="Heat Generated" color="amber" />
                <FlowArrow />
                <FlowNode icon={Wind} label="Cooling System" color="emerald" />
                <FlowArrow />
                <FlowNode icon={Droplets} label="Water Rejected" color="emerald" />
              </div>

              <div className="border-t pt-4 flex flex-col gap-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total draw</span>
                  <span className="font-mono text-foreground">40.5 kW</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">PUE</span>
                  <span className="font-mono text-electric">1.36</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Cooling overhead</span>
                  <span className="font-mono text-amber-glow">26.4 %</span>
                </div>
              </div>
            </div>
          </FadeSection>
        </div>
      </section>

      {/* ── Section 2: German Grid & Pricing ──────────────────────────────────── */}
      <section className="px-6 py-24 bg-surface">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
          <FadeSection delay={0.1} className="order-2 md:order-1">
            <div className="rounded-2xl border bg-background p-6 flex flex-col gap-4">
              <div className="text-sm font-mono text-electric uppercase tracking-wider">
                German Day-Ahead Prices (SMARD)
              </div>
              {/* Stylised price bar chart */}
              <div className="flex items-end gap-1 h-24 w-full">
                {Array.from({ length: 24 }, (_, h) => {
                  const p = 20 + 30 * Math.sin((2 * Math.PI * (h - 8)) / 24) + 5
                  const height = Math.max(10, Math.min(100, (p / 70) * 100))
                  const isLow = p < 30
                  return (
                    <div
                      key={h}
                      className="flex-1 rounded-sm"
                      style={{
                        height: `${height}%`,
                        backgroundColor: isLow
                          ? 'oklch(0.70 0.18 155 / 70%)'
                          : 'oklch(0.65 0.20 240 / 50%)',
                      }}
                      title={`${h}:00 — ~${Math.round(p)} €/MWh`}
                    />
                  )
                })}
              </div>
              <div className="flex justify-between text-xs text-muted-foreground font-mono">
                <span>00:00</span>
                <span>06:00</span>
                <span>12:00</span>
                <span>18:00</span>
                <span>23:00</span>
              </div>
              <div className="flex gap-3 mt-1">
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-full bg-emerald-glow" />
                  <span className="text-xs text-muted-foreground">Low price window</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-full bg-electric/50" />
                  <span className="text-xs text-muted-foreground">Peak period</span>
                </div>
              </div>
            </div>
          </FadeSection>

          <FadeSection className="order-1 md:order-2">
            <SectionHeader
              step="02 / Grid"
              title="The German electricity market"
              subtitle="Germany's grid has wildly variable day-ahead prices driven by renewable generation. A smart data center can exploit this to cut bills significantly."
            />
            <div className="mt-6 grid grid-cols-2 gap-3">
              <StatBubble value="€12.57" label="Cost / 24 h" color="electric" />
              <StatBubble value="€377" label="Cost / 30 days" color="electric" />
              <StatBubble value="~48 €/MWh" label="Avg spot price" color="amber" />
              <StatBubble value="36.7%" label="Max savings (TOU)" color="emerald" />
            </div>
          </FadeSection>
        </div>
      </section>

      {/* ── Section 3: Carbon emissions ───────────────────────────────────────── */}
      <section className="px-6 py-24 max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <FadeSection>
            <SectionHeader
              step="03 / Carbon"
              title="Carbon intensity of AI workloads"
              subtitle="The German grid carbon intensity varies by time of day as solar and wind generation fluctuate. Running training jobs during green windows can halve scope 2 emissions."
            />
            <div className="mt-6 flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                {[
                  { window: '00:00–06:00', label: 'Green window', pct: 85, color: 'emerald' as const },
                  { window: '06:00–18:00', label: 'Mixed', pct: 50, color: 'electric' as const },
                  { window: '18:00–22:00', label: 'Peak (fossil heavy)', pct: 20, color: 'amber' as const },
                ].map((row) => (
                  <div key={row.window} className="flex flex-col gap-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-mono text-muted-foreground">{row.window}</span>
                      <span className={row.color === 'emerald' ? 'text-emerald-glow' : row.color === 'amber' ? 'text-amber-glow' : 'text-electric'}>
                        {row.label}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full ${row.color === 'emerald' ? 'bg-emerald-glow' : row.color === 'amber' ? 'bg-amber-glow' : 'bg-electric'}`}
                        style={{ width: `${row.pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-3 flex-wrap mt-2">
                <StatBubble value="6,080 kg" label="CO₂ / 30 days" color="amber" />
                <StatBubble value="210 g/kWh" label="Avg grid intensity" color="amber" />
                <StatBubble value="62 kg/d" label="Savings w/ green sched." color="emerald" />
              </div>
            </div>
          </FadeSection>

          <FadeSection delay={0.2}>
            <div className="rounded-2xl border bg-surface p-6 flex flex-col gap-4">
              <div className="flex items-center gap-2 text-emerald-glow">
                <Leaf className="size-5" />
                <span className="font-semibold">Carbon reduction levers</span>
              </div>
              {[
                { label: 'Shift to green window', saving: '−30%', desc: 'Run LLM training 00:00–06:00' },
                { label: 'Match renewable supply', saving: '−62 kg/d', desc: 'Follow wind + solar curves' },
                { label: 'Reduce PUE to 1.2', saving: '−11%', desc: 'Better cooling = less total draw' },
                { label: 'GPU power capping', saving: '−17%', desc: 'Cap TDP at 85% during inference' },
              ].map((item) => (
                <div key={item.label} className="flex items-start justify-between gap-4 border-b pb-3 last:border-0 last:pb-0">
                  <div>
                    <div className="text-sm font-medium">{item.label}</div>
                    <div className="text-xs text-muted-foreground">{item.desc}</div>
                  </div>
                  <span className="text-emerald-glow font-mono font-bold text-sm whitespace-nowrap">{item.saving}</span>
                </div>
              ))}
            </div>
          </FadeSection>
        </div>
      </section>

      {/* ── Section 4: Water & Cooling ────────────────────────────────────────── */}
      <section className="px-6 py-24 bg-surface">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
          <FadeSection delay={0.1} className="order-2 md:order-1">
            <div className="rounded-2xl border bg-background p-6 flex flex-col gap-5">
              <div className="text-sm font-mono text-electric uppercase tracking-wider flex items-center gap-2">
                <Droplets className="size-4 text-emerald-glow" />
                Water & Cooling
              </div>
              <div className="grid grid-cols-2 gap-3">
                <StatBubble value="109.6 m³" label="Water / month" color="emerald" />
                <StatBubble value="0.45 L/kWh" label="WUE" color="emerald" />
                <StatBubble value="€5,248" label="Annual water cost" color="electric" />
                <StatBubble value="1.36" label="PUE" color="electric" />
              </div>
              <div className="border-t pt-4 text-sm text-muted-foreground leading-relaxed">
                Water is used in cooling towers to reject heat from the facility. Every 1°C rise in
                setpoint saves ~3–5% cooling energy and reduces water evaporation.
              </div>
            </div>
          </FadeSection>

          <FadeSection className="order-1 md:order-2">
            <SectionHeader
              step="04 / Cooling"
              title="Cooling is the silent water consumer"
              subtitle="Cooling towers evaporate water to reject heat. A 40 kW data center can consume over 100 m³ of water per month — roughly the same as a family home in 8 months."
            />
            <div className="mt-6 flex flex-col gap-3">
              {[
                {
                  icon: Thermometer,
                  label: 'Raise setpoint +2°C',
                  impact: 'Save 5–8% cooling energy',
                  color: 'amber' as const,
                },
                {
                  icon: Wind,
                  label: 'Free cooling (economiser)',
                  impact: 'Zero water use when ambient < 10°C',
                  color: 'emerald' as const,
                },
                {
                  icon: Droplets,
                  label: 'Liquid cooling (RDHX)',
                  impact: 'Lower WUE, higher precision',
                  color: 'electric' as const,
                },
              ].map((item) => (
                <div key={item.label} className="flex items-start gap-3 rounded-xl border bg-surface p-3">
                  <item.icon className={`size-4 mt-0.5 ${item.color === 'amber' ? 'text-amber-glow' : item.color === 'emerald' ? 'text-emerald-glow' : 'text-electric'}`} />
                  <div>
                    <div className="text-sm font-medium">{item.label}</div>
                    <div className="text-xs text-muted-foreground">{item.impact}</div>
                  </div>
                </div>
              ))}
            </div>
          </FadeSection>
        </div>
      </section>

      {/* ── Section 5: Optimization ───────────────────────────────────────────── */}
      <section className="px-6 py-24 max-w-6xl mx-auto">
        <FadeSection>
          <div className="text-center flex flex-col items-center gap-4 mb-12">
            <span className="text-xs font-mono text-electric uppercase tracking-widest">05 / Optimization</span>
            <h2 className="text-3xl md:text-4xl font-bold text-balance">
              10 scenarios. One goal — cut waste.
            </h2>
            <p className="text-muted-foreground max-w-xl text-balance">
              The simulation engine evaluates 10 distinct strategies from simple power capping to
              full combined optimisation. The dashboard lets you compare them interactively.
            </p>
          </div>
        </FadeSection>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { name: 'TOU Shifting', saving: '36.7%', color: 'electric' },
            { name: 'Cooling Opt.', saving: '15.8%', color: 'emerald' },
            { name: 'VM Consolidation', saving: '23.0%', color: 'electric' },
            { name: 'Renewable Matching', saving: '29.9%', color: 'emerald' },
            { name: 'GPU Power Cap', saving: '17.3%', color: 'electric' },
            { name: 'Thermal Storage', saving: '25.7%', color: 'emerald' },
            { name: 'Liquid Cooling', saving: '12.1%', color: 'amber' },
            { name: 'Freq. Response', saving: '9.1%', color: 'amber' },
            { name: 'Grid Freq. Resp.', saving: '9.1%', color: 'amber' },
            { name: 'Combined Stack', saving: '61.2%', color: 'electric' },
          ].map((s, i) => (
            <FadeSection key={s.name} delay={i * 0.05}>
              <div className={`rounded-xl border bg-surface p-3 text-center flex flex-col gap-1 ${s.color === 'electric' ? 'border-electric/30' : s.color === 'emerald' ? 'border-emerald/30' : 'border-amber/30'}`}>
                <span className={`text-xl font-bold font-mono ${s.color === 'electric' ? 'text-electric' : s.color === 'emerald' ? 'text-emerald-glow' : 'text-amber-glow'}`}>
                  {s.saving}
                </span>
                <span className="text-xs text-muted-foreground leading-tight">{s.name}</span>
              </div>
            </FadeSection>
          ))}
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────────────────────── */}
      <section className="px-6 py-32 bg-surface">
        <FadeSection>
          <div className="max-w-3xl mx-auto text-center flex flex-col items-center gap-6">
            <div className="flex items-center gap-2 text-electric">
              <BarChart3 className="size-5" />
              <Globe className="size-5" />
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-balance">
              Ready to explore the data?
            </h2>
            <p className="text-muted-foreground text-lg leading-relaxed text-balance">
              The dashboard connects live to your FastAPI backend (SMARD, pandapower, optimization
              engine). When offline it runs on precomputed simulation data so you always have
              something to explore.
            </p>
            <div className="flex gap-3 flex-wrap justify-center">
              <Button
                size="lg"
                render={<Link href="/dashboard" />}
                className="bg-electric text-background font-semibold hover:brightness-110 glow-electric"
              >
                Open Dashboard
                <ArrowRight data-icon="inline-end" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                render={
                  <a
                    href="https://github.com/AvadhootRaikar/ai_data_center_load_modelling"
                    target="_blank"
                    rel="noreferrer"
                  />
                }
              >
                View Source
              </Button>
            </div>
          </div>
        </FadeSection>
      </section>
    </main>
  )
}
