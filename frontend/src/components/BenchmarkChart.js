// frontend/src/components/BenchmarkChart.js
import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, ArcElement, RadialLinearScale,
  Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Bar, Radar } from 'react-chartjs-2';
import { modeColor, formatDuration, formatCost } from '../utils/formatters';
import './BenchmarkChart.css';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, ArcElement, RadialLinearScale,
  Title, Tooltip, Legend, Filler
);

const BenchmarkChart = ({ benchmark }) => {
  if (!benchmark) return null;

  const color = modeColor(benchmark.mode);

  const barData = {
    labels: ['Latency (s)', 'CPU %', 'GPU %', 'Energy (J)', 'Speedup'],
    datasets: [{
      label: benchmark.mode,
      data: [
        benchmark.latency,
        benchmark.cpu_usage * 100,
        benchmark.gpu_usage * 100,
        benchmark.energy_j,
        benchmark.speedup,
      ],
      backgroundColor: [
        'rgba(99, 102, 241, 0.7)',
        'rgba(34, 197, 94, 0.7)',
        'rgba(168, 85, 247, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(59, 130, 246, 0.7)',
      ],
      borderRadius: 8,
      borderSkipped: false,
    }],
  };

  const barOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(26, 29, 46, 0.9)',
        cornerRadius: 8,
        padding: 10,
        titleFont: { family: 'Inter', weight: '600' },
        bodyFont: { family: 'Inter' },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
      y: { grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { family: 'Inter', size: 11 } } },
    },
  };

  const radarData = {
    labels: ['Speed', 'Efficiency', 'Cost', 'Energy', 'Throughput'],
    datasets: [{
      label: benchmark.mode,
      data: [
        Math.min(benchmark.speedup / 2, 1) * 100,
        (1 - benchmark.cpu_usage) * 100,
        benchmark.cost_usd === 0 ? 100 : Math.max(0, 100 - benchmark.cost_usd * 100000),
        Math.max(0, 100 - benchmark.energy_j),
        Math.min(benchmark.throughput * 10, 100),
      ],
      backgroundColor: `${color}22`,
      borderColor: color,
      borderWidth: 2,
      pointBackgroundColor: color,
      pointRadius: 4,
    }],
  };

  const radarOpts = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        grid: { color: 'rgba(0,0,0,0.04)' },
        ticks: { display: false },
        pointLabels: { font: { family: 'Inter', size: 11, weight: '600' } },
      },
    },
    plugins: { legend: { display: false } },
  };

  return (
    <div className="glass-card benchmark-chart fade-in full-width" style={{ animationDelay: '0.25s' }}>
      <div className="section-title">
        <span className="icon">📊</span> Benchmark Results
        <span className={`badge badge-${benchmark.mode?.toLowerCase()}`}>{benchmark.mode}</span>
      </div>

      <div className="benchmark-stats">
        <div className="stat">
          <span className="stat-label">Latency</span>
          <span className="stat-value">{formatDuration(benchmark.latency)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Cost</span>
          <span className="stat-value">{formatCost(benchmark.cost_usd)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Energy</span>
          <span className="stat-value">{benchmark.energy_j.toFixed(1)} J</span>
        </div>
        <div className="stat">
          <span className="stat-label">Speedup</span>
          <span className="stat-value">{benchmark.speedup.toFixed(2)}×</span>
        </div>
        <div className="stat">
          <span className="stat-label">Throughput</span>
          <span className="stat-value">{benchmark.throughput.toFixed(2)}/s</span>
        </div>
      </div>

      <div className="charts-row">
        <div className="chart-container">
          <Bar data={barData} options={barOpts} />
        </div>
        <div className="chart-container radar">
          <Radar data={radarData} options={radarOpts} />
        </div>
      </div>
    </div>
  );
};

export default BenchmarkChart;
