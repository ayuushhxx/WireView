import React from 'react';
import {
  BookOpen,
  Code2,
  Layers,
  Radio,
  ShieldAlert,
} from 'lucide-react';

export const ProtocolGuideModal: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
          <BookOpen size={20} color="#38bdf8" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc' }}>
            WireView HTTP: Systems Networking &amp; RFC 7230 Architecture
          </h2>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.6 }}>
          This educational guide details how <strong>WireView HTTP</strong> implements a genuine HTTP/1.1 engine from scratch in Python using standard-library BSD TCP sockets, completely bypassing high-level web frameworks.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        {/* TCP Socket Mechanics */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.75rem' }}>
            <Radio size={16} />
            <span>1. Low-Level TCP Socket Lifecycle</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '0.75rem', lineHeight: 1.6 }}>
            The server constructs an <code>AF_INET</code>, <code>SOCK_STREAM</code> socket, configures <code>SO_REUSEADDR</code>, binds to <code>127.0.0.1:8080</code>, and calls <code>listen(backlog=128)</code>.
          </p>
          <div style={{ background: 'var(--bg-main)', padding: '0.65rem', borderRadius: 6, border: '1px solid var(--border-dim)' }}>
            <div style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 700 }}>Bounded Thread Pool Concurrency</div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
              Unlike naive servers that spawn unbounded threads per connection (susceptible to thread exhaustion attacks), WireView uses a bounded <code>ThreadPoolExecutor(max_workers=32)</code>.
            </p>
          </div>
        </div>

        {/* StreamBuffer & TCP Chunking */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.75rem' }}>
            <Layers size={16} />
            <span>2. The TCP Byte Stream &amp; Buffering</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '0.75rem', lineHeight: 1.6 }}>
            TCP is a byte stream, not a message protocol. A single <code>recv()</code> call can return half an HTTP header, or three pipelined requests concatenated together.
          </p>
          <div style={{ background: 'var(--bg-main)', padding: '0.65rem', borderRadius: 6, border: '1px solid var(--border-dim)' }}>
            <div style={{ fontSize: '0.72rem', color: '#06b6d4', fontWeight: 700 }}>StreamBuffer Abstraction</div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
              <code>StreamBuffer</code> accumulates incoming TCP chunks into an in-memory bytearray, scanning for <code>\r\n</code> boundaries without losing read-ahead bytes needed for bodies or keep-alive requests.
            </p>
          </div>
        </div>

        {/* HTTP/1.1 Framing & Security */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: '#f59e0b', marginBottom: '0.75rem' }}>
            <ShieldAlert size={16} />
            <span>3. RFC 7230 Security &amp; Smuggling Defenses</span>
          </div>
          <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-muted)', fontSize: '0.82rem', lineHeight: 1.6 }}>
            <li><strong>Whitespace before colon:</strong> Rejected per RFC 7230 §3.2.4 with 400 Bad Request.</li>
            <li><strong>Conflicting Framing:</strong> Conflicting Transfer-Encoding + Content-Length is rejected to prevent HTTP Request Smuggling.</li>
            <li><strong>Path Traversal Defense:</strong> All file access paths are verified with <code>Path.relative_to()</code>.</li>
            <li><strong>CRLF Injection Defense:</strong> Response serializer validates that header values contain no newline control characters.</li>
          </ul>
        </div>

        {/* Accurate Content-Length */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: '#10b981', marginBottom: '0.75rem' }}>
            <Code2 size={16} />
            <span>4. Accurate Byte Serialization</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '0.75rem', lineHeight: 1.6 }}>
            In HTTP/1.1, <code>Content-Length</code> represents the exact number of OCTETS (bytes) on the wire, not character length.
          </p>
          <div style={{ background: 'var(--bg-main)', padding: '0.65rem', borderRadius: 6, border: '1px solid var(--border-dim)' }}>
            <div style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 700 }}>Bodyless Semantics</div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
              Responses with status 204 No Content, 304 Not Modified, or HEAD methods strictly omit body transmission, while HEAD accurately retains the Content-Length header.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
