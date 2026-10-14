import React from 'react';
import type { PipelineStage, RequestFlow } from '../types';

interface PipelineVisualizerProps {
  selectedFlow: RequestFlow | null;
  recentFlows: RequestFlow[];
  onSelectFlow: (flow: RequestFlow) => void;
}

// ── Layout constants ─────────────────────────────────────────────────────────
const W = 800;   // SVG canvas width
const H = 320;   // SVG canvas height

const NODE_W = 120;
const NODE_H = 56;

// U-shaped layout: 5 nodes on top row, 3 on bottom row (right→left)
//   tcp_accept → buffer → parse → validate → route
//                                              ↓
//   tcp_send  ←  serialize  ← handler
const TOP_Y = 60;
const BOT_Y = 220;

// Top-row X centers: evenly spaced across full width
const TOP_XS = [70, 220, 370, 520, 670];
// Bottom-row X centers: right to left, mirroring the bend
const BOT_XS = [670, 520, 370];   // handler, serialize, tcp_send (right→left visual)
// But we reorder them so tcp_send ends up leftward:
// handler at x=670, serialize at x=520, tcp_send at x=370

// Node definitions — id must match PipelineStage
const NODES: { id: PipelineStage; label: string; sub: string; x: number; y: number }[] = [
  { id: 'tcp_accept', label: 'TCP Accept',    sub: 'socket.accept()',      x: TOP_XS[0], y: TOP_Y },
  { id: 'buffer',     label: 'StreamBuffer',  sub: 'recv() + CRLF scan',  x: TOP_XS[1], y: TOP_Y },
  { id: 'parse',      label: 'HTTP Parser',   sub: 'RFC 7230 headers',     x: TOP_XS[2], y: TOP_Y },
  { id: 'validate',   label: 'Validator',     sub: 'Framing & limits',     x: TOP_XS[3], y: TOP_Y },
  { id: 'route',      label: 'Router',        sub: 'Pattern dispatch',     x: TOP_XS[4], y: TOP_Y },
  { id: 'handler',    label: 'Handler',       sub: 'REST & CRUD logic',    x: BOT_XS[0], y: BOT_Y },
  { id: 'serialize',  label: 'Serializer',    sub: 'Status / Date / Len',  x: BOT_XS[1], y: BOT_Y },
  { id: 'tcp_send',   label: 'TCP Transmit',  sub: 'sendall() to socket',  x: BOT_XS[2], y: BOT_Y },
];

// Link tuples: [from-id, to-id]
const LINKS: [PipelineStage, PipelineStage][] = [
  ['tcp_accept', 'buffer'],
  ['buffer',     'parse'],
  ['parse',      'validate'],
  ['validate',   'route'],
  ['route',      'handler'],    // vertical bend down
  ['handler',    'serialize'],  // right → left on bottom
  ['serialize',  'tcp_send'],
];

const STAGE_ORDER: PipelineStage[] = [
  'tcp_accept','buffer','parse','validate','route','handler','serialize','tcp_send',
];

// ── Color palette by state ───────────────────────────────────────────────────
type NodeState = 'idle' | 'pending' | 'active' | 'completed' | 'error';

const COLORS: Record<NodeState, { fill: string; stroke: string; text: string; dot: string }> = {
  idle:      { fill: '#0d1424', stroke: '#1e293b', text: '#475569', dot: '#1e293b' },
  pending:   { fill: '#0d1424', stroke: '#1e293b', text: '#475569', dot: '#1e293b' },
  active:    { fill: '#071e38', stroke: '#0ea5e9', text: '#38bdf8', dot: '#0ea5e9' },
  completed: { fill: '#041f12', stroke: '#059669', text: '#34d399', dot: '#10b981' },
  error:     { fill: '#2a0808', stroke: '#dc2626', text: '#f87171', dot: '#ef4444' },
};

const METHOD_COLORS: Record<string, string> = {
  GET: '#38bdf8', POST: '#10b981', PUT: '#f59e0b', DELETE: '#ef4444',
  OPTIONS: '#a78bfa', HEAD: '#64748b', PATCH: '#fb923c',
};

