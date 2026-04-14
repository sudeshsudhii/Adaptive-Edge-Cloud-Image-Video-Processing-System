// frontend/src/components/TaskProgress.js
import React, { useEffect, useState, useRef } from 'react';
import { getTaskStatus } from '../services/api';
import TaskWebSocket from '../services/websocket';
import { statusToClass, formatDuration } from '../utils/formatters';
import './TaskProgress.css';

const TaskProgress = ({ taskId, onComplete }) => {
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
  }, [taskId]);

  if (!taskId) return null;

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

      {state && (
        <>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${state.progress_pct || 0}%` }} />
          </div>
          <div className="progress-details">
            <span>{(state.progress_pct || 0).toFixed(0)}%</span>
            {state.current_stage && <span className="stage">Stage: {state.current_stage}</span>}
            {state.mode && <span className={`badge badge-${state.mode?.toLowerCase()}`}>{state.mode}</span>}
          </div>
          {state.result && (
            <div className="result-summary">
              <span>⏱ {formatDuration(state.result.processing_time_s)}</span>
              <span>📂 {state.result.stages_completed?.length || 0} stages</span>
            </div>
          )}
          {state.error && <p className="error-text">❌ {state.error}</p>}
        </>
      )}
    </div>
  );
};

export default TaskProgress;
