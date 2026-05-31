# Simplified Dashboard - What to Keep vs Remove

## Status of Current app.py 
- **4,316 lines** (way too complex!)
- **10 tabs** that confuse users
- **Too much technical jargon**
- **Not user-friendly**

## Recommendation

Instead of trying to edit the existing 4316-line file (which is error-prone), I suggest:

### **Option 1: Quick Fix (5 min)**
- Keep the existing app.py as is  
- Just simplify the sidebar to hide advanced options
- Add an "Expert Mode" toggle to show/hide technical tabs

### **Option 2: Clean Rewrite (2 hours)**
- Create a new `app_simplified.py` with only 4 tabs:
  - Tab 1: **Home** - Workload selection + quick start
  - Tab 2: **Results** - 3 cards (Energy, Cost, Carbon)
  - Tab 3: **Scheduling** - Heatmaps showing when to run
  - Tab 4: **Advanced** - All technical details (collapsible)
- Keep all the existing simulation logic
- Just change the UI

## What I Recommend

**I'll create `app_simplified.py`** with:
- ✓ Clean, modern UI with 4 tabs max
- ✓ Auto-pricing already enabled (German grid data)
- ✓ No jargon - plain English
- ✓ Progress bar during simulation
- ✓ 3-card results summary
- ✓ Optional "Expert Mode" for advanced users

**You can then:**
1. Test the simplified version: `streamlit run src/dashboard/app_simplified.py`
2. If you like it, we can make it the default
3. Keep the old app.py for backup

---

## Do You Want Me To:

**A) Create a new simplified app.py** (best clean solution)
**B) Try to patch the existing app.py** (risky, might break things)
**C) Just hide the complex tabs** with a toggle (quick fix)

Which would you prefer?
