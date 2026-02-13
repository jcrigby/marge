import { useEffect, useState, useCallback } from 'react'
import type { EntityState, HealthData } from './types'
import { getDomain } from './types'
import { connect, subscribe, subscribeStatus } from './ws'
import type { ConnectionStatus } from './ws'
import EntityCard from './EntityCard'
import './App.css'

// Domain display order — most interactive first
const DOMAIN_ORDER = [
  'light', 'switch', 'lock', 'cover', 'climate', 'fan',
  'sensor', 'binary_sensor',
  'alarm_control_panel',
  'automation', 'scene',
  'input_boolean', 'input_number', 'input_select', 'input_text',
];

function domainSortKey(domain: string): number {
  const idx = DOMAIN_ORDER.indexOf(domain);
  return idx >= 0 ? idx : DOMAIN_ORDER.length;
}

function groupByDomain(entities: EntityState[]): Map<string, EntityState[]> {
  const groups = new Map<string, EntityState[]>();
  for (const e of entities) {
    const domain = getDomain(e.entity_id);
    if (!groups.has(domain)) groups.set(domain, []);
    groups.get(domain)!.push(e);
  }
  // Sort entries within each group
  for (const [, list] of groups) {
    list.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
  }
  return new Map(
    [...groups.entries()].sort((a, b) => domainSortKey(a[0]) - domainSortKey(b[0]))
  );
}

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  connected: 'Connected',
  connecting: 'Connecting...',
  disconnected: 'Disconnected',
};

function ConnectionDot({ status }: { status: ConnectionStatus }) {
  return (
    <span className={`conn-dot conn-${status}`} title={STATUS_LABELS[status]}>
      <span className="conn-indicator" />
      <span className="conn-label">{STATUS_LABELS[status]}</span>
    </span>
  );
}

function HealthBar({ health, connStatus }: { health: HealthData | null; connStatus: ConnectionStatus }) {
  if (!health) return (
    <div className="health-bar">
      <ConnectionDot status={connStatus} />
      <span className="health-item">Connecting...</span>
    </div>
  );
  return (
    <div className="health-bar">
      <ConnectionDot status={connStatus} />
      <span className="health-item">
        <strong>Marge</strong> v{health.version}
      </span>
      <span className="health-item">{health.entity_count} entities</span>
      <span className="health-item">{health.memory_rss_mb.toFixed(1)} MB</span>
      <span className="health-item">{health.startup_ms} ms startup</span>
      <span className="health-item">{health.latency_avg_us} us avg</span>
      <span className="health-item">{health.state_changes} changes</span>
      {health.sim_time && (
        <span className="health-item sim-time">{health.sim_time}</span>
      )}
    </div>
  );
}

function App() {
  const [entities, setEntities] = useState<EntityState[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [filter, setFilter] = useState('');
  const [connStatus, setConnStatus] = useState<ConnectionStatus>('disconnected');

  // Connect WebSocket on mount
  useEffect(() => {
    connect();
    const unsubEntities = subscribe((entityMap) => {
      setEntities([...entityMap.values()]);
    });
    const unsubStatus = subscribeStatus(setConnStatus);
    return () => { unsubEntities(); unsubStatus(); };
  }, []);

  // Poll health endpoint
  useEffect(() => {
    const fetchHealth = () => {
      fetch('/api/health')
        .then((r) => r.json())
        .then(setHealth)
        .catch(() => setHealth(null));
    };
    fetchHealth();
    const id = setInterval(fetchHealth, 5000);
    return () => clearInterval(id);
  }, []);

  const filtered = useCallback(() => {
    if (!filter) return entities;
    const q = filter.toLowerCase();
    return entities.filter((e) =>
      e.entity_id.toLowerCase().includes(q) ||
      e.state.toLowerCase().includes(q)
    );
  }, [entities, filter]);

  const groups = groupByDomain(filtered());

  return (
    <div className="app">
      <header className="app-header">
        <h1>Marge</h1>
        <input
          className="filter-input"
          type="text"
          placeholder="Filter entities..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </header>

      <HealthBar health={health} connStatus={connStatus} />

      <main className="entity-groups">
        {[...groups.entries()].map(([domain, domainEntities]) => (
          <section key={domain} className="domain-group">
            <h2 className="domain-title">{domain.replace(/_/g, ' ')}</h2>
            <div className="entity-grid">
              {domainEntities.map((entity) => (
                <EntityCard key={entity.entity_id} entity={entity} />
              ))}
            </div>
          </section>
        ))}
        {groups.size === 0 && (
          <div className="empty-state">
            {entities.length === 0
              ? 'Waiting for entities...'
              : 'No matching entities'}
          </div>
        )}
      </main>
    </div>
  );
}

export default App
