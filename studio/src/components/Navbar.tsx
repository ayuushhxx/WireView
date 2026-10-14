import React from 'react';
import {
  Activity,
  Radio,
  Server,
  Layers,
  BarChart3,
  Search,
  ListFilter,
  BookOpen,
  Home,
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  sseStatus: 'connected' | 'reconnecting' | 'disconnected';
  activeConnections: number;
  uptimeSeconds: number;
  totalRequests: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  sseStatus,
  activeConnections,
  uptimeSeconds,
  totalRequests,
}) => {
  const formatUptime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${mins}m ${s}s`;
  };

  return (
    <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '0.75rem 1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Logo and Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-glow-cyan)',
              }}
            >
              <Radio size={18} color="#fff" />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em', color: '#f8fafc' }}>
                WireView <span style={{ color: '#38bdf8' }}>Studio</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: '#64748b', fontWeight: 600, letterSpacing: '0.04em' }}>
                LOW-LEVEL SOCKET INSPECTOR
              </div>
            </div>
          </div>

          {/* SSE Connection Status */}
          <div
            className={`badge ${
              sseStatus === 'connected'
                ? 'badge-success'
                : sseStatus === 'reconnecting'
                ? 'badge-warning'
                : 'badge-danger'
            }`}
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor:
                  sseStatus === 'connected' ? '#10b981' : sseStatus === 'reconnecting' ? '#f59e0b' : '#ef4444',
                boxShadow: sseStatus === 'connected' ? '0 0 8px #10b981' : 'none',
              }}
            />
            {sseStatus === 'connected' ? 'SSE STREAM LIVE' : sseStatus === 'reconnecting' ? 'RECONNECTING...' : 'DISCONNECTED'}
          </div>
        </div>

        {/* Quick Stats Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1.25rem',
            background: 'var(--bg-subtle)',
            padding: '0.4rem 1rem',
            borderRadius: 8,
            border: '1px solid var(--border-dim)',
            fontSize: '0.82rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Server size={14} color="#38bdf8" />
            <span style={{ color: 'var(--text-muted)' }}>Sockets:</span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#f8fafc' }}>
              {activeConnections} active
            </span>
          </div>

          <div style={{ width: 1, height: 16, background: 'var(--border-dim)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Activity size={14} color="#10b981" />
            <span style={{ color: 'var(--text-muted)' }}>Reqs:</span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#f8fafc' }}>
              {totalRequests}
            </span>
          </div>

          <div style={{ width: 1, height: 16, background: 'var(--border-dim)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Uptime:</span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#f8fafc' }}>
              {formatUptime(uptimeSeconds)}
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {[
            { id: 'topology', label: 'Pipeline Flow', icon: Layers },
            { id: 'metrics', label: 'Metrics', icon: BarChart3 },
            { id: 'inspector', label: 'Inspector', icon: Search },
            { id: 'events', label: 'Event Log', icon: ListFilter },
            { id: 'guide', label: 'RFC Guide', icon: BookOpen },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="btn"
                style={{
                  background: isActive ? 'var(--bg-card)' : 'transparent',
                  color: isActive ? '#38bdf8' : 'var(--text-muted)',
                  border: isActive ? '1px solid var(--border-bright)' : '1px solid transparent',
                  padding: '0.45rem 0.85rem',
                  fontSize: '0.82rem',
                }}
              >
                <Icon size={15} />
                {tab.label}
              </button>
            );
          })}

          <a
            href="/"
            className="btn btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.82rem', marginLeft: '0.5rem', textDecoration: 'none' }}
            title="Go to Homepage"
          >
            <Home size={15} />
            Landing
          </a>
        </nav>
      </div>
    </header>
  );
};
