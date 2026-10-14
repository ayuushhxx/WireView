import React, { useState, useRef, useEffect } from 'react';
import {
  ListFilter,
  Trash2,
  ArrowDown,
  Search,
} from 'lucide-react';
import type { ServerEvent } from '../types';

interface LiveEventStreamProps {
  events: ServerEvent[];
  onClear: () => void;
}

export const LiveEventStream: React.FC<LiveEventStreamProps> = ({ events, onClear }) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStage, setFilterStage] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      // Events are prepended (newest first), so scroll to top to show latest
      logContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter((ev) => {
    if (filterSeverity !== 'all' && ev.severity !== filterSeverity) return false;
    if (filterStage !== 'all' && ev.stage !== filterStage) return false;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchMsg = ev.message.toLowerCase().includes(term);
      const matchReq = ev.request_id?.toLowerCase().includes(term);
      const matchConn = ev.connection_id?.toLowerCase().includes(term);
      if (!matchMsg && !matchReq && !matchConn) return false;
    }
    return true;
  });

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Controls Bar */}
      <div className="panel-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ListFilter size={16} color="#38bdf8" />
          <span>Real-Time Server Event Stream</span>
          <span className="badge badge-info font-mono" style={{ fontSize: '0.72rem' }}>
            {filteredEvents.length} events
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-main)', borderRadius: 6, border: '1px solid var(--border-dim)', padding: '0.2rem 0.5rem' }}>
            <Search size={13} color="var(--text-dim)" />
            <input
              type="text"
              placeholder="Search ID or message..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-main)',
                fontSize: '0.78rem',
                padding: '0.2rem 0.4rem',
                outline: 'none',
                width: 140,
              }}
            />
          </div>

          {/* Stage Filter */}
          <select
            value={filterStage}
            onChange={(e) => setFilterStage(e.target.value)}
            style={{
              background: 'var(--bg-main)',
              color: 'var(--text-main)',
              border: '1px solid var(--border-dim)',
              borderRadius: 6,
              fontSize: '0.78rem',
              padding: '0.3rem 0.5rem',
              outline: 'none',
            }}
          >
            <option value="all">All Stages</option>
            <option value="tcp_accept">TCP Accept</option>
            <option value="parse">Parse</option>
            <option value="validate">Validate</option>
            <option value="route">Route</option>
            <option value="handler">Handler</option>
            <option value="serialize">Serialize</option>
            <option value="tcp_send">TCP Transmit</option>
            <option value="tcp_close">TCP Close</option>
          </select>

          {/* Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            style={{
              background: 'var(--bg-main)',
              color: 'var(--text-main)',
              border: '1px solid var(--border-dim)',
              borderRadius: 6,
              fontSize: '0.78rem',
              padding: '0.3rem 0.5rem',
              outline: 'none',
            }}
          >
            <option value="all">All Severities</option>
            <option value="info">Info</option>
            <option value="success">Success</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          {/* Auto Scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`btn ${autoScroll ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem' }}
            title="Toggle Auto-Scroll"
          >
            <ArrowDown size={13} />
            Auto-Scroll
          </button>

          {/* Clear Button */}
          <button
            onClick={onClear}
            className="btn btn-secondary"
            style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem' }}
            title="Clear UI display (server history retained)"
          >
            <Trash2 size={13} />
            Clear
          </button>
        </div>
      </div>

      {/* Events Log Body */}
      <div ref={logContainerRef} style={{ flex: 1, overflowY: 'auto', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        {filteredEvents.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '2rem', fontSize: '0.85rem' }}>
            No events match the current filter.
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const borderCol =
              ev.severity === 'error'
                ? '#ef4444'
                : ev.severity === 'warning'
                ? '#f59e0b'
                : ev.severity === 'success'
                ? '#10b981'
                : '#0ea5e9';

            return (
              <div
                key={ev.event_id}
                style={{
                  background: 'var(--bg-main)',
                  borderLeft: `3px solid ${borderCol}`,
                  borderRadius: 4,
                  padding: '0.45rem 0.75rem',
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span className="font-mono" style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.72rem' }}>
                      [{ev.stage.toUpperCase()}]
                    </span>
                    <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>
                      {ev.message}
                    </span>
                  </div>

                  {(ev.request_id || ev.connection_id) && (
                    <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                      {ev.connection_id && <span>Conn: {ev.connection_id}</span>}
                      {ev.request_id && <span>Req: {ev.request_id}</span>}
                    </div>
                  )}
                </div>

                <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                  {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};
