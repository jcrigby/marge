import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import type { EntityState, HealthData } from './types'
import { getDomain } from './types'
import { connect, subscribe, subscribeStatus } from './ws'
import type { ConnectionStatus } from './ws'
import EntityCard from './EntityCard'
import EntityDetail from './EntityDetail'
import AutomationList from './AutomationList'
import AreaManager from './AreaManager'
import DeviceManager from './DeviceManager'
import EventLog from './EventLog'
import Settings from './Settings'
import ToastContainer from './Toast'
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

function DomainChips({
  domains,
  active,
  onToggle,
}: {
  domains: Map<string, number>;
  active: string | null;
  onToggle: (domain: string | null) => void;
}) {
  if (domains.size === 0) return null;
  return (
    <div className="domain-chips">
      <button
        className={`chip ${active === null ? 'active' : ''}`}
        onClick={() => onToggle(null)}
      >
        All
      </button>
      {[...domains.entries()].map(([domain, count]) => (
        <button
          key={domain}
          className={`chip ${active === domain ? 'active' : ''}`}
          onClick={() => onToggle(active === domain ? null : domain)}
        >
          {domain.replace(/_/g, ' ')} ({count})
        </button>
      ))}
    </div>
  );
}

function App() {
  const [entities, setEntities] = useState<EntityState[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [filter, setFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState<string | null>(null);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>('disconnected');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('marge_theme') as 'dark' | 'light') || 'dark'
  );
  const [activeTab, setActiveTab] = useState<'entities' | 'automations' | 'areas' | 'devices' | 'logs' | 'settings'>('entities');
  const filterRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : '');
    localStorage.setItem('marge_theme', theme);
  }, [theme]);

  useEffect(() => {
    connect();
    const unsubEntities = subscribe((entityMap) => {
      setEntities([...entityMap.values()]);
    });
    const unsubStatus = subscribeStatus(setConnStatus);
    return () => { unsubEntities(); unsubStatus(); };
  }, []);

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

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.key === '/' || e.key === 'f') {
        e.preventDefault();
        filterRef.current?.focus();
      }
      if (e.key === 'Escape') {
        if (selectedEntity) {
          setSelectedEntity(null);
        } else if (filter || domainFilter) {
          setFilter('');
          setDomainFilter(null);
          filterRef.current?.blur();
        }
      }
      // Tab switching: 1-6
      if (e.key === '1') setActiveTab('entities');
      if (e.key === '2') setActiveTab('automations');
      if (e.key === '3') setActiveTab('areas');
      if (e.key === '4') setActiveTab('devices');
      if (e.key === '5') setActiveTab('logs');
      if (e.key === '6') setActiveTab('settings');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedEntity, filter, domainFilter]);

  // Count entities per domain (unfiltered) for chips
  const domainCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of entities) {
      const d = getDomain(e.entity_id);
      counts.set(d, (counts.get(d) || 0) + 1);
    }
    return new Map(
      [...counts.entries()].sort((a, b) => domainSortKey(a[0]) - domainSortKey(b[0]))
    );
  }, [entities]);

  const filtered = useCallback(() => {
    let list = entities;
    if (domainFilter) {
      list = list.filter((e) => getDomain(e.entity_id) === domainFilter);
    }
    if (filter) {
      const q = filter.toLowerCase();
      list = list.filter((e) =>
        e.entity_id.toLowerCase().includes(q) ||
        e.state.toLowerCase().includes(q) ||
        ((e.attributes.friendly_name as string) || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [entities, filter, domainFilter]);

  const groups = groupByDomain(filtered());

  return (
    <div className="app">
      <header className="app-header">
        <h1>Marge</h1>
        <input
          ref={filterRef}
          className="filter-input"
          type="text"
          placeholder="Filter entities... (/ to focus)"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Escape') { setFilter(''); filterRef.current?.blur(); }}}
        />
        <button
          className="theme-toggle"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '\u{2600}' : '\u{1F319}'}
        </button>
      </header>

      <HealthBar health={health} connStatus={connStatus} />

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'entities' ? 'active' : ''}`}
          onClick={() => setActiveTab('entities')}
        >
          Entities<span className="tab-badge">{entities.length}</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'automations' ? 'active' : ''}`}
          onClick={() => setActiveTab('automations')}
        >
          Automations
        </button>
        <button
          className={`tab-btn ${activeTab === 'areas' ? 'active' : ''}`}
          onClick={() => setActiveTab('areas')}
        >
          Areas
        </button>
        <button
          className={`tab-btn ${activeTab === 'devices' ? 'active' : ''}`}
          onClick={() => setActiveTab('devices')}
        >
          Devices
        </button>
        <button
          className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          Logs
        </button>
        <button
          className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Settings
        </button>
      </nav>

      {activeTab === 'entities' && (
        <>
          <DomainChips
            domains={domainCounts}
            active={domainFilter}
            onToggle={setDomainFilter}
          />

          <main className="entity-groups">
            {[...groups.entries()].map(([domain, domainEntities]) => (
              <section key={domain} className="domain-group">
                <h2 className="domain-title">
                  {domain.replace(/_/g, ' ')}
                  <span className="domain-count">{domainEntities.length}</span>
                </h2>
                <div className="entity-grid">
                  {domainEntities.map((entity) => (
                    <div key={entity.entity_id} onDoubleClick={() => setSelectedEntity(entity.entity_id)}>
                      <EntityCard entity={entity} />
                    </div>
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
        </>
      )}

      {activeTab === 'automations' && (
        <AutomationList />
      )}

      {activeTab === 'areas' && (
        <AreaManager />
      )}

      {activeTab === 'devices' && (
        <DeviceManager allEntityIds={entities.map((e) => e.entity_id)} />
      )}

      {activeTab === 'logs' && (
        <EventLog entities={entities} />
      )}

      {activeTab === 'settings' && (
        <Settings health={health} />
      )}

      {selectedEntity && (() => {
        const entity = entities.find((e) => e.entity_id === selectedEntity);
        return entity ? (
          <EntityDetail entity={entity} onClose={() => setSelectedEntity(null)} />
        ) : null;
      })()}

      <ToastContainer />
    </div>
  );
}

export default App
