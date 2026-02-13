import { useEffect, useState, useCallback } from 'react';
import { toastSuccess, toastError } from './Toast';
import { setToken as setWsToken } from './ws';
import type { HealthData } from './types';

interface TokenInfo {
  id: string;
  name: string;
  created_at: string;
  token?: string;
}

interface DiagnosticData {
  automations: number;
  scenes: number;
  areas: number;
  devices: number;
  labels: number;
}

export default function Settings({ health }: { health: HealthData | null }) {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [newTokenName, setNewTokenName] = useState('');
  const [newTokenValue, setNewTokenValue] = useState<string | null>(null);
  const [wsToken, setLocalToken] = useState(localStorage.getItem('marge_token') || '');
  const [diag, setDiag] = useState<DiagnosticData | null>(null);
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);

  const fetchTokens = useCallback(() => {
    fetch('/api/auth/tokens')
      .then((r) => r.json())
      .then(setTokens)
      .catch(() => setTokens([]));
  }, []);

  const fetchDiagnostics = useCallback(() => {
    Promise.all([
      fetch('/api/config/automation/config').then((r) => r.json()).catch(() => []),
      fetch('/api/config/scene/config').then((r) => r.json()).catch(() => []),
      fetch('/api/areas').then((r) => r.json()).catch(() => []),
      fetch('/api/devices').then((r) => r.json()).catch(() => []),
      fetch('/api/labels').then((r) => r.json()).catch(() => []),
    ]).then(([autos, scenes, areas, devices, labels]) => {
      setDiag({
        automations: autos.length,
        scenes: scenes.length,
        areas: areas.length,
        devices: devices.length,
        labels: labels.length,
      });
    });
  }, []);

  useEffect(() => {
    fetchTokens();
    fetchDiagnostics();
  }, [fetchTokens, fetchDiagnostics]);

  const createToken = () => {
    if (!newTokenName.trim()) return;
    fetch('/api/auth/tokens', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newTokenName.trim() }),
    })
      .then((r) => r.json())
      .then((data: TokenInfo) => {
        setNewTokenValue(data.token || null);
        setNewTokenName('');
        toastSuccess(`Token "${data.name}" created`);
        fetchTokens();
      })
      .catch(() => toastError('Failed to create token'));
  };

  const deleteToken = (id: string, name: string) => {
    fetch(`/api/auth/tokens/${id}`, { method: 'DELETE' })
      .then((r) => {
        if (r.ok) {
          toastSuccess(`Token "${name}" deleted`);
          fetchTokens();
        } else {
          toastError('Failed to delete token');
        }
      });
  };

  const saveWsToken = () => {
    setWsToken(wsToken);
    toastSuccess('WebSocket token saved');
  };

  function formatUptime(secs: number): string {
    const d = Math.floor(secs / 86400);
    const h = Math.floor((secs % 86400) / 3600);
    const m = Math.floor((secs % 3600) / 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m ${secs % 60}s`;
  }

  return (
    <div className="settings-panel">
      {/* System Info */}
      <div className="settings-section">
        <h2 className="domain-title">
          System Info
        </h2>
        {health ? (
          <div className="settings-grid">
            <div className="settings-kv">
              <span className="settings-key">Version</span>
              <span className="settings-val">{health.version}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Uptime</span>
              <span className="settings-val">{formatUptime(health.uptime_seconds)}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Entities</span>
              <span className="settings-val">{health.entity_count}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Memory</span>
              <span className="settings-val">{health.memory_rss_mb.toFixed(1)} MB</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Startup</span>
              <span className="settings-val">{health.startup_ms} ms</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Avg Latency</span>
              <span className="settings-val">{health.latency_avg_us} us</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">State Changes</span>
              <span className="settings-val">{health.state_changes}</span>
            </div>
          </div>
        ) : (
          <div className="empty-state">Connecting...</div>
        )}
      </div>

      {/* WebSocket Auth */}
      <div className="settings-section">
        <h2 className="domain-title">
          Connection
        </h2>
        <div className="settings-form-row">
          <input
            type="password"
            className="area-input"
            placeholder="Bearer token (for authenticated mode)"
            value={wsToken}
            onChange={(e) => setLocalToken(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && saveWsToken()}
          />
          <button className="reload-btn" onClick={saveWsToken}>Save</button>
        </div>
        <p className="settings-hint">
          Set the bearer token used for WebSocket and REST authentication.
          Leave empty if auth is disabled.
        </p>
      </div>

      {/* Backup */}
      <div className="settings-section">
        <h2 className="domain-title">
          Backup
        </h2>
        <div className="settings-form-row">
          <button className="reload-btn" onClick={() => {
            const a = document.createElement('a');
            a.href = '/api/backup';
            a.download = '';
            a.click();
            toastSuccess('Backup download started');
          }}>Download Backup</button>
        </div>
        <p className="settings-hint">
          Downloads a tar.gz archive containing the database, automations, and scenes.
        </p>
      </div>

      {/* Diagnostics */}
      {diag && (
        <div className="settings-section">
          <h2 className="domain-title">Diagnostics</h2>
          <div className="settings-grid">
            <div className="settings-kv">
              <span className="settings-key">Automations</span>
              <span className="settings-val">{diag.automations}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Scenes</span>
              <span className="settings-val">{diag.scenes}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Areas</span>
              <span className="settings-val">{diag.areas}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Devices</span>
              <span className="settings-val">{diag.devices}</span>
            </div>
            <div className="settings-kv">
              <span className="settings-key">Labels</span>
              <span className="settings-val">{diag.labels}</span>
            </div>
          </div>
        </div>
      )}

      {/* Long-Lived Tokens */}
      <div className="settings-section">
        <h2 className="domain-title">
          Access Tokens
          <span className="domain-count">{tokens.length}</span>
        </h2>

        <div className="settings-form-row">
          <input
            type="text"
            className="area-input"
            placeholder="Token name (e.g., Mobile App)"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createToken()}
          />
          <button className="reload-btn" onClick={createToken}>Create</button>
        </div>

        {newTokenValue && (
          <div className="token-reveal">
            <p className="settings-hint">
              Copy this token now. It will not be shown again.
            </p>
            <code className="token-value">{newTokenValue}</code>
            <button className="reload-btn" onClick={() => {
              navigator.clipboard?.writeText(newTokenValue);
              toastSuccess('Token copied to clipboard');
            }}>Copy</button>
            <button className="reload-btn" onClick={() => setNewTokenValue(null)}>Dismiss</button>
          </div>
        )}

        {tokens.length === 0 ? (
          <div className="empty-state">No access tokens. Create one above.</div>
        ) : (
          <div className="token-list">
            {tokens.map((t) => (
              <div key={t.id} className="token-row">
                <div className="token-info">
                  <span className="token-name">{t.name}</span>
                  <span className="token-meta">{t.id} &middot; Created {new Date(t.created_at).toLocaleDateString()}</span>
                </div>
                <button className="reload-btn" onClick={() => deleteToken(t.id, t.name)}>Revoke</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Danger Zone */}
      <div className="settings-section settings-danger">
        <h2 className="domain-title">Danger Zone</h2>
        <div className="settings-form-row">
          <button
            className="reload-btn danger-btn"
            onClick={() => setShowPurgeConfirm(true)}
          >
            Purge All Entities
          </button>
          <button
            className="reload-btn danger-btn"
            onClick={() => {
              fetch('/api/config/automation/reload', { method: 'POST' })
                .then((r) => {
                  if (r.ok) toastSuccess('Automations reloaded');
                  else toastError('Reload failed');
                });
            }}
          >
            Reload Automations
          </button>
        </div>
        <p className="settings-hint">
          Purge removes all entity states from memory. Reload re-reads automation YAML.
        </p>
        {showPurgeConfirm && (
          <div className="purge-confirm">
            <p>Are you sure? This will delete all {health?.entity_count ?? 0} entities.</p>
            <div className="settings-form-row">
              <button className="reload-btn danger-btn" onClick={() => {
                fetch('/api/states', { method: 'GET' })
                  .then((r) => r.json())
                  .then((states: Array<{ entity_id: string }>) =>
                    Promise.all(states.map((s) =>
                      fetch(`/api/states/${s.entity_id}`, { method: 'DELETE' })
                    ))
                  )
                  .then(() => {
                    toastSuccess('All entities purged');
                    setShowPurgeConfirm(false);
                  })
                  .catch(() => toastError('Purge failed'));
              }}>Yes, Purge Everything</button>
              <button className="reload-btn" onClick={() => setShowPurgeConfirm(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
