// frontend/src/components/ProcessingTimeline.js
import React from 'react';
import './ProcessingTimeline.css';

const ProcessingTimeline = ({ taskState, uploadTime }) => {
  if (!taskState) return null;

  const created = taskState.created_at ? new Date(taskState.created_at) : null;
  const started = taskState.started_at ? new Date(taskState.started_at) : null;
  const completed = taskState.completed_at ? new Date(taskState.completed_at) : null;

  const decisionMs = created && started ? started - created : null;
  const processingMs = started && completed ? completed - started : null;
  const totalMs = created && completed ? completed - created : null;

  const fmt = (ms) => {
    if (ms == null) return '—';
    if (ms < 1) return '<1ms';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Compute bar widths proportional to total
  const total = (uploadTime || 0) + (decisionMs || 0) + (processingMs || 0);
  const pctOf = (val) => total > 0 ? Math.max(2, (val / total) * 100) : 25;

  const items = [
    { label: 'Upload', value: uploadTime, color: 'var(--accent)', pct: pctOf(uploadTime || 0) },
    { label: 'Decision', value: decisionMs, color: 'var(--warning)', pct: pctOf(decisionMs || 0) },
    { label: 'Processing', value: processingMs, color: 'var(--success)', pct: pctOf(processingMs || 0) },
  ];

  return (
    <div className="processing-timeline">
      <div className="timeline-label">Timing Breakdown</div>
      <div className="timeline-bar-row">
        {items.map((item) => (
          <div
            key={item.label}
            className="timeline-segment"
            style={{ width: `${item.pct}%`, background: item.color }}
            title={`${item.label}: ${fmt(item.value)}`}
          />
        ))}
      </div>
      <div className="timeline-items">
        {items.map((item) => (
          <div key={item.label} className="timeline-item">
            <span className="timeline-dot" style={{ background: item.color }} />
            <span className="timeline-item-label">{item.label}</span>
            <span className="timeline-item-value">{fmt(item.value)}</span>
          </div>
        ))}
        <div className="timeline-item timeline-total">
          <span className="timeline-dot" style={{ background: 'var(--text-primary)' }} />
          <span className="timeline-item-label">Total</span>
          <span className="timeline-item-value">{fmt(totalMs)}</span>
        </div>
      </div>
    </div>
  );
};

export default ProcessingTimeline;
