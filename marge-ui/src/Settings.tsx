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

export default function Settings({ health }: { health: HealthData | null }) {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [newTokenName, setNewTokenName] = useState('');
  const [newTokenValue, setNewTokenValue] = useState<string | null>(null);
  const [wsToken, setLocalToken] = useState(localStorage.getItem('marge_token') || '');

  const fetchTokens = useCallback(() => {
    fetch('/api/auth/tokens')
      .then((r) => r.json())
      .then(setTokens)
      .catch(() => setTokens([]));
  }, []);

  useEffect(() => {
    fetchTokens();
  }, [fetchTokens]);

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
    </div>
  );
}
