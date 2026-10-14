import { useState, useEffect, useRef, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { PipelineVisualizer } from './components/PipelineVisualizer';
import { RequestTestingPanel } from './components/RequestTestingPanel';
import { RequestInspector } from './components/RequestInspector';
import { MetricsDashboard } from './components/MetricsDashboard';
import { LiveEventStream } from './components/LiveEventStream';
import { ProtocolGuideModal } from './components/ProtocolGuideModal';
import type { MetricsSnapshot, PipelineStage, RequestFlow, ServerEvent } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('topology');
  const [sseStatus, setSseStatus] = useState<'connected' | 'reconnecting' | 'disconnected'>('disconnected');
  const [events, setEvents] = useState<ServerEvent[]>([]);
  const [recentFlows, setRecentFlows] = useState<RequestFlow[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<RequestFlow | null>(null);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);

  // Use a ref for the "manually selected" flow ID so we don't auto-override it
  const manualSelectionRef = useRef<string | null>(null);

  // ─── Auto-select: keep selectedFlow in sync with recentFlows ────────────────
  // When recentFlows updates, update selectedFlow if:
  //   a) Nothing is manually selected → auto-track the latest flow
  //   b) The currently selected flow received new events → refresh it
  //   c) A BRAND NEW flow just appeared → clear manual selection and track it
  useEffect(() => {
    if (recentFlows.length === 0) return;
    const latest = recentFlows[0];

    setSelectedFlow((prev) => {
      if (!prev) {
        // Nothing selected → auto-pick latest
        manualSelectionRef.current = null;
        return latest;
      }
      // Brand-new flow (not seen before) → clear manual lock and track it
      if (prev.request_id !== latest.request_id && !recentFlows.find(f => f.request_id === prev.request_id)) {
        manualSelectionRef.current = null;
        return latest;
      }
      // If there's no manual selection, always track the latest flow
      if (!manualSelectionRef.current) {
        return latest;
      }
      // User manually selected a different flow → find and refresh it
      const found = recentFlows.find((f) => f.request_id === prev.request_id);
      return found ?? prev;
    });
  }, [recentFlows]);

  // ─── SSE event handler (stable ref, avoids stale closure) ───────────────────
  // We process ALL incoming events through this ref-stable callback so the
  // EventSource listener installed once in useEffect always has fresh logic.
  const handleIncomingEventRef = useRef<(event: ServerEvent) => void>(() => {});

  handleIncomingEventRef.current = (event: ServerEvent) => {
    // Ignore internal background telemetry (/api/metrics and SSE stream)
    const evPath = ((event.metadata?.path || event.metadata?.target) as string) ?? '';
    if (evPath === '/api/metrics' || evPath.startsWith('/api/events')) {
      return;
    }

    // 1. Append to flat event log
    setEvents((prev) => [event, ...prev].slice(0, 500));

    // 2. Only flow-bearing events carry request_id
    if (!event.request_id) return;

    // 3. Merge event into the correct RequestFlow, advancing the state machine
    setRecentFlows((prevFlows) => {
      const existingFlow = prevFlows.find((f) => f.request_id === event.request_id);
      if (existingFlow && (existingFlow.path === '/api/metrics' || existingFlow.path.startsWith('/api/events'))) {
        return prevFlows;
      }

      // Clone to avoid mutating state
      const flow: RequestFlow = existingFlow
        ? {
            ...existingFlow,
            stagesCompleted: [...existingFlow.stagesCompleted],
            stageTimings: { ...existingFlow.stageTimings },
            events: [...existingFlow.events, event],
          }
        : {
            request_id: event.request_id ?? '',
            connection_id: event.connection_id ?? '',
            method: (event.metadata?.method as string) ?? 'GET',
            path: (event.metadata?.path as string) ?? '/',
            target: ((event.metadata?.target ?? event.metadata?.path) as string) ?? '/',
            timestamp: event.timestamp,
            stagesCompleted: (['tcp_accept', 'buffer'] as PipelineStage[]),
            currentStage: ('parse' as PipelineStage),
            stageTimings: {},
            events: [event],
          };

      // Enrich metadata from event payload
      if (event.metadata?.method) flow.method = event.metadata.method;
      if (event.metadata?.path) flow.path = event.metadata.path;
      if (event.metadata?.target) flow.target = event.metadata.target;
      if (event.metadata?.status_code) flow.status_code = event.metadata.status_code;
      if (event.metadata?.latency_ms !== undefined) flow.latency_ms = event.metadata.latency_ms;
      if (event.metadata?.stage_timings) {
        flow.stageTimings = { ...flow.stageTimings, ...event.metadata.stage_timings };
      }
      if (event.metadata?.parse_duration_ms !== undefined) {
        flow.stageTimings = { ...flow.stageTimings, parse: event.metadata.parse_duration_ms };
      }

      // ── State machine: advance pipeline stage ──────────────────────────────
      const addStage = (stage: any) => {
        if (!flow.stagesCompleted.includes(stage)) {
          flow.stagesCompleted = [...flow.stagesCompleted, stage];
        }
      };

      switch (event.event_type) {
        case 'connection_opened':
          addStage('tcp_accept');
          flow.currentStage = 'buffer' as any;
          break;
        case 'request_bytes_received':
          addStage('buffer');
          flow.currentStage = 'parse' as any;
          break;
        case 'request_line_parsed':
          addStage('buffer');
          addStage('parse');
          flow.currentStage = 'validate' as any;
          break;
        case 'headers_parsed':
          addStage('parse');
          flow.currentStage = 'validate' as any;
          break;
        case 'request_validated':
          addStage('validate');
          flow.currentStage = 'route' as any;
          break;
        case 'route_matched':
          addStage('route');
          flow.currentStage = 'handler' as any;
          break;
        case 'response_created':
          addStage('handler');
          addStage('serialize');
          flow.currentStage = 'tcp_send' as any;
          break;
        case 'response_sent':
        case 'request_completed':
          addStage('tcp_send');
          flow.currentStage = 'completed' as any;
          break;
        case 'request_rejected':
        case 'parser_error':
          flow.currentStage = 'failed' as any;
          flow.error = event.message;
          break;
      }

      // Return updated flows array (latest first, max 20)
      if (!existingFlow) {
        return [flow, ...prevFlows.slice(0, 19)];
      }
      return prevFlows.map((f) => (f.request_id === flow.request_id ? flow : f));
    });
  };

  // ─── SSE connection ──────────────────────────────────────────────────────────
  useEffect(() => {
    let evtSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    // Named SSE event types emitted by the Python server
    const SSE_EVENT_TYPES = [
      'message',
      'connection_opened', 'connection_closed',
      'request_bytes_received', 'request_line_parsed', 'headers_parsed',
      'request_validated', 'route_matched',
      'response_created', 'response_sent', 'request_completed',
      'request_rejected', 'parser_error',
      'sse_connected', 'sse_disconnected',
      'server_started', 'server_stopping', 'server_stopped',
      'general',
    ];

    const dispatchSSE = (e: MessageEvent) => {
      if (!e.data || e.data.trim() === '') return;
      try {
        const rawEv: ServerEvent = JSON.parse(e.data);
        handleIncomingEventRef.current(rawEv);
      } catch {
        // ignore malformed / heartbeat
      }
    };

    const connectSSE = () => {
      setSseStatus('reconnecting');
      evtSource = new EventSource('/api/events/stream');

      evtSource.onopen = () => {
        setSseStatus('connected');
      };

      // Catch unnamed events (data-only SSE lines without 'event:' field)
      evtSource.onmessage = dispatchSSE;

      // Catch ALL named event types the Python server emits
      // (EventSource.onmessage only fires when there is NO 'event:' field)
      SSE_EVENT_TYPES.forEach((type) => {
        evtSource!.addEventListener(type, dispatchSSE as EventListener);
      });

      evtSource.onerror = () => {
        setSseStatus('disconnected');
        if (evtSource) {
          evtSource.close();
          evtSource = null;
        }
        reconnectTimeout = setTimeout(connectSSE, 2500);
      };
    };

    connectSSE();

    return () => {
      if (evtSource) evtSource.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []); // Only mount once — stable via ref

  // ─── Metrics polling ─────────────────────────────────────────────────────────
  useEffect(() => {
    const fetchMetrics = () => {
      fetch('/api/metrics', { headers: { 'X-Internal-Poll': '1' } })
        .then((res) => (res.ok ? res.json() : null))
        .then((data: MetricsSnapshot | null) => {
          if (data) setMetrics(data);
        })
        .catch(() => {});
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 1200);
    return () => clearInterval(interval);
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const handleManualSelect = useCallback((flow: RequestFlow) => {
    manualSelectionRef.current = flow.request_id;
    setSelectedFlow(flow);
  }, []);

  const handleTriggerRequest = useCallback(() => {
    // Clear lock so newly sent request gets immediate visual focus & animation
    manualSelectionRef.current = null;
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-main)', overflow: 'hidden' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sseStatus={sseStatus}
        activeConnections={metrics?.active_connections || 0}
        uptimeSeconds={metrics?.server_uptime_seconds || 0}
        totalRequests={metrics?.total_requests || 0}
      />

      <main style={{ flex: 1, padding: '1rem', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'topology' && (
          <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '1rem', height: '100%', overflow: 'hidden' }}>
            <div style={{ minHeight: 0, overflow: 'hidden' }}>
              <RequestTestingPanel onTriggerRequest={handleTriggerRequest} />
            </div>
            <div style={{ minHeight: 0, overflow: 'hidden' }}>
              <PipelineVisualizer
                selectedFlow={selectedFlow}
                recentFlows={recentFlows}
                onSelectFlow={handleManualSelect}
              />
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <MetricsDashboard metrics={metrics} />
          </div>
        )}

        {activeTab === 'inspector' && (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <RequestInspector flow={selectedFlow} />
          </div>
        )}

        {activeTab === 'events' && (
          <div style={{ height: '100%', overflow: 'hidden' }}>
            <LiveEventStream events={events} onClear={clearEvents} />
          </div>
        )}

        {activeTab === 'guide' && (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <ProtocolGuideModal />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
