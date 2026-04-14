// frontend/src/components/SystemProfile.js
import React, { useEffect, useState } from 'react';
import { getFullProfile } from '../services/api';
import { formatPercent } from '../utils/formatters';
import './SystemProfile.css';

const SystemProfile = ({ onProfileLoaded }) => {
  const [system, setSystem] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const data = await getFullProfile();
      setSystem(data.system);
      setNetwork(data.network);
      if (onProfileLoaded) onProfileLoaded(data.system, data.network);
    } catch (err) {
      console.error('Profile fetch failed:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchProfile(); }, []);

  return (
    <div className="glass-card system-profile fade-in">
      <div className="section-title">
        <span className="icon">🖥️</span> System Profile
        <button className="btn btn-secondary btn-sm" onClick={fetchProfile} disabled={loading}>
          {loading ? '...' : '↻ Refresh'}
        </button>
      </div>

      {system ? (
        <div className="profile-grid">
          <div className="profile-item">
            <span className="label">CPU</span>
            <span className="value">{system.cpu_cores} cores @ {system.cpu_freq} GHz</span>
          </div>
          <div className="profile-item">
            <span className="label">CPU Load</span>
            <span className="value">{formatPercent(system.cpu_load)}</span>
            <div className="mini-bar">
              <div className="mini-bar-fill" style={{ width: formatPercent(system.cpu_load), background: system.cpu_load > 0.7 ? 'var(--danger)' : 'var(--accent)' }} />
            </div>
          </div>
          <div className="profile-item">
            <span className="label">GPU</span>
            <span className="value">{system.gpu_available ? `${system.gpu_cores} cores, ${system.gpu_vram_mb} MB` : 'Not available'}</span>
          </div>
          <div className="profile-item">
            <span className="label">RAM</span>
            <span className="value">{system.ram_gb} GB</span>
          </div>
          <div className="profile-item">
            <span className="label">Battery</span>
            <span className="value">{system.battery === -1 ? 'AC Power' : `${system.battery}%`}</span>
          </div>
          {network && (
            <>
              <div className="profile-item">
                <span className="label">Latency</span>
                <span className="value">{network.latency_ms} ms</span>
              </div>
              <div className="profile-item">
                <span className="label">Bandwidth</span>
                <span className="value">{network.bandwidth_mbps} Mbps</span>
              </div>
            </>
          )}
        </div>
      ) : (
        <p className="muted">Loading system profile...</p>
      )}
    </div>
  );
};

export default SystemProfile;
