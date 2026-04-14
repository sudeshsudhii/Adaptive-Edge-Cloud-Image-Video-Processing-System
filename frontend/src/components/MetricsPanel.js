// frontend/src/components/MetricsPanel.js
import React, { useEffect, useState } from 'react';
import { getMetrics } from '../services/api';
import './MetricsPanel.css';

const MetricsPanel = () => {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await getMetrics();
        setMetrics(data);
      } catch (e) { /* silent */ }
    };
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return null;

  const sys = metrics.system || {};

  return (
    <div className="glass-card metrics-panel fade-in" style={{ animationDelay: '0.3s' }}>
      <div className="section-title">
        <span className="icon">📡</span> Live Metrics
      </div>

      <div className="metrics-grid">
        <Gauge label="CPU" value={sys.cpu_percent || 0} max={100} unit="%" color="var(--accent)" />
        <Gauge label="RAM" value={sys.ram_percent || 0} max={100} unit="%" color="var(--success)" />
        <div className="metric-stat">
          <span className="metric-label">RAM Free</span>
          <span className="metric-value">{(sys.ram_available_gb || 0).toFixed(1)} GB</span>
        </div>
        <div className="metric-stat">
          <span className="metric-label">HTTP Requests</span>
          <span className="metric-value">
            {Object.values(metrics.counters || {}).reduce((a, b) => a + b, 0).toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  );
};

const Gauge = ({ label, value, max, unit, color }) => {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="gauge">
      <div className="gauge-ring">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(0,0,0,0.04)" strokeWidth="8" />
          <circle
            cx="50" cy="50" r="42" fill="none"
            stroke={color} strokeWidth="8"
            strokeDasharray={`${pct * 2.64} 264`}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
            style={{ transition: 'stroke-dasharray 0.5s ease' }}
          />
        </svg>
        <div className="gauge-text">
          <span className="gauge-value">{value.toFixed(0)}</span>
          <span className="gauge-unit">{unit}</span>
        </div>
      </div>
      <span className="gauge-label">{label}</span>
    </div>
  );
};

export default MetricsPanel;
