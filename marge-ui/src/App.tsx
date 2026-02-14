import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import type { EntityState, HealthData } from './types'
import { getDomain } from './types'
import { connect, subscribe, subscribeStatus } from './ws'
import type { ConnectionStatus } from './ws'
import EntityCard from './EntityCard'
import Sparkline from './Sparkline'
import EntityDetail from './EntityDetail'
import AutomationList from './AutomationList'
import AreaManager from './AreaManager'
import DeviceManager from './DeviceManager'
import EventLog from './EventLog'
import IntegrationManager from './IntegrationManager'
import LabelManager from './LabelManager'
import NotificationCenter from './NotificationCenter'
import Settings from './Settings'
import LoginPage from './LoginPage'
import ToastContainer from './Toast'
import './App.css'

// Domain display order — most interactive first
const DOMAIN_ORDER = [
  'light', 'switch', 'lock', 'cover', 'climate', 'fan',
  'media_player', 'vacuum', 'siren', 'valve',
  'sensor', 'binary_sensor',
  'alarm_control_panel', 'camera', 'weather',
  'automation', 'scene', 'script',
  'timer', 'counter',
  'number', 'select', 'button',
  'input_boolean', 'input_number', 'input_select', 'input_text', 'input_datetime',
  'person', 'zone', 'device_tracker', 'group', 'update',
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

function HealthBar({ health, connStatus, domainCounts }: { health: HealthData | null; connStatus: ConnectionStatus; domainCounts: Map<string, number> }) {
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
      <span className="health-item" title={[...domainCounts.entries()].map(([d, c]) => `${d}: ${c}`).join(', ')}>{health.entity_count} entities</span>
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

interface LabelInfo {
  label_id: string;
  name: string;
  color: string;
  entities: string[];
}

type GroupMode = 'domain' | 'area' | 'label';
type SortMode = 'name' | 'state' | 'last_changed';

function sortEntities(list: EntityState[], sort: SortMode): EntityState[] {
  const sorted = [...list];
  switch (sort) {
    case 'state':
      sorted.sort((a, b) => a.state.localeCompare(b.state) || a.entity_id.localeCompare(b.entity_id));
      break;
    case 'last_changed':
      sorted.sort((a, b) => (b.last_changed || '').localeCompare(a.last_changed || '') || a.entity_id.localeCompare(b.entity_id));
      break;
    default: // name
      sorted.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
  }
  return sorted;
}

function groupByLabel(entities: EntityState[], labels: LabelInfo[]): Map<string, EntityState[]> {
  const labelMap = new Map<string, Set<string>>();
  const labelNames = new Map<string, string>();
  for (const label of labels) {
    labelMap.set(label.label_id, new Set(label.entities));
    labelNames.set(label.label_id, label.name);
  }

  const groups = new Map<string, EntityState[]>();
  const unassigned: EntityState[] = [];

  for (const e of entities) {
    let found = false;
    for (const [labelId, entitySet] of labelMap) {
      if (entitySet.has(e.entity_id)) {
        const name = labelNames.get(labelId) || labelId;
        if (!groups.has(name)) groups.set(name, []);
        groups.get(name)!.push(e);
        found = true;
        // Don't break — entity can be in multiple labels
      }
    }
    if (!found) unassigned.push(e);
  }

  for (const [, list] of groups) {
    list.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
  }

  const sorted = new Map([...groups.entries()].sort((a, b) => a[0].localeCompare(b[0])));
  if (unassigned.length > 0) {
    unassigned.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
    sorted.set('Unassigned', unassigned);
  }
  return sorted;
}

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

type TabName = 'entities' | 'automations' | 'areas' | 'devices' | 'labels' | 'integrations' | 'logs' | 'settings';

const VALID_TABS: TabName[] = ['entities', 'automations', 'areas', 'devices', 'labels', 'integrations', 'logs', 'settings'];

function readUrlParams(): { tab: TabName; q: string; domain: string | null } {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') as TabName;
  return {
    tab: VALID_TABS.includes(tab) ? tab : 'entities',
    q: params.get('q') || '',
    domain: params.get('domain') || null,
  };
}

function ConfirmDialog({ message, onConfirm, onCancel }: {
  message: string; onConfirm: () => void; onCancel: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
      if (e.key === 'Enter') onConfirm();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onConfirm, onCancel]);

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-panel" onClick={(e) => e.stopPropagation()}>
        <p>{message}</p>
        <div className="confirm-actions">
          <button className="confirm-btn confirm-btn-danger" onClick={onConfirm}>Delete</button>
          <button className="confirm-btn" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

function QuickActions({ entities }: { entities: EntityState[] }) {
  const [open, setOpen] = useState(false);
  const qaRef = useRef<HTMLDivElement>(null);
  const scenes = entities.filter((e) => getDomain(e.entity_id) === 'scene');
  const automations = entities.filter((e) => getDomain(e.entity_id) === 'automation');

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (qaRef.current && !qaRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (scenes.length === 0 && automations.length === 0) return null;

  const activate = (e: EntityState) => {
    const domain = getDomain(e.entity_id);
    if (domain === 'scene') {
      import('./ws').then((ws) => ws.callService('scene', 'turn_on', e.entity_id));
    } else {
      import('./ws').then((ws) => ws.callService('automation', 'trigger', e.entity_id));
    }
  };

  return (
    <div className="notif-center" ref={qaRef}>
      <button className="theme-toggle" onClick={() => setOpen(!open)} title="Quick actions">
        {'\u26A1'}
      </button>
      {open && (
        <div className="notif-dropdown quick-actions-dropdown" onClick={(e) => e.stopPropagation()}>
          <div className="notif-header">
            <span className="notif-title">Quick Actions</span>
            <button className="notif-dismiss" onClick={() => setOpen(false)}>&times;</button>
          </div>
          <div className="quick-actions-list">
            {scenes.length > 0 && (
              <div className="quick-actions-group">
                <div className="quick-actions-group-title">Scenes</div>
                {scenes.map((s) => (
                  <button key={s.entity_id} className="quick-action-btn" onClick={() => activate(s)}>
                    {(s.attributes.friendly_name as string) || s.entity_id.split('.')[1]?.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            )}
            {automations.length > 0 && (
              <div className="quick-actions-group">
                <div className="quick-actions-group-title">Automations</div>
                {automations.map((a) => (
                  <button key={a.entity_id} className="quick-action-btn" onClick={() => activate(a)}>
                    {(a.attributes.friendly_name as string) || a.entity_id.split('.')[1]?.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const initial = readUrlParams();
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem('marge_token'));
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
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sortMode, setSortMode] = useState<SortMode>('name');
  const [areas, setAreas] = useState<AreaInfo[]>([]);
  const [labels, setLabels] = useState<LabelInfo[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const filterRef = useRef<HTMLInputElement>(null);

  const toggleSelect = useCallback((entityId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) next.delete(entityId);
      else next.add(entityId);
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => setSelected(new Set()), []);

  const deleteSelected = useCallback(() => {
    const ids = [...selected];
    Promise.all(ids.map((id) =>
      fetch(`/api/states/${id}`, { method: 'DELETE' })
    )).then(() => {
      setSelected(new Set());
      setConfirmDelete(false);
    });
  }, [selected]);

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

  // Dynamic page title
  useEffect(() => {
    const count = entities.length;
    document.title = count > 0 ? `Marge (${count})` : 'Marge';
  }, [entities.length]);

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

  // Fetch areas and labels for grouping
  useEffect(() => {
    const fetchAreas = () => {
      fetch('/api/areas').then((r) => r.json()).then(setAreas).catch(() => setAreas([]));
    };
    const fetchLabels = () => {
      fetch('/api/labels').then((r) => r.json()).then(setLabels).catch(() => setLabels([]));
    };
    fetchAreas();
    fetchLabels();
    const id = setInterval(() => { fetchAreas(); fetchLabels(); }, 10000);
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
      // Tab switching: 1-8
      if (e.key === '1') setActiveTab('entities');
      if (e.key === '2') setActiveTab('automations');
      if (e.key === '3') setActiveTab('areas');
      if (e.key === '4') setActiveTab('devices');
      if (e.key === '5') setActiveTab('labels');
      if (e.key === '6') setActiveTab('integrations');
      if (e.key === '7') setActiveTab('logs');
      if (e.key === '8') setActiveTab('settings');
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
      // Support prefix operators: domain:light, state:on, attr:friendly_name=Kitchen
      const domainMatch = q.match(/^domain:(\S+)$/);
      const stateMatch = q.match(/^state:(\S+)$/);
      const attrMatch = q.match(/^attr:(\S+)=(.+)$/);
      if (domainMatch) {
        list = list.filter((e) => getDomain(e.entity_id) === domainMatch[1]);
      } else if (stateMatch) {
        list = list.filter((e) => e.state.toLowerCase() === stateMatch[1]);
      } else if (attrMatch) {
        const [, key, val] = attrMatch;
        list = list.filter((e) =>
          String(e.attributes[key] ?? '').toLowerCase().includes(val)
        );
      } else {
        list = list.filter((e) =>
          e.entity_id.toLowerCase().includes(q) ||
          e.state.toLowerCase().includes(q) ||
          ((e.attributes.friendly_name as string) || '').toLowerCase().includes(q)
        );
      }
    }
    return list;
  }, [entities, filter, domainFilter]);

  const selectAll = useCallback(() => {
    const ids = filtered();
    setSelected(new Set(ids.map((e) => e.entity_id)));
  }, [filtered]);

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

  // Compute entity badges (area + label names)
  const entityBadges = useMemo(() => {
    const badges = new Map<string, { area?: string; labels: Array<{ name: string; color: string }> }>();
    for (const area of areas) {
      for (const eid of area.entities) {
        const b = badges.get(eid) || { labels: [] };
        b.area = area.name;
        badges.set(eid, b);
      }
    }
    for (const label of labels) {
      for (const eid of label.entities) {
        const b = badges.get(eid) || { labels: [] };
        b.labels.push({ name: label.name, color: label.color });
        badges.set(eid, b);
      }
    }
    return badges;
  }, [areas, labels]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('marge_token');
    setIsLoggedIn(false);
  }, []);

  const filteredList = filtered();
  const sortedFilteredList = sortEntities(filteredList, sortMode);
  const groups = groupMode === 'area'
    ? groupByArea(sortedFilteredList, areas)
    : groupMode === 'label'
    ? groupByLabel(sortedFilteredList, labels)
    : groupByDomain(sortedFilteredList);

  if (!isLoggedIn) {
    return <LoginPage onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Marge</h1>
        <input
          ref={filterRef}
          className="filter-input"
          type="text"
          placeholder="Filter... (/ to focus, domain:light, state:on)"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Escape') { setFilter(''); filterRef.current?.blur(); }}}
        />
        <QuickActions entities={entities} />
        <NotificationCenter />
        <button
          className="theme-toggle"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '\u{2600}' : '\u{1F319}'}
        </button>
        <button className="logout-btn" onClick={handleLogout} title="Sign out">
          Logout
        </button>
      </header>

      <HealthBar health={health} connStatus={connStatus} domainCounts={domainCounts} />

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'entities' ? 'active' : ''}`}
          onClick={() => setActiveTab('entities')}
        >
          Entities<span className="tab-badge">{filteredList.length !== entities.length ? `${filteredList.length}/` : ''}{entities.length}</span>
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
          className={`tab-btn ${activeTab === 'integrations' ? 'active' : ''}`}
          onClick={() => setActiveTab('integrations')}
        >
          Integrations
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
                  <Sparkline entityId={s.entity_id} width={80} height={20} />
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
              <button
                className={`chip ${groupMode === 'label' ? 'active' : ''}`}
                onClick={() => setGroupMode('label')}
              >
                By Label
              </button>
              <select
                className="sort-select"
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as SortMode)}
                title="Sort entities"
              >
                <option value="name">Sort: Name</option>
                <option value="state">Sort: State</option>
                <option value="last_changed">Sort: Recent</option>
              </select>
              <button
                className={`chip ${viewMode === 'list' ? 'active' : ''}`}
                onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
                title={`Switch to ${viewMode === 'grid' ? 'list' : 'grid'} view`}
              >
                {viewMode === 'grid' ? 'List' : 'Grid'}
              </button>
            </div>
          </div>

          {selected.size > 0 && (
            <div className="bulk-bar">
              <span>{selected.size} selected</span>
              <button className="bulk-btn" onClick={selectAll}>Select All</button>
              <button className="bulk-btn" onClick={clearSelection}>Clear</button>
              {areas.length > 0 && (
                <select
                  className="bulk-select"
                  value=""
                  onChange={(e) => {
                    const areaId = e.target.value;
                    if (!areaId) return;
                    Promise.all([...selected].map((eid) =>
                      fetch(`/api/areas/${areaId}/entities/${encodeURIComponent(eid)}`, { method: 'POST' })
                    ));
                    e.target.value = '';
                  }}
                >
                  <option value="">Assign to Area...</option>
                  {areas.map((a) => <option key={a.area_id} value={a.area_id}>{a.name}</option>)}
                </select>
              )}
              {labels.length > 0 && (
                <select
                  className="bulk-select"
                  value=""
                  onChange={(e) => {
                    const labelId = e.target.value;
                    if (!labelId) return;
                    Promise.all([...selected].map((eid) =>
                      fetch(`/api/labels/${labelId}/entities/${encodeURIComponent(eid)}`, { method: 'POST' })
                    ));
                    e.target.value = '';
                  }}
                >
                  <option value="">Assign to Label...</option>
                  {labels.map((l) => <option key={l.label_id} value={l.label_id}>{l.name}</option>)}
                </select>
              )}
              <button className="bulk-btn bulk-btn-danger" onClick={() => setConfirmDelete(true)}>
                Delete Selected
              </button>
            </div>
          )}

          <main className="entity-groups">
            {[...groups.entries()].map(([domain, domainEntities]) => (
              <section key={domain} className="domain-group">
                <h2 className="domain-title">
                  {domain.replace(/_/g, ' ')}
                  <span className="domain-count">{domainEntities.length}</span>
                </h2>
                {viewMode === 'grid' ? (
                  <div className="entity-grid">
                    {domainEntities.map((entity) => (
                      <div key={entity.entity_id} className={`entity-grid-item ${selected.has(entity.entity_id) ? 'selected' : ''}`}>
                        <input
                          type="checkbox"
                          className="entity-checkbox"
                          checked={selected.has(entity.entity_id)}
                          onChange={() => toggleSelect(entity.entity_id)}
                        />
                        <EntityCard entity={entity} onDetail={() => setSelectedEntity(entity.entity_id)} badges={entityBadges.get(entity.entity_id)} />
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
                ) : (
                  <div className="entity-list">
                    {domainEntities.map((entity) => (
                      <div key={entity.entity_id}
                        className={`entity-list-row ${selected.has(entity.entity_id) ? 'selected' : ''}`}
                        onClick={() => setSelectedEntity(entity.entity_id)}
                      >
                        <input
                          type="checkbox"
                          className="entity-list-check"
                          checked={selected.has(entity.entity_id)}
                          onChange={(e) => { e.stopPropagation(); toggleSelect(entity.entity_id); }}
                        />
                        <span className="entity-list-name">
                          {(entity.attributes.friendly_name as string) || entity.entity_id.split('.')[1]?.replace(/_/g, ' ')}
                        </span>
                        <span className="entity-list-id">{entity.entity_id}</span>
                        <span className={`entity-list-state ${entity.state === 'on' ? 'state-on' : entity.state === 'off' ? 'state-off' : ''}`}>
                          {entity.state}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
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

      {activeTab === 'integrations' && (
        <IntegrationManager />
      )}

      {activeTab === 'logs' && (
        <EventLog entities={entities} />
      )}

      {activeTab === 'settings' && (
        <Settings health={health} />
      )}

      {selectedEntity && (() => {
        const entity = entities.find((e) => e.entity_id === selectedEntity);
        if (!entity) return null;
        // Build flat entity ID list for prev/next navigation
        const flatIds = filteredList.map((e) => e.entity_id);
        const idx = flatIds.indexOf(selectedEntity);
        const onPrev = idx > 0 ? () => setSelectedEntity(flatIds[idx - 1]) : undefined;
        const onNext = idx >= 0 && idx < flatIds.length - 1 ? () => setSelectedEntity(flatIds[idx + 1]) : undefined;
        return (
          <EntityDetail entity={entity} onClose={() => setSelectedEntity(null)} onPrev={onPrev} onNext={onNext} />
        );
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
                <div className="help-row"><kbd>6</kbd><span>Integrations</span></div>
                <div className="help-row"><kbd>7</kbd><span>Logs</span></div>
                <div className="help-row"><kbd>8</kbd><span>Settings</span></div>
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
              <div className="help-section">
                <h4>Detail Panel</h4>
                <div className="help-row"><kbd>&larr;</kbd><span>Previous entity</span></div>
                <div className="help-row"><kbd>&rarr;</kbd><span>Next entity</span></div>
                <div className="help-row"><kbd>e</kbd><span>Edit state</span></div>
                <div className="help-row"><kbd>Esc</kbd><span>Close panel</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          message={`Delete ${selected.size} entity${selected.size !== 1 ? 'ies' : ''}? This cannot be undone.`}
          onConfirm={deleteSelected}
          onCancel={() => setConfirmDelete(false)}
        />
      )}

      <ToastContainer />
    </div>
  );
}

export default App
