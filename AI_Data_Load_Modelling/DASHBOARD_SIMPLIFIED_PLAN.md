# Dashboard Simplification Plan

## Current Issues
1. ✓ **Icon parameter error** - FIXED (removed unsupported `icon` parameter)
2. **Too many tabs** - 10 tabs overwhelming users
3. **Too much technical jargon** - confusing for non-experts
4. **Unclear workflow** - users don't know what features do

## Questions for You

### About Auto-Pricing
✓ **YES - We ARE taking prices automatically!**
- Using real **German grid data** (EPEX SPOT rates)
- Prices vary by time: EUR 0.027/kWh (off-peak) → EUR 0.050/kWh (peak)
- Carbon intensity also automatic: 80-250 g CO2/kWh based on renewables
- No manual entry needed!

---

## Proposed Simplified Dashboard Layout

### **HOME PAGE (Simple Entry)**
```
┌─────────────────────────────────────────┐
│  HPC Workload Optimization Dashboard    │
└─────────────────────────────────────────┘

[Select Your Workload]
  ○ Training (MLPerf benchmark)
  ○ Inference (real queries)

[Quick Optimization]
  [GPU Power Limiting]    [Smart Scheduling]
  [Cooling Upgrade]       [All of Above]
  
→ RUN SIMULATION
```

### **RESULTS PAGE (3 Simple Cards)**
```
┌──────────────┬──────────────┬──────────────┐
│   ENERGY     │    COST      │   CARBON     │
│              │              │              │
│ 0.032 MWh    │ EUR 120      │ 1,200 kg     │
│ -20% vs now  │ -EUR 30      │ -240 kg      │
│              │              │              │
└──────────────┴──────────────┴──────────────┘

[Savings Breakdown]
Annual Energy: 7.3 MWh    (-20%)
Annual Cost:   EUR 10,950 (-20%)
Annual CO2:    87.6 tons  (-20%)

[Best Time to Run This Job]
💰 Cheapest:  01:00 (EUR 0.027/kWh) - Save 45%
🌱 Greenest:  13:00 (80 g CO2/kWh) - Reduce 68%
```

### **DETAILS PAGE (Optional Expandable)**
- Grid status (real-time pricing, carbon %)
- 24-hour cost/carbon heatmap
- Technical audit (if interested)

---

## Recommended Tab Structure

### **KEEP (Essential)**
1. **Home** - Workload selection + Quick start
2. **Results** - Energy, Cost, Carbon cards + Savings
3. **Scheduling** - "When to run this job" with heatmaps
4. **Details** - (Collapsible) Grid info, audit log

### **REMOVE (Confusing)**
- ✗ Grid / Power-Flow Analysis (too technical)
- ✗ Optimization Audit (move to Details)
- ✗ Cost / Time Pricing (shown in scheduling)
- ✗ Load Balancing (internal detail)
- ✗ Hosting Capacity (internal detail)
- ✗ MLPerf Trace (too technical)
- ✗ Workload Comparison (advanced feature)
- ✗ Model Explanation (advanced feature)
- ✗ Calculation Trace (for debugging only)

---

## Simplified Sidebar Configuration

### **Simple Mode (Default)**
```
Workload
├─ Type: [Training ▼]
├─ Dataset: [train_run_1.csv ▼]

Optimization
├─ Goal: [Minimize Cost ▼]
├─ [▢] GPU Power Limiting
├─ [▢] Cooling Upgrade  
├─ [▢] Smart Scheduling
```

### **Expert Mode (Collapsible)**
- Advanced PUE settings
- Node configuration
- Grid parameters
- (Show/hide toggle)

---

## Modern UI Elements

### **Color Scheme**
- **Primary**: Simple blue (#0066CC)
- **Success**: Green for savings (#00A651)
- **Danger**: Red for warnings (#E63946)
- **Background**: Clean white/light gray

### **Typography**
- Large, readable fonts
- Clear hierarchy (H1, H2, H3)
- Minimal icons - only when helpful

### **Layout**
- Single column on mobile
- Max 2-3 columns on desktop
- Lots of whitespace
- No dense tables

---

## User Flow (Simplified)

```
START
  ↓
[SELECT WORKLOAD] Home page
  ↓
[CONFIGURE OPTIONS] Simple sidebar
  ↓
[RUN SIMULATION] Big green button
  ↓
[SEE RESULTS] 3 big cards showing savings
  ↓
[SCHEDULE OPTIMIZATION] When to run?
  ↓
[EXPLORE DETAILS] Optional for tech users
```

---

## Implementation Checklist

- [ ] **Remove icon parameter** ✓ DONE
- [ ] **Create 4-tab simplified layout**
  - [ ] Home (workload selection)
  - [ ] Results (3-card comparison)
  - [ ] Scheduling (heatmaps)
  - [ ] Details (advanced)
- [ ] **Simplify sidebar**
  - [ ] Move advanced options to Expert Mode toggle
  - [ ] Use clearer labels (no jargon)
  - [ ] Add help tooltips instead of confusion
- [ ] **Update result cards**
  - [ ] Show simple: current value, optimized value, savings %
  - [ ] No delta confusion
  - [ ] Show annual projection (just 1 line)
- [ ] **Collapse/hide complex tabs**
  - [ ] Grid Analysis → Details → Expandable section
  - [ ] MLPerf info → Hidden by default
  - [ ] Calculation trace → Debug mode only

---

## What Would You Like?

**Option A: Minimal (4 tabs)**
- Home → Results → Scheduling → Details

**Option B: Standard (5 tabs)**  
- Home → Results → Scheduling → Details → Advanced

**Option C: Keep current (10 tabs)**
- No change

**Which layout appeals to you most?** Tell me and I'll implement it!

---

## Quick Wins Already Done
✓ Automatic pricing (German grid data)
✓ Automatic carbon intensity
✓ Progress bar during simulation
✓ Simplified metric cards
✓ 24-hour cost heatmap
✓ 24-hour carbon heatmap
✓ Grid stability analysis

**What's left:** Reorganize tabs + simplify sidebar labels + hide technical jargon
