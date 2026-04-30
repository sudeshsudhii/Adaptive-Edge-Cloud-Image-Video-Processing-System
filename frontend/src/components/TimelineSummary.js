// frontend/src/components/TimelineSummary.js
import React from 'react';
import './TimelineSummary.css';

const TimelineSummary = ({ uploadMs, decisionMs, processingMs }) => {
  if (uploadMs == null && processingMs == null) return null;
  
  const total = (uploadMs || 0) + (decisionMs || 0) + (processingMs || 0);
  const fmt = (val) => val != null ? `${Math.round(val)}ms` : '-';

  return (
    <div className="timeline-summary-simple">
      <div className="timeline-stat"><span>Upload:</span> <strong>{fmt(uploadMs)}</strong></div>
      <div className="timeline-stat"><span>Decision:</span> <strong>{fmt(decisionMs)}</strong></div>
      <div className="timeline-stat"><span>Processing:</span> <strong>{fmt(processingMs)}</strong></div>
      <div className="timeline-stat total"><span>Total:</span> <strong>{fmt(total)}</strong></div>
    </div>
  );
};

export default TimelineSummary;
