export interface EntityState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed: string;
  last_updated: string;
}

export interface StateChangedEvent {
  event_type: 'state_changed';
  data: {
    entity_id: string;
    old_state: EntityState | null;
    new_state: EntityState;
  };
  time_fired: string;
}

export interface HealthData {
  status: string;
  version: string;
  entity_count: number;
  memory_rss_mb: number;
  uptime_seconds: number;
  startup_ms: number;
  state_changes: number;
  latency_avg_us: number;
  latency_max_us: number;
  sim_time: string;
  sim_chapter: string;
}

export type Domain =
  | 'light'
  | 'switch'
  | 'sensor'
  | 'binary_sensor'
  | 'climate'
  | 'cover'
  | 'lock'
  | 'fan'
  | 'alarm_control_panel'
  | 'automation'
  | 'scene'
  | 'input_boolean'
  | 'input_number'
  | 'input_select'
  | 'input_text'
  | string;

export function getDomain(entityId: string): Domain {
  return entityId.split('.')[0] || 'unknown';
}

export function getEntityName(entityId: string): string {
  const name = entityId.split('.')[1] || entityId;
  return name.replace(/_/g, ' ');
}
