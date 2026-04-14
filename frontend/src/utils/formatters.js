// frontend/src/utils/formatters.js

export const formatBytes = (mb) => {
  if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
  return `${mb.toFixed(2)} MB`;
};

export const formatDuration = (seconds) => {
  if (seconds < 0.001) return '<1ms';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
};

export const formatCost = (usd) => {
  if (usd === 0) return 'Free';
  if (usd < 0.0001) return `$${usd.toExponential(2)}`;
  return `$${usd.toFixed(6)}`;
};

export const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

export const modeColor = (mode) => {
  switch (mode?.toUpperCase()) {
    case 'LOCAL': return '#22c55e';
    case 'CLOUD': return '#3b82f6';
    case 'SPLIT': return '#a855f7';
    default: return '#6366f1';
  }
};

export const statusToClass = (status) => {
  switch (status?.toUpperCase()) {
    case 'PENDING': return 'badge-pending';
    case 'RUNNING': return 'badge-running';
    case 'COMPLETED': return 'badge-completed';
    case 'FAILED': return 'badge-failed';
    default: return '';
  }
};
