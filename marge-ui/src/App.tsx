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
import LabelManager from './LabelManager'
import NotificationCenter from './NotificationCenter'
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

interface AreaInfo {
  area_id: string;
  name: string;
  entities: string[];
}

type GroupMode = 'domain' | 'area';

function groupByArea(entities: EntityState[], areas: AreaInfo[]): Map<string, EntityState[]> {
  const areaMap = new Map<string, Set<string>>();
  const areaNames = new Map<string, string>();
  for (const area of areas) {
    areaMap.set(area.area_id, new Set(area.entities));
    areaNames.set(area.area_id, area.name);
  }

  const groups = new Map<string, EntityState[]>();
  const unassigned: EntityState[] = [];

  for (const e of entities) {
    let found = false;
    for (const [areaId, entitySet] of areaMap) {
      if (entitySet.has(e.entity_id)) {
        const name = areaNames.get(areaId) || areaId;
        if (!groups.has(name)) groups.set(name, []);
        groups.get(name)!.push(e);
        found = true;
        break;
      }
    }
    if (!found) unassigned.push(e);
  }

  // Sort within groups
  for (const [, list] of groups) {
    list.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
  }

  // Sorted groups + unassigned at end
  const sorted = new Map([...groups.entries()].sort((a, b) => a[0].localeCompare(b[0])));
  if (unassigned.length > 0) {
    unassigned.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
    sorted.set('Unassigned', unassigned);
  }
  return sorted;
}

type TabName = 'entities' | 'automations' | 'areas' | 'devices' | 'labels' | 'logs' | 'settings';

const VALID_TABS: TabName[] = ['entities', 'automations', 'areas', 'devices', 'labels', 'logs', 'settings'];

function readUrlParams(): { tab: TabName; q: string; domain: string | null } {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') as TabName;
  return {
    tab: VALID_TABS.includes(tab) ? tab : 'entities',
    q: params.get('q') || '',
    domain: params.get('domain') || null,
  };
}

