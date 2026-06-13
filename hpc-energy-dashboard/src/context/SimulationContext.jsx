import { createContext, useContext, useState, useEffect } from 'react';

const SimulationContext = createContext(null);

// Robust fallback mock data in case backend is unavailable
const DEFAULT_MOCK_RESULTS = {
  metrics: {
    baseline_energy: 142.8,
    current_energy: 124.5,
    energy_change_pct: 12.8,
    baseline_cost: 15000,
    current_cost: 11250,
    cost_change_pct: 25.0,
    baseline_carbon: 2219,
    current_carbon: 710,
    carbon_change_pct: 68.0,
    weighted_avg_power: 8.42,
    peak_power: 11.2,
    annual_energy_saved: 18.3,
    annual_cost_saved: 3750,
    annual_carbon_saved: 1.5
  },
  projections_table: [
    { category: 'IT Load (Compute)', estimated: '92.4 MWh', historical: '95.1 MWh', deviation: '-2.8%', status: 'PASS', statusType: 'pass' },
    { category: 'Cooling System (Chilled Water)', estimated: '28.1 MWh', historical: '22.4 MWh', deviation: '+25.4%', status: 'WARN', statusType: 'warn' },
    { category: 'Power Distribution Losses', estimated: '4.2 MWh', historical: '3.9 MWh', deviation: '+7.6%', status: 'PASS', statusType: 'pass' },
    { category: 'UPS Parasitic Load', estimated: '1.8 MWh', historical: '2.5 MWh', deviation: '-28.0%', status: 'FAIL', statusType: 'fail' },
    { category: 'Lighting & Auxiliary', estimated: '0.9 MWh', historical: '0.8 MWh', deviation: '+12.5%', status: 'PASS', statusType: 'pass' },
  ],
  grid_health: {
    voltage_stability: 99.2,
    harmonic_distortion: 2.1,
    transformer_load: 84.0,
    solver_load: 76,
    stability_status: 'Warning - Moderate Grid Stress',
    recommended_shift: 'Shift to off-peak (00-06)',
    insight_message: 'The current scenario shows a 12.8% energy reduction compared to the baseline trace, primarily driven by aggressive liquid cooling PUE management and scheduled training delays during peak grid pricing.'
  },
  demand_chart: {
    hours: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
    baseline_mw: [2.1, 1.8, 1.6, 2.4, 3.8, 5.1, 5.6, 5.3, 4.7, 3.9, 2.8, 2.2, 2.0],
    optimized_mw: [1.8, 1.5, 1.4, 2.0, 3.2, 4.2, 4.8, 4.5, 3.8, 3.0, 2.2, 1.8, 1.7],
    price_eur_mwh: [28, 28, 28, 34, 34, 42, 42, 42, 38, 38, 26, 26, 26],
    carbon_intensity_g: [100, 100, 100, 200, 200, 80, 80, 80, 250, 250, 120, 120, 120]
  },
  cumulative_savings: {
    hours: Array.from({ length: 24 }, (_, i) => i),
    savings_eur: [10, 25, 45, 60, 80, 105, 135, 170, 210, 250, 290, 320, 350, 390, 430, 480, 520, 560, 600, 650, 710, 780, 840, 910]
  },
  security_checks: [
    { element: 'Trafo HV/MV', type: '110→20 kV Transformer', metric: 'Loading', preFault: '42.1%', postFault: '78.3%', margin: '21.7%', status: 'PASS' },
    { element: 'Line MV-01', type: '20 kV Cable', metric: 'Loading', preFault: '34.5%', postFault: '67.2%', margin: '32.8%', status: 'PASS' },
    { element: 'Line MV-02', type: '20 kV Cable', metric: 'Loading', preFault: '28.9%', postFault: '89.1%', margin: '10.9%', status: 'WARN' },
    { element: 'Trafo MV/LV-1', type: '20→0.4 kV Transformer', metric: 'Loading', preFault: '56.7%', postFault: '92.4%', margin: '7.6%', status: 'WARN' },
    { element: 'External Grid', type: 'Grid Connection', metric: 'Voltage', preFault: '1.00 p.u.', postFault: '0.97 p.u.', margin: '0.03 p.u.', status: 'PASS' }
  ],
  simulation_results_table: [
    { timestep: 1, time: '08:03:32', power: '2.140 MW', voltage: '0.985 p.u.', loading: '42.1%', status: 'PASS' },
    { timestep: 2, time: '08:03:37', power: '2.310 MW', voltage: '0.984 p.u.', loading: '43.5%', status: 'PASS' },
    { timestep: 3, time: '08:03:42', power: '2.440 MW', voltage: '0.984 p.u.', loading: '44.2%', status: 'PASS' },
    { timestep: 4, time: '08:03:54', power: '2.800 MW', voltage: '0.981 p.u.', loading: '48.9%', status: 'PASS' },
    { timestep: 5, time: '08:04:03', power: '2.220 MW', voltage: '0.985 p.u.', loading: '42.3%', status: 'PASS' },
    { timestep: 6, time: '08:04:08', power: '5.620 MW', voltage: '0.972 p.u.', loading: '68.5%', status: 'PASS' },
    { timestep: 7, time: '08:04:13', power: '5.310 MW', voltage: '0.974 p.u.', loading: '66.1%', status: 'PASS' },
    { timestep: 8, time: '08:04:20', power: '2.250 MW', voltage: '0.985 p.u.', loading: '42.4%', status: 'PASS' },
    { timestep: 9, time: '08:04:25', power: '5.690 MW', voltage: '0.971 p.u.', loading: '69.1%', status: 'PASS' }
  ]
};

