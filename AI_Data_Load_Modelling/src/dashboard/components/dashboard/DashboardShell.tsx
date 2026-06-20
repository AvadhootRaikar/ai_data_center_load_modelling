'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  LayoutDashboard,
  Zap,
  BarChart3,
  Activity,
  Droplets,
  ChevronLeft,
} from 'lucide-react'
import OverviewTab from './tabs/OverviewTab'
import GridPricingTab from './tabs/GridPricingTab'
import ScenarioTab from './tabs/ScenarioTab'
import GridHealthTab from './tabs/GridHealthTab'
import WaterTab from './tabs/WaterTab'

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'grid', label: 'Grid & Pricing', icon: Zap },
  { id: 'scenarios', label: 'Scenarios', icon: BarChart3 },
  { id: 'grid-health', label: 'Grid Health', icon: Activity },
  { id: 'water', label: 'Water & Cooling', icon: Droplets },
] as const

type TabId = (typeof TABS)[number]['id']

export default function DashboardShell() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top header bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur-sm">
        <div className="max-w-screen-xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
          >
            <ChevronLeft className="size-4" />
            <span className="hidden sm:inline">Walkthrough</span>
          </Link>

          <div className="h-4 w-px bg-border" />

          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-electric animate-pulse" />
            <span className="text-sm font-semibold text-foreground">
              AI Data Center Dashboard
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground font-mono">
            <span className="hidden sm:inline">Frankfurt, DE</span>
            <span className="hidden sm:inline">·</span>
            <span>40.5 kW baseline</span>
          </div>
        </div>
      </header>

      {/* Tab navigation + content */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as TabId)}
        className="flex flex-col flex-1"
      >
        {/* Tab bar */}
        <div className="border-b border-border bg-background sticky top-14 z-20">
          <div className="max-w-screen-xl mx-auto px-4 sm:px-6">
            <TabsList className="h-12 bg-transparent p-0 gap-0 rounded-none w-full justify-start overflow-x-auto">
              {TABS.map(({ id, label, icon: Icon }) => (
                <TabsTrigger
                  key={id}
                  value={id}
                  className="h-12 rounded-none border-b-2 border-transparent data-[state=active]:border-electric data-[state=active]:text-electric data-[state=active]:bg-transparent px-4 gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                >
                  <Icon className="size-4" />
                  <span className="hidden sm:inline">{label}</span>
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
        </div>

        {/* Tab content */}
        <div className="max-w-screen-xl w-full mx-auto px-4 sm:px-6 py-6 flex-1">
          <TabsContent value="overview">
            <OverviewTab />
          </TabsContent>
          <TabsContent value="grid">
            <GridPricingTab />
          </TabsContent>
          <TabsContent value="scenarios">
            <ScenarioTab />
          </TabsContent>
          <TabsContent value="grid-health">
            <GridHealthTab />
          </TabsContent>
          <TabsContent value="water">
            <WaterTab />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
