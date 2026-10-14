import React, { useState } from 'react';
import {
  Send,
  Zap,
} from 'lucide-react';

interface RequestTestingPanelProps {
  onTriggerRequest?: () => void;
}

interface TestPreset {
  id: string;
  name: string;
  method: string;
  path: string;
  description: string;
  category: 'standard' | 'rest' | 'security' | 'errors';
  body?: string;
  headers?: Record<string, string>;
}

const PRESETS: TestPreset[] = [
  {
    id: 'health',
    name: 'GET /health',
    method: 'GET',
    path: '/health',
    description: 'Server uptime and active TCP connection count.',
    category: 'standard',
  },
  {
    id: 'info',
    name: 'GET /api/info',
    method: 'GET',
    path: '/api/info',
    description: 'Inspect engine capabilities, methods, and RFC limits.',
    category: 'standard',
  },
  {
    id: 'items_list',
    name: 'GET /api/items',
    method: 'GET',
    path: '/api/items',
    description: 'Retrieve collection of networking RFC demo items.',
    category: 'rest',
  },
  {
    id: 'items_create',
    name: 'POST /api/items',
    method: 'POST',
    path: '/api/items',
    description: 'Add a new networking RFC resource with JSON payload.',
    category: 'rest',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: 'RFC 9110: HTTP Semantics',
      category: 'Standards',
      description: 'Defines overall architecture and semantics of HTTP.',
      layer: 'Application',
    }, null, 2),
  },
  {
    id: 'echo_post',
    name: 'POST /api/echo',
    method: 'POST',
    path: '/api/echo',
    description: 'Echo back received JSON body with framing verification.',
    category: 'rest',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client: 'WireView Studio',
      timestamp: Date.now(),
      purpose: 'Verify raw socket parsing',
    }, null, 2),
  },
  {
    id: 'test_404',
    name: '404 Unknown Route',
    method: 'GET',
    path: '/api/nonexistent/service',
    description: 'Route does not match any registered pattern.',
    category: 'errors',
  },
  {
    id: 'test_405',
    name: '405 Method Not Allowed',
    method: 'POST',
    path: '/api/time',
    description: 'Route exists for GET, but POST raises 405 with Allow header.',
    category: 'errors',
  },
  {
    id: 'test_500',
    name: '500 Server Error Sim',
    method: 'GET',
    path: '/api/test/error',
    description: 'Trigger exception handler and RFC 500 serialization.',
    category: 'errors',
  },
  {
    id: 'test_traversal',
    name: 'Path Traversal Defense',
    method: 'GET',
    path: '/static/../../etc/passwd',
    description: 'Attempts directory escape outside static directory.',
    category: 'security',
  },
];

