// frontend/src/components/PipelineStatus.js
import React, { useState, useEffect } from 'react';
import './PipelineStatus.css';

const resolveActive = (status, currentStage) => {
  if (!status || status === 'PENDING') return 0;
  if (status === 'FAILED') return 2;
  if (status === 'COMPLETED') return 3;
  if (currentStage?.includes('decision')) return 1;
  return 2;
};

const getStatusText = (activeIdx, mode, status) => {
  if (status === 'FAILED') return 'Processing Failed';
  if (activeIdx === 0) return 'Uploading...';
  if (activeIdx === 1) return 'Analyzing system...';
  if (activeIdx === 2) return `Processing on ${mode || 'EDGE'}...`;
  if (activeIdx === 3) return 'Completed';
  return 'Idle';
};

const PipelineStatus = ({ status, currentStage, mode, isDemo = false }) => {
  const [demoStep, setDemoStep] = useState(0);

  useEffect(() => {
    if (!isDemo) return;
    const interval = setInterval(() => {
      setDemoStep((prev) => (prev + 1) % 4);
    }, 2500);
    return () => clearInterval(interval);
  }, [isDemo]);

  const activeIdx = isDemo ? demoStep : resolveActive(status, currentStage);
  const displayMode = mode || (isDemo ? 'CLOUD' : 'LOCAL');

  const STAGES = [
    { key: 'upload', label: 'Upload', icon: '📤' },
    { key: 'decision', label: 'Decision', icon: '🧠' },
    { key: 'processing', label: displayMode, icon: '⚙️' },
    { key: 'complete', label: 'Complete', icon: '✅' },
  ];

  return (
    <div className="pipeline-status">
      <div className="pipeline-track">
        {STAGES.map((stage, i) => {
          const isDone = i < activeIdx;
          const isCurrent = i === activeIdx;
          const isFailed = !isDemo && status === 'FAILED' && isCurrent;

          return (
            <React.Fragment key={stage.key}>
              {i > 0 && (
                <div className={`pipeline-connector ${isDone ? 'done' : isCurrent ? 'active' : ''}`} />
              )}
              <div className={`pipeline-node ${isDone ? 'done' : ''} ${isCurrent ? 'active' : ''} ${isFailed ? 'failed' : ''}`}>
                <div className="node-icon">{isDone ? '✓' : stage.icon}</div>
                <span className="node-label">{stage.label}</span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div className="pipeline-status-text">
        {getStatusText(activeIdx, displayMode, status)}
      </div>
    </div>
  );
};

export default PipelineStatus;
