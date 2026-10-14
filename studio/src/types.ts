export interface ServerEvent {
  event_id: string;
  timestamp: number;
  event_type: string;
  stage: string;
  message: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  request_id?: string;
  connection_id?: string;
  metadata?: Record<string, any>;
}

export interface MetricsSnapshot {
  server_uptime_seconds: number;
  total_requests: number;
  requests_per_second: number;
  active_connections: number;
  peak_connections: number;
  total_connections: number;
  total_bytes_read: number;
  total_bytes_written: number;
  status_categories: {
    '2xx': number;
    '3xx': number;
    '4xx': number;
    '5xx': number;
  };
  status_counts: Record<string, number>;
  latency_ms: {
    avg: number;
    min: number;
    max: number;
    p50: number;
    p95: number;
    p99: number;
  };
  stage_timings_ms: Record<string, number>;
}

export type PipelineStage =
  | 'tcp_accept'
  | 'buffer'
  | 'parse'
  | 'validate'
  | 'route'
  | 'handler'
  | 'serialize'
  | 'tcp_send';

export interface RequestFlow {
  request_id: string;
  connection_id: string;
  method: string;
  path: string;
  target: string;
  timestamp: number;
  stagesCompleted: PipelineStage[];
  currentStage: PipelineStage | 'completed' | 'failed';
  status_code?: number;
  latency_ms?: number;
  error?: string;
  stageTimings: Partial<Record<PipelineStage, number>>;
  events: ServerEvent[];
}
