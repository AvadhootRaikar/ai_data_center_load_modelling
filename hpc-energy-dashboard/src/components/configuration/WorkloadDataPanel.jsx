import { useState } from 'react';
import { HardDrive } from 'lucide-react';
import { useSimulation } from '../../context/SimulationContext';

export default function WorkloadDataPanel() {
  const [advanced, setAdvanced] = useState(false);
  
  const {
    workloadMode,
    trainingFile, setTrainingFile,
    inferenceFile, setInferenceFile,
    trainingFiles,
    inferenceFiles,
    numberOfCenters, setNumberOfCenters,
    nodesPerCenter, setNodesPerCenter
  } = useSimulation();

  // Convert centers to percent for slider (range 1 to 10)
  const centersPercent = ((numberOfCenters - 1) / (10 - 1)) * 100;
  
  // Convert nodes to percent for slider (range 10 to 100)
  const nodesPercent = ((nodesPerCenter - 10) / (100 - 10)) * 100;

  const showTraining = workloadMode === 'Training Run' || workloadMode === 'Simultaneous Training + Inference';
  const showInference = workloadMode === 'Inference Run' || workloadMode === 'Simultaneous Training + Inference';

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-header-left">
          <HardDrive size={14} style={{ color: 'var(--color-muted-foreground)' }} />
          <span className="card-title">Workload Data</span>
        </div>
        <div className="advanced-toggle" onClick={() => setAdvanced(!advanced)}>
          <span className="advanced-toggle-label">Advanced Parameters</span>
          <div className={`toggle-track ${advanced ? 'active' : ''}`}>
            <div className="toggle-knob" />
          </div>
        </div>
      </div>
      <div className="card-body">
        {showTraining && (
          <div style={{ marginBottom: 12 }}>
            <span className="slider-row-label" style={{ display: 'block', marginBottom: 4 }}>Training Trace File</span>
            <select 
              value={trainingFile} 
              onChange={(e) => setTrainingFile(e.target.value)}
              className="input-field"
              style={{ width: '100%', padding: '6px 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', background: 'var(--color-input)' }}
            >
              {trainingFiles.map(file => (
                <option key={file} value={file}>{file}</option>
              ))}
            </select>
          </div>
        )}

        {showInference && (
          <div style={{ marginBottom: 12 }}>
            <span className="slider-row-label" style={{ display: 'block', marginBottom: 4 }}>Inference Trace File</span>
            <select 
              value={inferenceFile} 
              onChange={(e) => setInferenceFile(e.target.value)}
              className="input-field"
              style={{ width: '100%', padding: '6px 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', background: 'var(--color-input)' }}
            >
              {inferenceFiles.map(file => (
                <option key={file} value={file}>{file}</option>
              ))}
            </select>
          </div>
        )}

        <div className="slider-row">
          <div className="slider-row-header">
            <span className="slider-row-label">HPC Centers</span>
            <div className="slider-row-value">
              <span className="slider-row-value-num">{numberOfCenters}</span>
              <span className="slider-row-value-unit">clusters</span>
            </div>
          </div>
          <div className="slider-track" style={{ position: 'relative' }}>
            <div className="slider-fill" style={{ width: `${centersPercent}%` }} />
            <div className="slider-thumb" style={{ left: `calc(${centersPercent}% - 8px)` }} />
            <input 
              type="range"
              min="1"
              max="10"
              step="1"
              value={numberOfCenters}
              onChange={(e) => setNumberOfCenters(parseInt(e.target.value))}
              style={{
                position: 'absolute',
                top: 0, left: 0, width: '100%', height: '100%',
                opacity: 0, cursor: 'pointer'
              }}
            />
          </div>
        </div>

        {advanced && (
          <div className="slider-row">
            <div className="slider-row-header">
              <span className="slider-row-label">Nodes per Center</span>
              <div className="slider-row-value">
                <span className="slider-row-value-num">{nodesPerCenter}</span>
                <span className="slider-row-value-unit">nodes</span>
              </div>
            </div>
            <div className="slider-track" style={{ position: 'relative' }}>
              <div className="slider-fill" style={{ width: `${nodesPercent}%` }} />
              <div className="slider-thumb" style={{ left: `calc(${nodesPercent}% - 8px)` }} />
              <input 
                type="range"
                min="10"
                max="100"
                step="5"
                value={nodesPerCenter}
                onChange={(e) => setNodesPerCenter(parseInt(e.target.value))}
                style={{
                  position: 'absolute',
                  top: 0, left: 0, width: '100%', height: '100%',
                  opacity: 0, cursor: 'pointer'
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

