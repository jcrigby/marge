import { useEffect, useState, useCallback } from 'react';
import { callService } from './ws';

interface AutomationInfo {
  id: string;
  alias: string;
  description: string;
  mode: string;
  trigger_count: number;
  condition_count: number;
  action_count: number;
  last_triggered: string | null;
  total_triggers: number;
  enabled: boolean;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return 'just now';
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AutomationList() {
  const [automations, setAutomations] = useState<AutomationInfo[]>([]);
  const [reloading, setReloading] = useState(false);
  const [firingId, setFiringId] = useState<string | null>(null);

  const fetchAutomations = useCallback(() => {
    fetch('/api/config/automation/config')
      .then((r) => r.json())
      .then(setAutomations)
      .catch(() => setAutomations([]));
  }, []);

  useEffect(() => {
    fetchAutomations();
    const id = setInterval(fetchAutomations, 3000);
    return () => clearInterval(id);
  }, [fetchAutomations]);

  const triggerAutomation = (autoId: string) => {
    setFiringId(autoId);
    callService('automation', 'trigger', `automation.${autoId}`);
    setTimeout(() => {
      setFiringId(null);
      fetchAutomations();
    }, 800);
  };

  const reload = () => {
    setReloading(true);
    fetch('/api/config/core/reload', { method: 'POST' })
      .then(() => {
        setTimeout(() => {
          fetchAutomations();
          setReloading(false);
        }, 500);
      })
      .catch(() => setReloading(false));
  };

  return (
    <div className="automation-list">
      <div className="automation-header">
        <h2 className="domain-title">
          Automations
          <span className="domain-count">{automations.length}</span>
        </h2>
        <button
          className="reload-btn"
          onClick={reload}
          disabled={reloading}
        >
          {reloading ? 'Reloading...' : 'Reload'}
        </button>
      </div>

      {automations.length === 0 ? (
        <div className="empty-state">No automations loaded</div>
      ) : (
        <div className="automation-table-wrap">
          <table className="automation-table">
            <thead>
              <tr>
                <th>Automation</th>
                <th>Mode</th>
                <th>Triggers</th>
                <th>Fired</th>
                <th>Last Triggered</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {automations.map((auto) => (
                <tr
                  key={auto.id}
                  className={`${auto.enabled ? '' : 'disabled-row'} ${firingId === auto.id ? 'firing-row' : ''}`}
                >
                  <td>
                    <div className="auto-alias">{auto.alias || auto.id}</div>
                    {auto.description && (
                      <div className="auto-desc">{auto.description}</div>
                    )}
                    <div className="auto-id">{auto.id}</div>
                  </td>
                  <td>
                    <span className="auto-mode">{auto.mode}</span>
                  </td>
                  <td className="auto-counts">
                    {auto.trigger_count}T / {auto.condition_count}C / {auto.action_count}A
                  </td>
                  <td className="auto-fired">
                    {auto.total_triggers}
                  </td>
                  <td className="auto-last-triggered">
                    {auto.last_triggered
                      ? relativeTime(auto.last_triggered)
                      : 'never'}
                  </td>
                  <td>
                    <span className={`auto-status ${auto.enabled ? 'status-on' : 'status-off'}`}>
                      {auto.enabled ? 'ON' : 'OFF'}
                    </span>
                  </td>
                  <td>
                    <button
                      className="trigger-btn"
                      onClick={() => triggerAutomation(auto.id)}
                    >
                      Run
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