function App() {
  const initial = readUrlParams();
  const [entities, setEntities] = useState<EntityState[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [filter, setFilter] = useState(initial.q);
  const [domainFilter, setDomainFilter] = useState<string | null>(initial.domain);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>('disconnected');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('marge_theme') as 'dark' | 'light') || 'dark'
  );
  const [activeTab, setActiveTab] = useState<TabName>(initial.tab);
  const [groupMode, setGroupMode] = useState<GroupMode>('domain');
  const [areas, setAreas] = useState<AreaInfo[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  const filterRef = useRef<HTMLInputElement>(null);

  // Sync state to URL params
  useEffect(() => {
    const params = new URLSearchParams();
    if (activeTab !== 'entities') params.set('tab', activeTab);
    if (filter) params.set('q', filter);
    if (domainFilter) params.set('domain', domainFilter);
    const search = params.toString();
    const url = search ? `?${search}` : window.location.pathname;
    window.history.replaceState(null, '', url);
  }, [activeTab, filter, domainFilter]);

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

  // Fetch areas for area grouping
  useEffect(() => {
    const fetchAreas = () => {
      fetch('/api/areas')
        .then((r) => r.json())
        .then(setAreas)
        .catch(() => setAreas([]));
    };
    fetchAreas();
    const id = setInterval(fetchAreas, 10000);
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
      if (e.key === '?') {
        setShowHelp((v) => !v);
        return;
      }
      if (e.key === 'Escape') {
        if (showHelp) {
          setShowHelp(false);
        } else if (selectedEntity) {
          setSelectedEntity(null);
        } else if (filter || domainFilter) {
          setFilter('');
          setDomainFilter(null);
          filterRef.current?.blur();
        }
      }
      // Tab switching: 1-7
      if (e.key === '1') setActiveTab('entities');
      if (e.key === '2') setActiveTab('automations');
      if (e.key === '3') setActiveTab('areas');
      if (e.key === '4') setActiveTab('devices');
      if (e.key === '5') setActiveTab('labels');
      if (e.key === '6') setActiveTab('logs');
      if (e.key === '7') setActiveTab('settings');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedEntity, filter, domainFilter, showHelp]);

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

  // Summary stats for quick status strip
  const summary = useMemo(() => {
    const lights = entities.filter((e) => getDomain(e.entity_id) === 'light');
    const lightsOn = lights.filter((e) => e.state === 'on').length;
    const locks = entities.filter((e) => getDomain(e.entity_id) === 'lock');
    const locksLocked = locks.filter((e) => e.state === 'locked').length;
    const climate = entities.find((e) => getDomain(e.entity_id) === 'climate');
    const alarm = entities.find((e) => getDomain(e.entity_id) === 'alarm_control_panel');
    const sensors = entities.filter((e) => getDomain(e.entity_id) === 'sensor');
    const numericSensors = sensors.filter((e) => !isNaN(Number(e.state)));

    return { lights, lightsOn, locks, locksLocked, climate, alarm, numericSensors };
  }, [entities]);

  const filteredList = filtered();
  const groups = groupMode === 'area'
    ? groupByArea(filteredList, areas)
    : groupByDomain(filteredList);

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
        <NotificationCenter />
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
          {(domainCounts.get('automation') ?? 0) > 0 && (
            <span className="tab-badge">{domainCounts.get('automation')}</span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'areas' ? 'active' : ''}`}
          onClick={() => setActiveTab('areas')}
        >
          Areas
          {areas.length > 0 && <span className="tab-badge">{areas.length}</span>}
        </button>
        <button
          className={`tab-btn ${activeTab === 'devices' ? 'active' : ''}`}
          onClick={() => setActiveTab('devices')}
        >
          Devices
        </button>
        <button
          className={`tab-btn ${activeTab === 'labels' ? 'active' : ''}`}
          onClick={() => setActiveTab('labels')}
        >
          Labels
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
          {entities.length > 0 && (
            <div className="summary-strip">
              {summary.lights.length > 0 && (
                <div className="summary-card">
                  <span className="summary-value">{summary.lightsOn}/{summary.lights.length}</span>
                  <span className="summary-label">Lights On</span>
                </div>
              )}
              {summary.locks.length > 0 && (
                <div className="summary-card">
                  <span className="summary-value">{summary.locksLocked}/{summary.locks.length}</span>
                  <span className="summary-label">Locked</span>
                </div>
              )}
              {summary.climate && (
                <div className="summary-card">
                  <span className="summary-value">
                    {String(summary.climate.attributes.current_temperature ?? summary.climate.state)}
                  </span>
                  <span className="summary-label">Climate</span>
                </div>
              )}
              {summary.alarm && (
                <div className={`summary-card ${summary.alarm.state !== 'disarmed' ? 'summary-alert' : ''}`}>
                  <span className="summary-value">{summary.alarm.state.replace(/_/g, ' ')}</span>
                  <span className="summary-label">Alarm</span>
                </div>
              )}
              {summary.numericSensors.slice(0, 3).map((s) => (
                <div key={s.entity_id} className="summary-card">
                  <span className="summary-value">
                    {Number(s.state).toFixed(1)}
                    {s.attributes.unit_of_measurement ? ` ${s.attributes.unit_of_measurement}` : ''}
                  </span>
                  <span className="summary-label">
                    {(s.attributes.friendly_name as string) || s.entity_id.split('.')[1]?.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="entity-toolbar">
            <DomainChips
              domains={domainCounts}
              active={domainFilter}
              onToggle={setDomainFilter}
            />
            <div className="group-toggle">
              <button
                className={`chip ${groupMode === 'domain' ? 'active' : ''}`}
                onClick={() => setGroupMode('domain')}
              >
                By Domain
              </button>
              <button
                className={`chip ${groupMode === 'area' ? 'active' : ''}`}
                onClick={() => setGroupMode('area')}
              >
                By Area
              </button>
            </div>
          </div>

          <main className="entity-groups">
            {[...groups.entries()].map(([domain, domainEntities]) => (
              <section key={domain} className="domain-group">
                <h2 className="domain-title">
                  {domain.replace(/_/g, ' ')}
                  <span className="domain-count">{domainEntities.length}</span>
                </h2>
                <div className="entity-grid">
                  {domainEntities.map((entity) => (
                    <div key={entity.entity_id} className="entity-grid-item">
                      <EntityCard entity={entity} />
                      <button
                        className="card-expand-btn"
                        onClick={() => setSelectedEntity(entity.entity_id)}
                        title="Details"
                      >
                        &#x2197;
                      </button>
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
        <AreaManager allEntityIds={entities.map((e) => e.entity_id)} />
      )}

      {activeTab === 'devices' && (
        <DeviceManager allEntityIds={entities.map((e) => e.entity_id)} />
      )}

      {activeTab === 'labels' && (
        <LabelManager allEntityIds={entities.map((e) => e.entity_id)} />
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

      {showHelp && (
        <div className="help-overlay" onClick={() => setShowHelp(false)}>
          <div className="help-panel" onClick={(e) => e.stopPropagation()}>
            <div className="help-header">
              <h3>Keyboard Shortcuts</h3>
              <button className="detail-close" onClick={() => setShowHelp(false)}>X</button>
            </div>
            <div className="help-grid">
              <div className="help-section">
                <h4>Navigation</h4>
                <div className="help-row"><kbd>1</kbd><span>Entities</span></div>
                <div className="help-row"><kbd>2</kbd><span>Automations</span></div>
                <div className="help-row"><kbd>3</kbd><span>Areas</span></div>
                <div className="help-row"><kbd>4</kbd><span>Devices</span></div>
                <div className="help-row"><kbd>5</kbd><span>Labels</span></div>
                <div className="help-row"><kbd>6</kbd><span>Logs</span></div>
                <div className="help-row"><kbd>7</kbd><span>Settings</span></div>
              </div>
              <div className="help-section">
                <h4>Actions</h4>
                <div className="help-row"><kbd>/</kbd><span>Focus search</span></div>
                <div className="help-row"><kbd>f</kbd><span>Focus search</span></div>
                <div className="help-row"><kbd>?</kbd><span>Toggle help</span></div>
                <div className="help-row"><kbd>Esc</kbd><span>Close / Clear</span></div>
              </div>
              <div className="help-section">
                <h4>Entity Cards</h4>
                <div className="help-row"><span className="help-hint">Click</span><span>Toggle lights, switches, locks</span></div>
                <div className="help-row"><span className="help-hint">Double-click</span><span>Open detail panel</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      <ToastContainer />
    </div>
  );
}

export default App
