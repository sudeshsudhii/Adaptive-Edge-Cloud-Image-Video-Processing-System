// frontend/src/components/ResultCompare.js
import React, { useState, useRef, useEffect } from 'react';
import './ResultCompare.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const ResultCompare = ({ originalFile, result, mode }) => {
  const [sliderPos, setSliderPos] = useState(50);
  const [originalUrl, setOriginalUrl] = useState(null);
  const containerRef = useRef(null);
  const dragging = useRef(false);

  useEffect(() => {
    if (!originalFile) return;
    const url = URL.createObjectURL(originalFile);
    setOriginalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [originalFile]);

  if (!result?.output_path || !originalUrl) return null;

  // Build processed image URL — serve from backend's static outputs
  const processedUrl = `${API_BASE}/outputs/${result.task_id}/result.png`;

  const handleMove = (clientX) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    setSliderPos(pct);
  };

  const onPointerDown = (e) => {
    dragging.current = true;
    handleMove(e.clientX);
  };
  const onPointerMove = (e) => { if (dragging.current) handleMove(e.clientX); };
  const onPointerUp = () => { dragging.current = false; };

  return (
    <div className="glass-card result-compare fade-in">
      <div className="section-title">
        <span className="icon">🔍</span> Before vs After
        <span className={`badge badge-${mode?.toLowerCase() || 'local'}`}>{mode || 'LOCAL'}</span>
      </div>

      <div
        ref={containerRef}
        className="compare-container"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        {/* Original (full width, behind) */}
        <img src={originalUrl} alt="Original" className="compare-img compare-original" />

        {/* Processed (clipped by slider) */}
        <div className="compare-clip" style={{ width: `${sliderPos}%` }}>
          <img
            src={processedUrl}
            alt="Processed"
            className="compare-img compare-processed"
            onError={(e) => { e.target.src = originalUrl; }}
          />
        </div>

        {/* Slider handle */}
        <div className="compare-slider" style={{ left: `${sliderPos}%` }}>
          <div className="slider-handle">
            <span>◀▶</span>
          </div>
        </div>

        {/* Labels */}
        <span className="compare-label label-left">Processed</span>
        <span className="compare-label label-right">Original</span>
      </div>

      {result.processing_time_s != null && (
        <div className="compare-meta">
          <span>⏱ {(result.processing_time_s * 1000).toFixed(0)}ms</span>
          <span>📂 {result.stages_completed?.length || 0} stages</span>
          <span>🎯 {result.mode_used}</span>
        </div>
      )}
    </div>
  );
};

export default ResultCompare;
