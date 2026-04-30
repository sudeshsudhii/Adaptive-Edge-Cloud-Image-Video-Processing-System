// frontend/src/services/api.js
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Auth interceptor ────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor ────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token');
    }
    return Promise.reject(err);
  }
);

// ═══════════════════════════════════════════════════════════
//  API FUNCTIONS
// ═══════════════════════════════════════════════════════════

export const login = async (username, password) => {
  const { data } = await api.post('/auth/login', { username, password });
  localStorage.setItem('auth_token', data.access_token);
  return data;
};

export const getSystemProfile = async () => {
  const { data } = await api.get('/system/profile');
  return data;
};

export const getNetworkProfile = async () => {
  const { data } = await api.get('/system/network');
  return data;
};

export const getFullProfile = async () => {
  const { data } = await api.get('/system/full');
  return data;
};

export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const submitProcessing = async (inputSchema, filePath, mode, priority) => {
  const params = new URLSearchParams();
  params.append('file_path', filePath);
  if (mode) params.append('mode', mode);
  if (priority) params.append('priority', priority);

  const { data } = await api.post(`/process?${params.toString()}`, inputSchema);
  return data;
};

export const getTaskStatus = async (taskId) => {
  const { data } = await api.get(`/status/${taskId}`);
  return data;
};

export const getBenchmark = async (taskId) => {
  const { data } = await api.get(`/benchmark/${taskId}`);
  return data;
};

export const getAllBenchmarks = async () => {
  const { data } = await api.get('/benchmark');
  return data;
};

export const getHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};

export const getMetrics = async () => {
  const { data } = await api.get('/metrics');
  return data;
};

export default api;
