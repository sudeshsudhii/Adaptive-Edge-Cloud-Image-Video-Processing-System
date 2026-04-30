// frontend/src/components/ModeBadge.js
import React from 'react';
import './ModeBadge.css';

const ModeBadge = ({ mode, reasoning }) => {
  if (!mode) return null;
  const isLocal = mode === 'LOCAL';
  const isCloud = mode === 'CLOUD';
  const isSplit = mode === 'SPLIT';
  
  let icon = '⚡';
  if (isCloud) icon = '☁️';
  if (isSplit) icon = '🔀';

  return (
    <div className={`mode-badge-card mode-${mode.toLowerCase()}`}>
      <div className="mode-badge-header">
        <span className="mode-title">Mode: {mode} {icon}</span>
      </div>
      {reasoning && <div className="mode-reason">Reason: {reasoning}</div>}
    </div>
  );
};

export default ModeBadge;