export function SimulationProvider({ children }) {
  // Config state
  const [workloadMode, setWorkloadMode] = useState('Training Run');
  const [trainingFile, setTrainingFile] = useState('train_run_1.csv');
  const [inferenceFile, setInferenceFile] = useState('inference_run_1.csv');
  const [targetPue, setTargetPue] = useState(1.25);
  const [coolingType, setCoolingType] = useState('Liquid');
  const [optimizationGoal, setOptimizationGoal] = useState('Minimize Cost');
  
  const [enableGpuLimiting, setEnableGpuLimiting] = useState(false);
  const [enableCoolingUpgrade, setEnableCoolingUpgrade] = useState(false);
  const [enableSmartScheduling, setEnableSmartScheduling] = useState(false);
  const [enableLoadBalancing, setEnableLoadBalancing] = useState(false);
  
  const [numberOfCenters, setNumberOfCenters] = useState(3);
  const [nodesPerCenter, setNodesPerCenter] = useState(64);
  const [gridBackend, setGridBackend] = useState('Synthetic HPC grid');
  const [fastMode, setFastMode] = useState(true);

  const [expansionMode, setExpansionMode] = useState(false);
  const [transformerHeadroom, setTransformerHeadroom] = useState(1.2);
  const [forecastHorizon, setForecastHorizon] = useState(30);

  // File Options
  const [trainingFiles, setTrainingFiles] = useState([
    'train_run_1.csv', 'train_run_2.csv', 'train_run_4.csv', 'train_run_5.csv'
  ]);
  const [inferenceFiles, setInferenceFiles] = useState([
    'inference_run_1.csv', 'inference_run_2.csv', 'inference_run_3.csv', 'inference_run_4.csv'
  ]);

  // Results State
  const [results, setResults] = useState(DEFAULT_MOCK_RESULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasRun, setHasRun] = useState(false);

  // Load configuration options from backend on mount
  useEffect(() => {
    async function loadOptions() {
      try {
        const res = await fetch('/api/config-options');
        if (res.ok) {
          const data = await res.json();
          if (data.training_files && data.training_files.length) {
            setTrainingFiles(data.training_files);
            setTrainingFile(data.training_files[0]);
          }
          if (data.inference_files && data.inference_files.length) {
            setInferenceFiles(data.inference_files);
            setInferenceFile(data.inference_files[0]);
          }
        }
      } catch (err) {
        console.warn('API Server unavailable, using default workload list', err);
      }
    }
    loadOptions();
  }, []);

  // Run simulation API call
  async function runSimulation() {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        workload_mode: workloadMode,
        training_file: trainingFile,
        inference_file: inferenceFile,
        target_pue: parseFloat(targetPue),
        optimization_goal: optimizationGoal,
        enable_gpu_limiting: enableGpuLimiting,
        enable_cooling_upgrade: enableCoolingUpgrade,
        enable_smart_scheduling: enableSmartScheduling,
        enable_load_balancing: enableLoadBalancing,
        number_of_centers: parseInt(numberOfCenters),
        nodes_per_center: parseInt(nodesPerCenter),
        grid_backend: gridBackend,
        fast_mode: fastMode,
        expansion_mode: expansionMode,
        transformer_headroom: parseFloat(transformerHeadroom)
      };

      const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Simulation run failed');
      }

      const data = await res.json();
      setResults(data);
      setHasRun(true);
    } catch (err) {
      console.error('Simulation API error:', err);
      setError(err.message || 'Connection to simulation server failed. Displaying simulated fallback.');
      
      // Fallback behavior: apply adjustments to mock results based on checkboxes
      const base = JSON.parse(JSON.stringify(DEFAULT_MOCK_RESULTS));
      if (enableGpuLimiting) {
        base.metrics.current_energy = base.metrics.baseline_energy * 0.85;
        base.metrics.current_cost = base.metrics.baseline_cost * 0.80;
        base.metrics.current_carbon = base.metrics.baseline_carbon * 0.85;
      } else if (enableCoolingUpgrade) {
        base.metrics.current_energy = base.metrics.baseline_energy * 0.95;
        base.metrics.current_cost = base.metrics.baseline_cost * 0.92;
        base.metrics.current_carbon = base.metrics.baseline_carbon * 0.95;
      } else if (enableSmartScheduling) {
        base.metrics.current_cost = base.metrics.baseline_cost * 0.75;
        base.metrics.current_carbon = base.metrics.baseline_carbon * 0.70;
      }
      
      // recalculate saving percentages
      base.metrics.energy_change_pct = ((base.metrics.baseline_energy - base.metrics.current_energy) / base.metrics.baseline_energy * 100).toFixed(1);
      base.metrics.cost_change_pct = ((base.metrics.baseline_cost - base.metrics.current_cost) / base.metrics.baseline_cost * 100).toFixed(1);
      base.metrics.carbon_change_pct = ((base.metrics.baseline_carbon - base.metrics.current_carbon) / base.metrics.baseline_carbon * 100).toFixed(1);
      
      setResults(base);
      setHasRun(true);
    } finally {
      setLoading(false);
    }
  }

  function resetToBaseline() {
    setEnableGpuLimiting(false);
    setEnableCoolingUpgrade(false);
    setEnableSmartScheduling(false);
    setEnableLoadBalancing(false);
    setTargetPue(1.25);
    setCoolingType('Liquid');
    setNumberOfCenters(3);
    setNodesPerCenter(64);
    setWorkloadMode('Training Run');
    setExpansionMode(false);
    setTransformerHeadroom(1.2);
    setForecastHorizon(30);
    setError(null);
  }

  const value = {
    workloadMode, setWorkloadMode,
    trainingFile, setTrainingFile,
    inferenceFile, setInferenceFile,
    targetPue, setTargetPue,
    coolingType, setCoolingType,
    optimizationGoal, setOptimizationGoal,
    enableGpuLimiting, setEnableGpuLimiting,
    enableCoolingUpgrade, setEnableCoolingUpgrade,
    enableSmartScheduling, setEnableSmartScheduling,
    enableLoadBalancing, setEnableLoadBalancing,
    numberOfCenters, setNumberOfCenters,
    nodesPerCenter, setNodesPerCenter,
    gridBackend, setGridBackend,
    fastMode, setFastMode,
    expansionMode, setExpansionMode,
    transformerHeadroom, setTransformerHeadroom,
    forecastHorizon, setForecastHorizon,
    
    trainingFiles,
    inferenceFiles,
    
    results,
    loading,
    error,
    hasRun,
    runSimulation,
    resetToBaseline
  };

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
}
