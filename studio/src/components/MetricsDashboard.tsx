import React from 'react';
import {
  Activity,
  Server,
  Zap,
  ArrowDownLeft,
  ArrowUpRight,
  PieChart,
  Clock,
  Layers,
} from 'lucide-react';
import type { MetricsSnapshot } from '../types';

interface MetricsDashboardProps {
  metrics: MetricsSnapshot | null;
}

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({ metrics }) => {
  if (!metrics) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading real server telemetry...
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const totalStatus = Object.values(metrics.status_categories).reduce((a, b) => a + b, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Top Counters Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
        <div className="glass-panel" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Total Requests
            </span>
            <Activity size={16} color="#06b6d4" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {metrics.total_requests}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#38bdf8', marginTop: '0.2rem', fontWeight: 600 }}>
            {metrics.requests_per_second} req / sec (5s window)
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Active TCP Sockets
            </span>
            <Server size={16} color="#10b981" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10b981', marginTop: '0.25rem' }}>
            {metrics.active_connections}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Peak concurrent: {metrics.peak_connections} | Total: {metrics.total_connections}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Avg Latency
            </span>
            <Clock size={16} color="#f59e0b" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {metrics.latency_ms.avg.toFixed(2)} ms
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            p50: {metrics.latency_ms.p50}ms | p95: {metrics.latency_ms.p95}ms | p99: {metrics.latency_ms.p99}ms
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Wire I/O Volume
            </span>
            <Zap size={16} color="#6366f1" />
          </div>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.4rem' }}>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                <ArrowDownLeft size={12} color="#10b981" /> Inbound
              </div>
              <div className="font-mono" style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                {formatBytes(metrics.total_bytes_read)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                <ArrowUpRight size={12} color="#06b6d4" /> Outbound
              </div>
              <div className="font-mono" style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                {formatBytes(metrics.total_bytes_written)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Section: Status Codes and Stage Latencies */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        {/* Status Codes Distribution */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc', marginBottom: '1rem' }}>
            <PieChart size={16} color="#38bdf8" />
            <span>HTTP Status Code Distribution</span>
          </div>

          <div style={{ display: 'flex', height: 20, borderRadius: 6, overflow: 'hidden', marginBottom: '1.25rem' }}>
            {Object.entries(metrics.status_categories).map(([cat, count]) => {
              if (count === 0 && totalStatus > 0) return null;
              const pct = totalStatus > 0 ? (count / totalStatus) * 100 : 25;
              const color =
                cat === '2xx'
                  ? '#10b981'
                  : cat === '3xx'
                  ? '#06b6d4'
                  : cat === '4xx'
                  ? '#f59e0b'
                  : '#ef4444';
              return (
                <div
                  key={cat}
                  style={{
                    width: `${pct}%`,
                    background: color,
                    transition: 'width 0.3s ease',
                  }}
                  title={`${cat}: ${count} requests (${pct.toFixed(1)}%)`}
                />
              );
            })}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
            {[
              { cat: '2xx', label: 'Success', color: '#10b981', count: metrics.status_categories['2xx'] },
              { cat: '3xx', label: 'Redirect', color: '#06b6d4', count: metrics.status_categories['3xx'] },
              { cat: '4xx', label: 'Client Err', color: '#f59e0b', count: metrics.status_categories['4xx'] },
              { cat: '5xx', label: 'Server Err', color: '#ef4444', count: metrics.status_categories['5xx'] },
            ].map((item) => (
              <div key={item.cat} style={{ background: 'var(--bg-main)', padding: '0.5rem', borderRadius: 6, border: '1px solid var(--border-dim)' }}>
                <div style={{ fontSize: '0.72rem', color: item.color, fontWeight: 700 }}>{item.cat} {item.label}</div>
                <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.1rem' }}>
                  {item.count}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Average Stage Durations */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc', marginBottom: '1rem' }}>
            <Layers size={16} color="#38bdf8" />
            <span>Average Stage Processing Times</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {Object.entries(metrics.stage_timings_ms).map(([stage, avgMs]) => (
              <div key={stage} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                  {stage}
                </span>
                <span className="font-mono" style={{ fontWeight: 700, color: '#38bdf8' }}>
                  {avgMs.toFixed(3)} ms
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
