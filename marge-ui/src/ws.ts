import type { EntityState, StateChangedEvent } from './types';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';
type Listener = (entities: Map<string, EntityState>) => void;
type StatusListener = (status: ConnectionStatus) => void;

let ws: WebSocket | null = null;
let msgId = 1;
const entities = new Map<string, EntityState>();
const listeners = new Set<Listener>();
const statusListeners = new Set<StatusListener>();
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
let status: ConnectionStatus = 'disconnected';

const MAX_RECONNECT_DELAY = 30000;

function getWsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}/api/websocket`;
}

function getToken(): string {
  return localStorage.getItem('marge_token') || '';
}

export function setToken(token: string): void {
  localStorage.setItem('marge_token', token);
}

function setStatus(s: ConnectionStatus): void {
  status = s;
  for (const fn of statusListeners) fn(s);
}

export function connect(): void {
  if (ws && ws.readyState <= WebSocket.OPEN) return;

  setStatus('connecting');
  ws = new WebSocket(getWsUrl());

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    switch (msg.type) {
      case 'auth_required':
        ws!.send(JSON.stringify({ type: 'auth', access_token: getToken() }));
        break;

      case 'auth_ok':
        setStatus('connected');
        reconnectDelay = 1000; // Reset backoff on success
        // Subscribe to state_changed events
        ws!.send(JSON.stringify({ id: msgId++, type: 'subscribe_events', event_type: 'state_changed' }));
        // Fetch all current states
        ws!.send(JSON.stringify({ id: msgId++, type: 'get_states' }));
        break;

      case 'auth_invalid':
        console.warn('Auth failed:', msg.message);
        ws!.close();
        break;

      case 'result':
        if (msg.success && Array.isArray(msg.result)) {
          // Response to get_states
          entities.clear();
          for (const e of msg.result as EntityState[]) {
            entities.set(e.entity_id, e);
          }
          notify();
        }
        break;

      case 'event': {
        const data = msg.event as StateChangedEvent;
        if (data.event_type === 'state_changed' && data.data.new_state) {
          entities.set(data.data.entity_id, data.data.new_state);
          notify();
        }
        break;
      }
    }
  };

  ws.onclose = () => {
    ws = null;
    setStatus('disconnected');
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws?.close();
  };
}

function scheduleReconnect(): void {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, reconnectDelay);
  // Exponential backoff: 1s, 2s, 4s, 8s, ... max 30s
  reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
}

function notify(): void {
  for (const fn of listeners) {
    fn(entities);
  }
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  // Immediately deliver current state
  if (entities.size > 0) fn(entities);
  return () => listeners.delete(fn);
}

export function subscribeStatus(fn: StatusListener): () => void {
  statusListeners.add(fn);
  fn(status); // Deliver current status immediately
  return () => statusListeners.delete(fn);
}

export function callService(domain: string, service: string, entityId: string, data?: Record<string, unknown>): void {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  fetch(`/api/services/${domain}/${service}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ entity_id: entityId, ...data }),
  }).catch(console.error);
}
