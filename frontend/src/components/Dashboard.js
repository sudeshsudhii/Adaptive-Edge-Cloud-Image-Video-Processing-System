// frontend/src/components/Dashboard.js
import React, { useState } from 'react';
import SystemProfile from './SystemProfile';
import FileUpload from './FileUpload';
import DecisionView from './DecisionView';
import TaskProgress from './TaskProgress';
import BenchmarkChart from './BenchmarkChart';
import MetricsPanel from './MetricsPanel';
import ResultCompare from './ResultCompare';
import ActivityFeed from './ActivityFeed';
import PipelineStatus from './PipelineStatus';
import { submitProcessing } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [systemProfile, setSystemProfile] = useState(null); // eslint-disable-line no-unused-vars
  const [networkProfile, setNetworkProfile] = useState(null); // eslint-disable-line no-unused-vars
  const [uploadedFile, setUploadedFile] = useState(null);
  const [rawFile, setRawFile] = useState(null);
  const [uploadTime, setUploadTime] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [taskState, setTaskState] = useState(null);
  const [decision, setDecision] = useState(null);
  const [benchmark, setBenchmark] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [selectedMode, setSelectedMode] = useState('AUTO');

  const handleProfileLoaded = (sys, net) => {
    setSystemProfile(sys);
    setNetworkProfile(net);
  };

  const handleUploaded = (result) => {
    setUploadedFile(result);
    setRawFile(result._rawFile || null);
    setUploadTime(result._uploadTimeMs || null);
    setTaskId(null);
    setTaskState(null);
    setBenchmark(null);
    setDecision(null);
  };

  const handleProcess = async () => {
    if (!uploadedFile) return;
    setProcessing(true);
    setBenchmark(null);
    setDecision(null);
    setTaskState(null);

    try {
      const inputSchema = {
        file_type: uploadedFile.file_type,
        resolution: uploadedFile.resolution,
        frames: uploadedFile.frames,
        size_mb: uploadedFile.size_mb,
      };
      const mode = selectedMode === 'AUTO' ? null : selectedMode;
      const result = await submitProcessing(inputSchema, uploadedFile.file_path, mode);
      setTaskId(result.task_id);
    } catch (err) {
      console.error('Submit failed:', err);
    }
    setProcessing(false);
  };

  const handleTaskComplete = (state) => {
    setTaskState(state);
    if (state.benchmark) setBenchmark(state.benchmark);
    if (state.result) {
      setDecision({
        mode: state.mode || state.result?.mode_used,
        system_score: 0.5,
        network_score: 0.3,
        complexity_score: 0.4,
        confidence: 0.85,
        reasoning: `Task completed using ${state.mode || state.result?.mode_used} mode in ${(state.result.processing_time_s * 1000).toFixed(0)}ms.`,
      });
    }
  };

  return (
    <div className="dashboard">
      {/* Demo Pipeline (if idle) */}
      {!uploadedFile && (
        <div className="glass-card fade-in" style={{ padding: 24, marginBottom: 20 }}>
          <div className="section-title">
            <span className="icon">🎮</span> System Pipeline Demo
          </div>
          <PipelineStatus isDemo={true} />
        </div>
      )}

      <div className="dashboard-grid">
        <SystemProfile onProfileLoaded={handleProfileLoaded} />
        <FileUpload onUploaded={handleUploaded} />
      </div>

      {/* Processing Controls */}
      {uploadedFile && (
        <div className="glass-card process-controls fade-in">
          <div className="section-title">
            <span className="icon">⚡</span> Process
          </div>
          <div className="controls-row">
            <div className="mode-selector">
              {['AUTO', 'LOCAL', 'CLOUD', 'SPLIT'].map((m) => (
                <button
                  key={m}
                  className={`mode-btn ${selectedMode === m ? 'active' : ''} ${m.toLowerCase()}`}
                  onClick={() => setSelectedMode(m)}
                >
                  {m}
                </button>
              ))}
            </div>
            {selectedMode !== 'AUTO' && (
              <span className="mode-hint">
                {selectedMode === 'LOCAL' && '⚡ Low latency, local GPU/CPU'}
                {selectedMode === 'CLOUD' && '☁️ Full cloud offload'}
                {selectedMode === 'SPLIT' && '🔀 Split edge + cloud pipeline'}
              </span>
            )}
            <button
              className="btn btn-primary"
              onClick={handleProcess}
              disabled={processing}
            >
              {processing ? '⏳ Submitting...' : '🚀 Start Processing'}
            </button>
          </div>
        </div>
      )}

      {/* Task Progress + Pipeline + Timeline */}
      {taskId && (
        <TaskProgress
          taskId={taskId}
          uploadTime={uploadTime}
          onComplete={handleTaskComplete}
        />
      )}

      {/* Before vs After comparison */}
      {taskState?.result && rawFile && (
        <ResultCompare
          originalFile={rawFile}
          result={taskState.result}
          mode={taskState.mode || taskState.result?.mode_used}
        />
      )}

      {/* Results */}
      <div className="dashboard-grid">
        {decision && <DecisionView decision={decision} />}
        <MetricsPanel />
        <ActivityFeed newTask={taskState} />
      </div>

      {benchmark && <BenchmarkChart benchmark={benchmark} />}
    </div>
  );
};

export default Dashboard;
