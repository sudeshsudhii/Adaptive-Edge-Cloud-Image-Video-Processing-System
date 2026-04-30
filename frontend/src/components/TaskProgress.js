// frontend/src/components/TaskProgress.js
import React, { useEffect, useState, useRef } from 'react';
import { getTaskStatus } from '../services/api';
import TaskWebSocket from '../services/websocket';
import { statusToClass, formatDuration } from '../utils/formatters';
import PipelineStatus from './PipelineStatus';
import TimelineSummary from './TimelineSummary';
import ModeBadge from './ModeBadge';
import './TaskProgress.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const TaskProgress = ({ taskId, uploadTime, onComplete }) => {
  const [state, setState] = useState(null);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;

    // Poll fallback
    const poll = async () => {
      try {
        const s = await getTaskStatus(taskId);
        setState(s);
        if (s.status === 'COMPLETED' || s.status === 'FAILED') {
          clearInterval(pollRef.current);
          if (s.status === 'COMPLETED' && onComplete) onComplete(s);
        }
      } catch (err) { /* silent */ }
    };

    poll();
    pollRef.current = setInterval(poll, 1500);

    // WebSocket (optional upgrade)
    try {
      wsRef.current = new TaskWebSocket(taskId, (data) => {
        setState((prev) => ({ ...prev, ...data }));
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          clearInterval(pollRef.current);
          if (data.status === 'COMPLETED' && onComplete) onComplete(data);
        }
      });
      wsRef.current.connect();
    } catch (e) { /* WS unavailable, fallback to polling */ }

    return () => {
      clearInterval(pollRef.current);
      wsRef.current?.disconnect();
    };
  }, [taskId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!taskId) return null;

  const isComplete = state?.status === 'COMPLETED';

  return (
    <div className="glass-card task-progress fade-in" style={{ animationDelay: '0.2s' }}>
      <div className="section-title">
        <span className="icon">⏱️</span> Task Progress
      </div>

      <div className="task-info">
        <div className="task-id">
          <span className="label">Task ID</span>
          <code>{taskId}</code>
        </div>
        <span className={`badge ${statusToClass(state?.status)}`}>
          {state?.status || 'PENDING'}
        </span>
      </div>

      {/* Pipeline Status Indicator */}
      <PipelineStatus
        status={state?.status}
        currentStage={state?.current_stage}
        mode={state?.mode || state?.result?.mode_used}
      />
      <ModeBadge 
        mode={state?.mode || state?.result?.mode_used} 
        reasoning={state?.result ? `Completed using ${state.mode || state.result?.mode_used} mode in ${(state.result.processing_time_s * 1000).toFixed(0)}ms.` : null} 
      />

      {state && (
        <>
          <div className="progress-bar" style={{ marginTop: 16 }}>
            <div className="progress-bar-fill" style={{ width: `${state.progress_pct || 0}%` }} />
          </div>
          <div className="progress-details">
            <span>{(state.progress_pct || 0).toFixed(0)}%</span>
            {state.current_stage && <span className="stage">Stage: {state.current_stage}</span>}
            {state.mode && <span className={`badge badge-${state.mode?.toLowerCase()}`}>{state.mode}</span>}
          </div>

          {/* Processing Timeline */}
          {state.created_at && (
            <TimelineSummary 
              uploadMs={uploadTime}
              decisionMs={state.started_at ? new Date(state.started_at) - new Date(state.created_at) : null}
              processingMs={state.completed_at ? new Date(state.completed_at) - new Date(state.started_at) : null}
            />
          )}

          {state.result && (
            <div className="result-summary">
              <span>⏱ {formatDuration(state.result.processing_time_s)}</span>
              <span>📂 {state.result.stages_completed?.length || 0} stages</span>
            </div>
          )}

          {/* Download Button */}
          {isComplete && state.result?.output_path && (
            <a
              className="btn btn-primary download-btn"
              href={`${API_BASE}/outputs/${state.result.task_id}/result.png`}
              download={`processed_${taskId}.png`}
              target="_blank"
              rel="noreferrer"
            >
              ⬇️ Download Result
            </a>
          )}

          {state.error && <p className="error-text">❌ {state.error}</p>}
        </>
      )}
    </div>
  );
};

export default TaskProgress;