export const RequestTestingPanel: React.FC<RequestTestingPanelProps> = ({ onTriggerRequest }) => {
  const [method, setMethod] = useState('GET');
  const [path, setPath] = useState('/api/info');
  const [headersStr, setHeadersStr] = useState('Content-Type: application/json');
  const [bodyStr, setBodyStr] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<any>(null);

  // Applies a preset and immediately fires the request
  const sendPreset = async (preset: TestPreset) => {
    setMethod(preset.method);
    setPath(preset.path);
    const hStr = preset.headers
      ? Object.entries(preset.headers).map(([k, v]) => `${k}: ${v}`).join('\n')
      : 'Content-Type: application/json';
    setHeadersStr(hStr);
    setBodyStr(preset.body || '');

    // Fire immediately with preset values (don't wait for state update)
    setIsLoading(true);
    const start = performance.now();

    const headers: Record<string, string> = {};
    if (hStr.trim()) {
      hStr.split('\n').forEach((line) => {
        const idx = line.indexOf(':');
        if (idx > -1) headers[line.substring(0, idx).trim()] = line.substring(idx + 1).trim();
      });
    }

    const options: RequestInit = { method: preset.method, headers };
    if (['POST', 'PUT', 'PATCH'].includes(preset.method) && preset.body) {
      options.body = preset.body;
    }

    try {
      const res = await fetch(preset.path, options);
      const latency = performance.now() - start;
      const text = await res.text();
      let resBody: any = null;
      try { resBody = JSON.parse(text); } catch { resBody = text; }
      const resHeaders: Record<string, string> = {};
      res.headers.forEach((v, k) => { resHeaders[k] = v; });
      setLastResponse({ status: res.status, statusText: res.statusText, headers: resHeaders, body: resBody, latencyMs: latency });
      if (onTriggerRequest) onTriggerRequest();
    } catch (err: any) {
      setLastResponse({ status: 0, statusText: 'Network Error', body: err.message, latencyMs: performance.now() - start });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    setIsLoading(true);
    const start = performance.now();

    const headers: Record<string, string> = {};
    if (headersStr.trim()) {
      headersStr.split('\n').forEach((line) => {
        const idx = line.indexOf(':');
        if (idx > -1) {
          headers[line.substring(0, idx).trim()] = line.substring(idx + 1).trim();
        }
      });
    }

    const options: RequestInit = {
      method,
      headers,
    };

    if (['POST', 'PUT', 'PATCH'].includes(method) && bodyStr.trim()) {
      options.body = bodyStr;
    }

    try {
      const res = await fetch(path, options);
      const latency = performance.now() - start;

      let resBody: any = null;
      const text = await res.text();
      try {
        resBody = JSON.parse(text);
      } catch {
        resBody = text;
      }

      const resHeaders: Record<string, string> = {};
      res.headers.forEach((v, k) => {
        resHeaders[k] = v;
      });

      setLastResponse({
        status: res.status,
        statusText: res.statusText,
        headers: resHeaders,
        body: resBody,
        latencyMs: latency,
      });

      if (onTriggerRequest) {
        onTriggerRequest();
      }
    } catch (err: any) {
      setLastResponse({
        status: 0,
        statusText: 'Network Error / Socket Refused',
        body: err.message,
        latencyMs: performance.now() - start,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Zap size={16} color="#38bdf8" />
          <span>Interactive Request Lab</span>
        </div>
      </div>

      <div style={{ padding: '1rem', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Quick Presets Grid */}
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
            Educational Scenarios
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.4rem' }}>
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => sendPreset(p)}
                className="btn btn-secondary"
                style={{
                  padding: '0.4rem 0.6rem',
                  fontSize: '0.74rem',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  textAlign: 'left',
                  borderRadius: 6,
                }}
                title={p.description}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', width: '100%' }}>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      color:
                        p.category === 'security'
                          ? '#ef4444'
                          : p.category === 'errors'
                          ? '#f59e0b'
                          : p.category === 'rest'
                          ? '#10b981'
                          : '#38bdf8',
                    }}
                  >
                    {p.method}
                  </span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
                    {p.name.replace(/^[A-Z]+\s/, '')}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Request Builder */}
        <div style={{ background: 'var(--bg-main)', padding: '0.85rem', borderRadius: 8, border: '1px solid var(--border-dim)' }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.6rem' }}>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="font-mono"
              style={{
                background: 'var(--bg-card)',
                color: '#38bdf8',
                border: '1px solid var(--border-bright)',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                fontSize: '0.82rem',
                fontWeight: 700,
                outline: 'none',
              }}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
              <option value="OPTIONS">OPTIONS</option>
              <option value="HEAD">HEAD</option>
            </select>

            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/api/info"
              className="font-mono"
              style={{
                flex: 1,
                background: 'var(--bg-card)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-bright)',
                padding: '0.4rem 0.75rem',
                borderRadius: 6,
                fontSize: '0.82rem',
                outline: 'none',
              }}
            />

            <button
              onClick={handleSend}
              disabled={isLoading}
              className="btn btn-primary"
              style={{ padding: '0.4rem 1rem', fontSize: '0.82rem' }}
            >
              {isLoading ? '...' : <><Send size={13} /> Send</>}
            </button>
          </div>

          {['POST', 'PUT', 'PATCH'].includes(method) && (
            <div style={{ marginTop: '0.5rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: 600 }}>
                JSON Body:
              </div>
              <textarea
                value={bodyStr}
                onChange={(e) => setBodyStr(e.target.value)}
                rows={3}
                className="font-mono"
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  color: '#a5f3fc',
                  border: '1px solid var(--border-bright)',
                  padding: '0.5rem',
                  borderRadius: 6,
                  fontSize: '0.76rem',
                  resize: 'vertical',
                  outline: 'none',
                }}
              />
            </div>
          )}
        </div>

        {/* Instant Response Preview */}
        {lastResponse && (
          <div style={{ background: 'var(--bg-main)', padding: '0.85rem', borderRadius: 8, border: '1px solid var(--border-dim)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span
                  className={`badge ${
                    lastResponse.status >= 200 && lastResponse.status < 300
                      ? 'badge-success'
                      : lastResponse.status < 500
                      ? 'badge-warning'
                      : 'badge-danger'
                  }`}
                >
                  {lastResponse.status} {lastResponse.statusText}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Roundtrip: {lastResponse.latencyMs.toFixed(1)}ms
                </span>
              </div>
            </div>

            <pre
              className="font-mono"
              style={{
                fontSize: '0.72rem',
                color: '#94a3b8',
                background: 'var(--bg-panel)',
                padding: '0.5rem',
                borderRadius: 4,
                maxHeight: 120,
                overflowY: 'auto',
              }}
            >
              {typeof lastResponse.body === 'object'
                ? JSON.stringify(lastResponse.body, null, 2)
                : String(lastResponse.body)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
