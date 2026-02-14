import { useEffect, useState, useCallback } from 'react';
import { callService } from './ws';
import { toastSuccess, toastError } from './Toast';
import AutomationEditor from './AutomationEditor';

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

interface SceneInfo {
  id: string;
  name: string;
  entity_count: number;
  entities: string[];
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
  const [scenes, setScenes] = useState<SceneInfo[]>([]);
  const [showSceneEditor, setShowSceneEditor] = useState(false);
  const [sceneYaml, setSceneYaml] = useState('');
  const [sceneYamlDirty, setSceneYamlDirty] = useState(false);
  const [sceneSaving, setSceneSaving] = useState(false);
  const [sceneYamlError, setSceneYamlError] = useState<string | null>(null);
  const [activatingScene, setActivatingScene] = useState<string | null>(null);
  const [showVisualEditor, setShowVisualEditor] = useState(false);

  const fetchScenes = useCallback(() => {
    fetch('/api/config/scene/config')
      .then((r) => r.json())
      .then(setScenes)
      .catch(() => setScenes([]));
  }, []);

  useEffect(() => {
    fetchScenes();
    const id = setInterval(fetchScenes, 5000);
    return () => clearInterval(id);
  }, [fetchScenes]);

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

  const loadSceneYaml = () => {
    fetch('/api/config/scene/yaml')
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.text();
      })
      .then((text) => {
        setSceneYaml(text);
        setSceneYamlDirty(false);
        setSceneYamlError(null);
        setShowSceneEditor(true);
      })
      .catch(() => toastError('Failed to load scene YAML'));
  };

  const saveSceneYaml = () => {
    setSceneSaving(true);
    setSceneYamlError(null);
    fetch('/api/config/scene/yaml', {
      method: 'PUT',
      headers: { 'Content-Type': 'text/yaml' },
      body: sceneYaml,
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess('Scene YAML saved');
          setSceneYamlDirty(false);
          setTimeout(fetchScenes, 500);
        } else {
          setSceneYamlError(data.message || 'Save failed');
          toastError('Invalid YAML — check syntax');
        }
        setSceneSaving(false);
      })
      .catch(() => {
        toastError('Failed to save scene YAML');
        setSceneSaving(false);
      });
  };

  const activateScene = (sceneId: string) => {
    setActivatingScene(sceneId);
    callService('scene', 'turn_on', `scene.${sceneId}`);
    setTimeout(() => setActivatingScene(null), 800);
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
            className={`reload-btn ${showVisualEditor ? 'active-btn' : ''}`}
            onClick={() => { setShowVisualEditor((v) => !v); if (!showVisualEditor) setShowEditor(false); }}
          >
            {showVisualEditor ? 'Close Builder' : 'New Automation'}
          </button>
          <button
            className={`reload-btn ${showEditor ? 'active-btn' : ''}`}
            onClick={() => { if (showEditor) { setShowEditor(false); } else { loadYaml(); setShowVisualEditor(false); } }}
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

      {showVisualEditor && (
        <AutomationEditor
          onClose={() => setShowVisualEditor(false)}
          onSaved={() => {
            setShowVisualEditor(false);
            setTimeout(fetchAutomations, 500);
          }}
        />
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

      {/* ── Scenes ── */}
      <div className="automation-header" style={{ marginTop: '2rem' }}>
        <h2 className="domain-title">
          Scenes
          <span className="domain-count">{scenes.length}</span>
        </h2>
        <div className="automation-header-actions">
          <button
            className={`reload-btn ${showSceneEditor ? 'active-btn' : ''}`}
            onClick={() => showSceneEditor ? setShowSceneEditor(false) : loadSceneYaml()}
          >
            {showSceneEditor ? 'Close Editor' : 'Edit YAML'}
          </button>
        </div>
      </div>

      {showSceneEditor && (
        <div className="yaml-editor-panel">
          <div className="yaml-editor-header">
            <span className="yaml-editor-title">
              scenes.yaml
              {sceneYamlDirty && <span className="yaml-dirty"> (modified)</span>}
            </span>
            <button
              className="reload-btn"
              onClick={saveSceneYaml}
              disabled={sceneSaving || !sceneYamlDirty}
            >
              {sceneSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
          {sceneYamlError && (
            <div className="yaml-error">{sceneYamlError}</div>
          )}
          <textarea
            className="yaml-textarea"
            value={sceneYaml}
            onChange={(e) => {
              setSceneYaml(e.target.value);
              setSceneYamlDirty(true);
              setSceneYamlError(null);
            }}
            spellCheck={false}
          />
        </div>
      )}

      {scenes.length === 0 ? (
        <div className="empty-state">No scenes loaded</div>
      ) : (
        <div className="scene-grid">
          {scenes.map((scene) => (
            <div
              key={scene.id}
              className={`card scene-card ${activatingScene === scene.id ? 'firing-row' : ''}`}
            >
              <div className="card-header">
                <span className="card-name">{scene.name}</span>
                <span className="domain-count">{scene.entity_count}</span>
              </div>
              <div className="auto-id">scene.{scene.id}</div>
              {scene.entities.length > 0 && (
                <div className="area-entities">
                  {scene.entities.map((eid) => (
                    <span key={eid} className="chip">{eid.split('.')[1]?.replace(/_/g, ' ')}</span>
                  ))}
                </div>
              )}
              <div className="card-actions">
                <button
                  className="trigger-btn"
                  onClick={() => activateScene(scene.id)}
                >
                  Activate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
