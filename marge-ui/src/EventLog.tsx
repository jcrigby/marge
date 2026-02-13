import { useEffect, useState, useRef } from 'react';
import type { EntityState } from './types';
import { getDomain } from './types';

interface LogEntry {
  id: number;
  time: string;
  entity_id: string;
  domain: string;
  from_state: string;
  to_state: string;
  timestamp: number;
}

const DOMAIN_ICONS: Record<string, string> = {
  light: 'L',
  switch: 'S',
  sensor: 'T',
  binary_sensor: 'B',
  lock: 'K',
  cover: 'C',
  climate: 'H',
  fan: 'F',
  alarm_control_panel: 'A',
  automation: 'R',
  scene: 'E',
  input_boolean: 'I',
  input_number: '#',
};

let entryId = 0;

export default function EventLog({ entities }: { entities: EntityState[] }) {
  const [log, setLog] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [filterDomain, setFilterDomain] = useState('');
  const prevStates = useRef<Map<string, string>>(new Map());
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const changes: LogEntry[] = [];
    const now = Date.now();

    for (const e of entities) {
      const prev = prevStates.current.get(e.entity_id);
      if (prev !== undefined && prev !== e.state) {
        changes.push({
          id: ++entryId,
          time: new Date().toLocaleTimeString(),
          entity_id: e.entity_id,
          domain: getDomain(e.entity_id),
          from_state: prev,
          to_state: e.state,
          timestamp: now,
        });
      }
      prevStates.current.set(e.entity_id, e.state);
    }

    if (changes.length > 0 && !paused) {
      setLog((prev) => [...changes, ...prev].slice(0, 500));
    }
  }, [entities, paused]);

  // Auto-scroll to top on new entries
  useEffect(() => {
    if (!paused && logRef.current) {
      logRef.current.scrollTop = 0;
    }
  }, [log, paused]);

  const filtered = filterDomain
    ? log.filter((e) => e.domain === filterDomain)
    : log;

  // Unique domains in log
  const logDomains = [...new Set(log.map((e) => e.domain))].sort();

  return (
    <div className="event-log">
      <div className="automation-header">
        <h2 className="domain-title">
          Event Log
          <span className="domain-count">{filtered.length}</span>
        </h2>
        <div className="automation-header-actions">
          {logDomains.length > 1 && (
            <select
              className="log-domain-filter"
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
            >
              <option value="">All domains</option>
              {logDomains.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          )}
          <button
            className={`reload-btn ${paused ? 'active-btn' : ''}`}
            onClick={() => setPaused(!paused)}
          >
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button
            className="reload-btn"
            onClick={() => setLog([])}
          >
            Clear
          </button>
        </div>
      </div>

      <div className="log-entries" ref={logRef}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            {log.length === 0
              ? 'Waiting for state changes...'
              : 'No matching events'}
          </div>
        ) : (
          filtered.map((entry) => (
            <div key={entry.id} className="log-entry">
              <span className="log-icon" data-domain={entry.domain}>
                {DOMAIN_ICONS[entry.domain] || '?'}
              </span>
              <span className="log-time">{entry.time}</span>
              <span className="log-entity">
                {entry.entity_id.split('.')[1]?.replace(/_/g, ' ')}
              </span>
              <span className="log-transition">
                <span className="log-from">{entry.from_state}</span>
                <span className="log-arrow">&rarr;</span>
                <span className="log-to">{entry.to_state}</span>
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
