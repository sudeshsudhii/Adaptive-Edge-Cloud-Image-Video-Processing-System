// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import { login, getHealth } from './services/api';
import './App.css';

function App() {
  const [isReady, setIsReady] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      try {
        await getHealth();
        setBackendStatus('connected');

        // Auto-login in dev mode (auth disabled)
        const token = localStorage.getItem('auth_token');
        if (!token) {
          try {
            await login('admin', 'admin123');
          } catch (e) {
            // Auth might be disabled, that's fine
          }
        }
        setIsReady(true);
      } catch (err) {
        setBackendStatus('disconnected');
        setError('Cannot connect to backend. Make sure the FastAPI server is running on port 8000.');
        // Retry after 3s
        setTimeout(() => {
          setBackendStatus('checking');
          init();
        }, 3000);
      }
    };
    init();
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">
          <span>Edge-Cloud</span> Processor
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="app-version">v2.0</span>
          <span className={`badge ${backendStatus === 'connected' ? 'badge-completed' : backendStatus === 'checking' ? 'badge-pending' : 'badge-failed'}`}>
            {backendStatus === 'connected' ? '● Connected' : backendStatus === 'checking' ? '● Connecting...' : '● Disconnected'}
          </span>
        </div>
      </header>

      {error && backendStatus === 'disconnected' && (
        <div className="glass-card" style={{ padding: 20, marginBottom: 20, borderColor: 'var(--danger)' }}>
          <p style={{ color: 'var(--danger)', fontWeight: 600 }}>⚠️ {error}</p>
        </div>
      )}

      {isReady ? (
        <Dashboard />
      ) : (
        backendStatus === 'checking' && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <div className="upload-spinner" style={{ width: 40, height: 40, margin: '0 auto 16px' }} />
            <p className="muted">Connecting to backend...</p>
          </div>
        )
      )}
    </div>
  );
}

export default App;
