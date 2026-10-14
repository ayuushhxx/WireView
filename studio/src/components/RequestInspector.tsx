import React from 'react';
import {
  Search,
  Clock,
  Layers,
} from 'lucide-react';
import type { RequestFlow } from '../types';

interface RequestInspectorProps {
  flow: RequestFlow | null;
}

export const RequestInspector: React.FC<RequestInspectorProps> = ({ flow }) => {
  if (!flow) {
    return (
      <div className="glass-panel" style={{ padding: '3rem 1.5rem', textAlign: 'center' }}>
        <Search size={36} color="#475569" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
          No Request Selected
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: 450, margin: '0 auto' }}>
          Select any past request from the flow strip above or send a new request from the Request Lab to inspect its low-level networking lifecycle.
        </p>
      </div>
    );
  }

  const timingEntries = Object.entries(flow.stageTimings || {});
  const totalTiming = timingEntries.reduce((acc, [, val]) => acc + (val || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Overview Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
        <div className="glass-panel" style={{ padding: '0.85rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Request Target
          </div>
          <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8', marginTop: '0.2rem' }}>
            {flow.method} {flow.path}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Protocol: HTTP/1.1
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '0.85rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Socket Identity
          </div>
          <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', marginTop: '0.2rem' }}>
            {flow.connection_id}
          </div>
          <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Request ID: {flow.request_id}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '0.85rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Outcome &amp; Latency
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
            <span
              style={{
                fontSize: '1.1rem',
                fontWeight: 800,
                color: (flow.status_code || 0) < 400 ? '#10b981' : (flow.status_code || 0) < 500 ? '#f59e0b' : '#ef4444',
              }}
            >
              {flow.status_code || 'Pending'}
            </span>
            {flow.latency_ms !== undefined && (
              <span className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                ({flow.latency_ms.toFixed(2)} ms)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stage Timing Waterfall Breakdown */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>
            <Clock size={16} color="#38bdf8" />
            <span>Request Stage Execution Waterfall</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Measured with <code>time.perf_counter()</code>
          </div>
        </div>

        {timingEntries.length === 0 ? (
          <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>
            Stage timings currently being compiled...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {timingEntries.map(([stage, duration]) => {
              const durVal = duration || 0;
              const pct = totalTiming > 0 ? Math.max((durVal / totalTiming) * 100, 4) : 10;
              return (
                <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.8rem' }}>
                  <div style={{ width: 100, color: 'var(--text-muted)', textTransform: 'capitalize', fontWeight: 600 }}>
                    {stage}:
                  </div>
                  <div style={{ flex: 1, background: 'var(--bg-main)', height: 18, borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        background:
                          stage === 'handler'
                            ? '#0284c7'
                            : stage === 'parse'
                            ? '#06b6d4'
                            : stage === 'transmit'
                            ? '#10b981'
                            : '#6366f1',
                        borderRadius: 4,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                  <div className="font-mono" style={{ width: 65, textAlign: 'right', fontWeight: 700, color: '#f8fafc' }}>
                    {durVal.toFixed(3)}ms
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Structured Telemetry Events Trail for this Request */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc', marginBottom: '0.75rem' }}>
          <Layers size={16} color="#38bdf8" />
          <span>Pipeline Event Log (Tied to Request ID)</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 220, overflowY: 'auto' }}>
          {flow.events.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>No events recorded for this request.</div>
          ) : (
            flow.events.map((ev) => (
              <div
                key={ev.event_id}
                style={{
                  background: 'var(--bg-main)',
                  borderLeft: `3px solid ${
                    ev.severity === 'error'
                      ? '#ef4444'
                      : ev.severity === 'warning'
                      ? '#f59e0b'
                      : ev.severity === 'success'
                      ? '#10b981'
                      : '#0ea5e9'
                  }`,
                  padding: '0.4rem 0.65rem',
                  borderRadius: 4,
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span className="font-mono" style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.72rem' }}>
                    [{ev.stage}]
                  </span>
                  <span style={{ color: 'var(--text-main)' }}>{ev.message}</span>
                </div>
                <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                  {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