// ── Helper: build SVG path between two node centres ──────────────────────────
function buildEdge(from: typeof NODES[0], to: typeof NODES[0]): string {
  const hw = NODE_W / 2;
  const hh = NODE_H / 2;

  if (from.x === to.x) {
    // Vertical (route → handler)
    return `M ${from.x} ${from.y + hh} L ${to.x} ${to.y - hh}`;
  }
  if (to.x > from.x) {
    // Left-to-right (top row)
    return `M ${from.x + hw} ${from.y} L ${to.x - hw} ${to.y}`;
  }
  // Right-to-left (bottom row)
  return `M ${from.x - hw} ${from.y} L ${to.x + hw} ${to.y}`;
}

// ── Component ────────────────────────────────────────────────────────────────
export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({
  selectedFlow,
  recentFlows,
  onSelectFlow,
}) => {
  // Current animation step index: while animating, step 0..N-1 has stage[step] as 'active'
  // When animation finishes or not active, animatingStep is null
  const [animatingStep, setAnimatingStep] = React.useState<number | null>(null);
  const [speedMs, setSpeedMs] = React.useState<number>(360); // 360ms per stage = calm, readable ~2.8s traversal
  const animTimerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const lastFlowIdRef = React.useRef<string | null>(null);

  const startAnimation = React.useCallback((stages: PipelineStage[], customSpeed?: number) => {
    if (animTimerRef.current) {
      clearInterval(animTimerRef.current);
      animTimerRef.current = null;
    }
    if (stages.length === 0) {
      setAnimatingStep(null);
      return;
    }
    const delay = customSpeed ?? speedMs;
    setAnimatingStep(0);
    let step = 0;
    animTimerRef.current = setInterval(() => {
      step += 1;
      if (step >= stages.length) {
        setAnimatingStep(null);
        if (animTimerRef.current) {
          clearInterval(animTimerRef.current);
          animTimerRef.current = null;
        }
      } else {
        setAnimatingStep(step);
      }
    }, delay);
  }, [speedMs]);

  React.useEffect(() => {
    if (!selectedFlow) {
      setAnimatingStep(null);
      lastFlowIdRef.current = null;
      return;
    }

    const isNewFlow = selectedFlow.request_id !== lastFlowIdRef.current;
    lastFlowIdRef.current = selectedFlow.request_id;

    // Only auto-animate if this is a newly arrived flow from a triggered command!
    const isLatestActiveFlow = recentFlows.length > 0 && recentFlows[0]?.request_id === selectedFlow.request_id;

    const stagesToReveal = STAGE_ORDER.filter(s =>
      (selectedFlow.stagesCompleted as string[]).includes(s)
    );

    if (isNewFlow && isLatestActiveFlow && stagesToReveal.length > 0) {
      startAnimation(stagesToReveal);
    } else if (isNewFlow) {
      // User clicked an older historical flow: render it directly without forcing an animation
      setAnimatingStep(null);
    }

    return () => {
      if (animTimerRef.current) {
        clearInterval(animTimerRef.current);
        animTimerRef.current = null;
      }
    };
  }, [selectedFlow?.request_id, startAnimation, recentFlows]);

  const getNodeState = (id: PipelineStage): NodeState => {
    if (!selectedFlow) return 'idle';

    const stagesToReveal = STAGE_ORDER.filter(s =>
      (selectedFlow.stagesCompleted as string[]).includes(s)
    );

    // During playback animation: the front stage is 'active', earlier stages are 'completed'
    if (animatingStep !== null && animatingStep < stagesToReveal.length) {
      const activeStage = stagesToReveal[animatingStep];
      if (id === activeStage) return 'active';
      const completedSlice = stagesToReveal.slice(0, animatingStep);
      if (completedSlice.includes(id)) return 'completed';
      return 'pending';
    }

    // Static / live request state:
    const cur = selectedFlow.currentStage;
    if (cur === 'failed') {
      if (stagesToReveal.length === 0) return 'pending';
      const lastOk = stagesToReveal[stagesToReveal.length - 1];
      const failIdx = STAGE_ORDER.indexOf(lastOk);
      const thisIdx = STAGE_ORDER.indexOf(id);
      if (failIdx >= 0 && thisIdx === failIdx + 1) return 'error';
      return stagesToReveal.includes(id) ? 'completed' : 'pending';
    }

    if (stagesToReveal.includes(id)) return 'completed';
    if (cur === id) return 'active';
    return 'pending';
  };

  const edgeColor = (from: PipelineStage, to: PipelineStage) => {
    const fs = getNodeState(from);
    const ts = getNodeState(to);
    if (ts === 'error') return '#dc2626';
    if (fs === 'completed' && ts === 'active') return '#0ea5e9';
    if (fs === 'completed' && ts === 'completed') return '#10b981';
    return '#1e293b';
  };

  const edgeAnimated = (from: PipelineStage, to: PipelineStage) => {
    const fs = getNodeState(from);
    const ts = getNodeState(to);
    return fs === 'completed' && ts === 'active';
  };

  const statusColor = (code?: number) =>
    !code ? '#64748b'
    : code < 300 ? '#10b981'
    : code < 400 ? '#06b6d4'
    : code < 500 ? '#f59e0b'
    : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', minHeight: 0, overflow: 'hidden' }}>

      {/* ── Request history strip ─────────────────────────────────────────── */}
      <div className="glass-panel" style={{ padding: '0.65rem 0.9rem', flexShrink: 0 }}>
        <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.06em', color: 'var(--text-dim)', marginBottom: '0.45rem' }}>
          Live Request Stream — click to inspect pipeline
        </div>
        <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto', paddingBottom: '2px' }}>
          {recentFlows.length === 0
            ? <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                No requests yet — click a preset on the left!
              </span>
            : recentFlows.map((flow) => {
                const isSel = selectedFlow?.request_id === flow.request_id;
                const done  = flow.currentStage === 'completed' || flow.currentStage === 'failed';
                return (
                  <button key={flow.request_id} onClick={() => onSelectFlow(flow)}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                      background: isSel ? '#071e38' : 'var(--bg-subtle)',
                      border: `1px solid ${isSel ? '#0ea5e9' : 'var(--border-dim)'}`,
                      borderRadius: 6, padding: '0.28rem 0.55rem', cursor: 'pointer',
                      whiteSpace: 'nowrap', fontSize: '0.74rem', color: 'var(--text-main)',
                      boxShadow: isSel ? '0 0 10px rgba(14,165,233,0.25)' : 'none',
                      transition: 'all 0.15s',
                    }}>
                    <span style={{ fontWeight: 800, fontSize: '0.66rem',
                      color: METHOD_COLORS[flow.method] ?? '#a78bfa' }}>
                      {flow.method}
                    </span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{flow.path}</span>
                    {done && flow.status_code && (
                      <span style={{ fontWeight: 800, color: statusColor(flow.status_code) }}>
                        {flow.status_code}
                      </span>
                    )}
                    {!done && <span style={{ color: '#06b6d4', fontSize: '0.68rem' }}>⏳</span>}
                    {flow.latency_ms !== undefined && (
                      <span style={{ color: 'var(--text-dim)', fontSize: '0.66rem' }}>
                        {flow.latency_ms.toFixed(1)}ms
                      </span>
                    )}
                  </button>
                );
              })}
        </div>
      </div>

      {/* ── SVG Pipeline Canvas ───────────────────────────────────────────── */}
      <div className="glass-panel" style={{ flex: 1, padding: '0.85rem', position: 'relative',
        display: 'flex', flexDirection: 'column', gap: '0.75rem', minHeight: 0 }}>

        {/* Selected flow info bar */}
        {selectedFlow && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexShrink: 0,
            background: 'rgba(7,14,28,0.9)', border: '1px solid var(--border-bright)',
            borderRadius: 8, padding: '0.35rem 0.85rem', fontSize: '0.78rem' }}>
            <span style={{ fontWeight: 800, color: METHOD_COLORS[selectedFlow.method] ?? '#a78bfa' }}>
              {selectedFlow.method}
            </span>
            <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#f8fafc' }}>
              {selectedFlow.target ?? selectedFlow.path}
            </span>
            {selectedFlow.status_code && (
              <span style={{ fontWeight: 800, color: statusColor(selectedFlow.status_code) }}>
                {selectedFlow.status_code}
              </span>
            )}
            {selectedFlow.latency_ms !== undefined && (
              <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontSize: '0.72rem' }}>
                ⏱ {selectedFlow.latency_ms.toFixed(2)} ms
              </span>
            )}
            <button
              onClick={() => {
                const stagesToReveal = STAGE_ORDER.filter(s =>
                  (selectedFlow.stagesCompleted as string[]).includes(s)
                );
                startAnimation(stagesToReveal);
              }}
              title="Replay packet trace animation through pipeline"
              style={{
                background: 'rgba(14,165,233,0.12)',
                border: '1px solid rgba(14,165,233,0.4)',
                borderRadius: 5,
                color: '#38bdf8',
                fontSize: '0.68rem',
                fontWeight: 600,
                padding: '0.2rem 0.55rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                transition: 'all 0.15s ease',
              }}
            >
              <span style={{ fontSize: '0.75rem' }}>↻</span> Replay Trace
            </button>

            {/* Speed Selector */}
            <div style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(15,23,42,0.6)',
              borderRadius: 5, border: '1px solid var(--border-dim)', padding: '2px', gap: '2px', marginLeft: '0.2rem' }}>
              <span style={{ fontSize: '0.64rem', color: 'var(--text-dim)', padding: '0 0.3rem', fontWeight: 600 }}>Speed:</span>
              {[
                { label: '0.5x Slow', ms: 500 },
                { label: '1x Normal', ms: 360 },
                { label: '2x Fast', ms: 160 },
              ].map(({ label, ms }) => (
                <button
                  key={ms}
                  onClick={() => setSpeedMs(ms)}
                  title={`${ms}ms per stage`}
                  style={{
                    background: speedMs === ms ? 'rgba(14,165,233,0.3)' : 'transparent',
                    border: 'none',
                    borderRadius: 3,
                    color: speedMs === ms ? '#38bdf8' : 'var(--text-dim)',
                    fontSize: '0.64rem',
                    fontWeight: speedMs === ms ? 800 : 500,
                    padding: '0.1rem 0.35rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <span style={{ marginLeft: 'auto', color: 'var(--text-dim)', fontSize: '0.66rem',
              fontFamily: 'monospace' }}>
              {selectedFlow.request_id}
            </span>
          </div>
        )}

        {/* The SVG — responsive via viewBox */}
        <div style={{ flex: 1, minHeight: 220, display: 'flex', alignItems: 'center', overflow: 'hidden' }}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="xMidYMid meet"
            style={{ width: '100%', height: '100%', minHeight: 220, maxHeight: 300 }}
          >
            <defs>
              {/* Arrow markers */}
              <marker id="m-dim"  viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0 0 L8 4 L0 8z" fill="#1e293b"/>
              </marker>
              <marker id="m-lit"  viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0 0 L8 4 L0 8z" fill="#0ea5e9"/>
              </marker>
              <marker id="m-done" viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0 0 L8 4 L0 8z" fill="#10b981"/>
              </marker>
              <marker id="m-err"  viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0 0 L8 4 L0 8z" fill="#dc2626"/>
              </marker>

              {/* Glow filters */}
              <filter id="glow-blue" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="3.5" result="b"/>
                <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <filter id="glow-green" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="3" result="b"/>
                <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <filter id="glow-red" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="4" result="b"/>
                <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>

              {/* Step-dash animation keyframe via CSS */}
              <style>{`
                @keyframes dashFlow {
                  from { stroke-dashoffset: 20; }
                  to   { stroke-dashoffset: 0; }
                }
                @keyframes pulseDot {
                  0%, 100% { opacity: 1; r: 5; }
                  50%       { opacity: 0.4; r: 7; }
                }
              `}</style>
            </defs>

            {/* ── Step labels ─────────────────────────────────────────────── */}
            <text x="400" y="14" textAnchor="middle" fill="#1e293b"
              fontSize="11" fontFamily="system-ui" fontWeight="700" letterSpacing="0.05em">
              REQUEST PATH
            </text>
            <text x="520" y={H - 8} textAnchor="middle" fill="#1e293b"
              fontSize="11" fontFamily="system-ui" fontWeight="700" letterSpacing="0.05em">
              RESPONSE PATH
            </text>

            {/* ── Edges ───────────────────────────────────────────────────── */}
            {LINKS.map(([fid, tid]) => {
              const fn = NODES.find(n => n.id === fid)!;
              const tn = NODES.find(n => n.id === tid)!;
              const d    = buildEdge(fn, tn);
              const lit  = edgeAnimated(fid, tid);
              const ec   = edgeColor(fid, tid);
              const err  = ec === '#dc2626';
              const done = ec === '#10b981';

              return (
                <path key={`${fid}-${tid}`}
                  d={d}
                  fill="none"
                  stroke={ec}
                  strokeWidth={lit || err || done ? 2 : 1.2}
                  strokeDasharray={lit ? '8 4' : undefined}
                  markerEnd={err ? 'url(#m-err)' : lit ? 'url(#m-lit)' : done ? 'url(#m-done)' : 'url(#m-dim)'}
                  style={lit ? { animation: 'dashFlow 0.6s linear infinite' } : undefined}
                />
              );
            })}

            {/* ── Nodes ───────────────────────────────────────────────────── */}
            {NODES.map((node, i) => {
              const state = getNodeState(node.id);
              const c     = COLORS[state];
              const rx    = node.x - NODE_W / 2;
              const ry    = node.y - NODE_H / 2;
              const timing = selectedFlow?.stageTimings?.[node.id];
              const glowId = state === 'active' ? 'url(#glow-blue)'
                           : state === 'completed' ? 'url(#glow-green)'
                           : state === 'error' ? 'url(#glow-red)'
                           : undefined;

              return (
                <g key={node.id} filter={glowId}>
                  {/* Card */}
                  <rect
                    x={rx} y={ry} width={NODE_W} height={NODE_H} rx={9}
                    fill={c.fill}
                    stroke={c.stroke}
                    strokeWidth={state === 'active' || state === 'error' ? 2 : 1.2}
                  />

                  {/* Step badge */}
                  <rect x={rx + 6} y={ry + 5} width={16} height={13} rx={3}
                    fill={c.stroke} opacity={0.6}/>
                  <text x={rx + 14} y={ry + 15} textAnchor="middle"
                    fill={c.text} fontSize="8" fontWeight="800" fontFamily="monospace">
                    {i + 1}
                  </text>

                  {/* Status dot */}
                  <circle cx={rx + NODE_W - 10} cy={ry + 10} r="5" fill={c.dot}
                    style={state === 'active' ? { animation: 'pulseDot 1s ease-in-out infinite' } : undefined}
                  />

                  {/* Label */}
                  <text x={node.x} y={node.y - 6} textAnchor="middle"
                    fill={c.text} fontSize="12" fontWeight="700"
                    fontFamily="system-ui, sans-serif">
                    {node.label}
                  </text>

                  {/* Sublabel */}
                  <text x={node.x} y={node.y + 10} textAnchor="middle"
                    fill="#475569" fontSize="8.5" fontFamily="'Courier New', monospace">
                    {node.sub}
                  </text>

                  {/* Timing badge (shown when available) */}
                  {timing !== undefined && (
                    <text x={node.x} y={node.y + 23} textAnchor="middle"
                      fill="#0ea5e9" fontSize="8" fontWeight="700" fontFamily="monospace">
                      {timing.toFixed(2)}ms
                    </text>
                  )}
                </g>
              );
            })}

            {/* ── U-bend connector line (visual only) ─────────────────────── */}
            {/* Right-side vertical line from route down to handler */}
            {/* already drawn by the route→handler edge */}
          </svg>
        </div>

        {/* ── Legend ───────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', flexShrink: 0,
          fontSize: '0.72rem', color: 'var(--text-dim)', alignItems: 'center' }}>
          {([
            { color: '#10b981', label: 'Completed' },
            { color: '#0ea5e9', label: 'Active (animated)' },
            { color: '#ef4444', label: 'Error / Rejected' },
            { color: '#1e293b', label: 'Pending' },
          ] as const).map(({ color, label }) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: 9, height: 9, borderRadius: '50%',
                background: color, display: 'inline-block', flexShrink: 0 }} />
              {label}
            </span>
          ))}
          <span style={{ marginLeft: 'auto', fontStyle: 'italic', color: 'var(--text-dim)' }}>
            Driven by live SSE from Python socket loop
          </span>
        </div>
      </div>
    </div>
  );
};
