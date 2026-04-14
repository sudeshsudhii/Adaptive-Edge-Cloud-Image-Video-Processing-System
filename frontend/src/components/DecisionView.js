// frontend/src/components/DecisionView.js
import React from 'react';
import './DecisionView.css';

const DecisionView = ({ decision }) => {
  if (!decision) return null;

  const modeClass = decision.mode?.toLowerCase();

  return (
    <div className="glass-card decision-view fade-in" style={{ animationDelay: '0.15s' }}>
      <div className="section-title">
        <span className="icon">🧠</span> Decision Engine
      </div>

      <div className="decision-result">
        <div className={`decision-mode badge-${modeClass || 'cloud'}`}>
          {decision.mode}
        </div>
        <div className="decision-confidence">
          Confidence: {(decision.confidence * 100).toFixed(0)}%
        </div>
      </div>

      <p className="decision-reasoning">{decision.reasoning}</p>

      <div className="scores-grid">
        <ScoreBar label="System" value={decision.system_score} color="var(--success)" />
        <ScoreBar label="Network" value={decision.network_score} color="var(--cloud-blue)" invert />
        <ScoreBar label="Complexity" value={decision.complexity_score} color="var(--split-purple)" />
      </div>
    </div>
  );
};

const ScoreBar = ({ label, value, color, invert }) => (
  <div className="score-item">
    <div className="score-header">
      <span className="score-label">{label}</span>
      <span className="score-value">{(value * 100).toFixed(1)}%</span>
    </div>
    <div className="score-bar">
      <div
        className="score-bar-fill"
        style={{
          width: `${value * 100}%`,
          background: color,
          opacity: invert && value > 0.7 ? 0.6 : 1,
        }}
      />
    </div>
  </div>
);

export default DecisionView;
