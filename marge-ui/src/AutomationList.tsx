import { useEffect, useState, useCallback } from 'react';
import { callService } from './ws';
import { toastSuccess, toastError } from './Toast';

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
  const [showEditor, setShowEditor] = useState(false);
  const [yaml, setYaml] = useState('');
  const [yamlDirty, setYamlDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [yamlError, setYamlError] = useState<string | null>(null);

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

  const loadYaml = () => {
    fetch('/api/config/automation/yaml')
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.text();
      })
      .then((text) => {
        setYaml(text);
        setYamlDirty(false);
        setYamlError(null);
        setShowEditor(true);
      })
      .catch(() => toastError('Failed to load automation YAML'));
  };

  const saveYaml = () => {
    setSaving(true);
    setYamlError(null);
    fetch('/api/config/automation/yaml', {
      method: 'PUT',
      headers: { 'Content-Type': 'text/yaml' },
      body: yaml,
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Saved and reloaded ${data.automations_reloaded} automations`);
          setYamlDirty(false);
          setTimeout(fetchAutomations, 500);
        } else {
          setYamlError(data.message || 'Save failed');
          toastError('Invalid YAML — check syntax');
        }
        setSaving(false);
      })
      .catch(() => {
        toastError('Failed to save automation YAML');
        setSaving(false);
      });
  };

  const triggerAutomation = (autoId: string) => {
    setFiringId(autoId);
    callService('automation', 'trigger', `automation.${autoId}`);
    setTimeout(() => {
      setFiringId(null);
      fetchAutomations();
    }, 800);
  };

  const toggleEnabled = (autoId: string, currentlyEnabled: boolean) => {
    const service = currentlyEnabled ? 'turn_off' : 'turn_on';
    callService('automation', service, `automation.${autoId}`);
    setTimeout(fetchAutomations, 500);
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
        <div className="automation-header-actions">
          <button
            className={`reload-btn ${showEditor ? 'active-btn' : ''}`}
            onClick={() => showEditor ? setShowEditor(false) : loadYaml()}
          >
            {showEditor ? 'Close Editor' : 'Edit YAML'}
          </button>
          <button
            className="reload-btn"
            onClick={reload}
            disabled={reloading}
          >
            {reloading ? 'Reloading...' : 'Reload'}
          </button>
        </div>
      </div>

      {showEditor && (
        <div className="yaml-editor-panel">
          <div className="yaml-editor-header">
            <span className="yaml-editor-title">
              automations.yaml
              {yamlDirty && <span className="yaml-dirty"> (modified)</span>}
            </span>
            <button
              className="reload-btn"
              onClick={saveYaml}
              disabled={saving || !yamlDirty}
            >
              {saving ? 'Saving...' : 'Save & Reload'}
            </button>
          </div>
          {yamlError && (
            <div className="yaml-error">{yamlError}</div>
          )}
          <textarea
            className="yaml-textarea"
            value={yaml}
            onChange={(e) => {
              setYaml(e.target.value);
              setYamlDirty(true);
              setYamlError(null);
            }}
            spellCheck={false}
          />
        </div>
      )}

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
                    <button
                      className={`auto-status ${auto.enabled ? 'status-on' : 'status-off'}`}
                      onClick={() => toggleEnabled(auto.id, auto.enabled)}
                      title={auto.enabled ? 'Click to disable' : 'Click to enable'}
                    >
                      {auto.enabled ? 'ON' : 'OFF'}
                    </button>
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
