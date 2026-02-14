import { useEffect, useState, useCallback } from 'react';
import type { EntityState } from './types';
import { getDomain, getEntityName } from './types';
import { callService } from './ws';
import { toastSuccess, toastError } from './Toast';

function getFriendlyName(entity: EntityState): string {
  return (entity.attributes.friendly_name as string) || getEntityName(entity.entity_id);
}

interface Props {
  entity: EntityState;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
}

interface HistoryEntry {
  state: string;
  last_changed: string;
  attributes: Record<string, unknown>;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatShortTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function isNumeric(s: string): boolean {
  return s !== '' && s !== 'unknown' && s !== 'unavailable' && !isNaN(Number(s));
}

interface ChartPoint {
  x: number; // 0..1 normalized time
  y: number; // raw value
  time: string; // ISO string
  value: number;
}

function HistoryChart({ entries }: { entries: HistoryEntry[] }) {
  const points: ChartPoint[] = [];
  for (const e of entries) {
    if (isNumeric(e.state)) {
      points.push({
        x: 0, y: 0,
        time: e.last_changed,
        value: Number(e.state),
      });
    }
  }

  if (points.length < 2) return null;

  const times = points.map((p) => new Date(p.time).getTime());
  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  const tRange = tMax - tMin || 1;

  const values = points.map((p) => p.value);
  let vMin = Math.min(...values);
  let vMax = Math.max(...values);
  if (vMin === vMax) {
    vMin -= 1;
    vMax += 1;
  }
  const vRange = vMax - vMin;

  // Normalize
  for (let i = 0; i < points.length; i++) {
    points[i].x = (times[i] - tMin) / tRange;
    points[i].y = (points[i].value - vMin) / vRange;
  }

  const W = 440;
  const H = 140;
  const PAD_L = 42;
  const PAD_R = 8;
  const PAD_T = 8;
  const PAD_B = 24;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const px = (p: ChartPoint) => PAD_L + p.x * plotW;
  const py = (p: ChartPoint) => PAD_T + (1 - p.y) * plotH;

  // Step-line path (HA-style: hold previous value until next change)
  let path = `M${px(points[0]).toFixed(1)},${py(points[0]).toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    // horizontal to new x at old y
    path += ` L${px(points[i]).toFixed(1)},${py(points[i - 1]).toFixed(1)}`;
    // vertical to new y
    path += ` L${px(points[i]).toFixed(1)},${py(points[i]).toFixed(1)}`;
  }

  // Fill area under step-line
  let fillPath = path;
  fillPath += ` L${px(points[points.length - 1]).toFixed(1)},${(PAD_T + plotH).toFixed(1)}`;
  fillPath += ` L${px(points[0]).toFixed(1)},${(PAD_T + plotH).toFixed(1)} Z`;

  // Y-axis labels (5 ticks)
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
    label: (vMin + frac * vRange).toFixed(vRange > 10 ? 0 : 1),
    yPos: PAD_T + (1 - frac) * plotH,
  }));

  // X-axis labels (up to 5 evenly spaced)
  const xCount = Math.min(5, points.length);
  const xTicks: { label: string; xPos: number }[] = [];
  for (let i = 0; i < xCount; i++) {
    const frac = i / (xCount - 1);
    const tVal = tMin + frac * tRange;
    xTicks.push({
      label: formatShortTime(new Date(tVal).toISOString()),
      xPos: PAD_L + frac * plotW,
    });
  }

  return (
    <svg className="history-chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <line key={`yg${i}`} x1={PAD_L} x2={W - PAD_R} y1={t.yPos} y2={t.yPos}
          stroke="var(--border-subtle)" strokeWidth="0.5" />
      ))}
      {/* Fill */}
      <path d={fillPath} fill="var(--accent)" opacity="0.12" />
      {/* Step-line */}
      <path d={path} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
      {/* Data points */}
      {points.map((p, i) => (
        <circle key={i} cx={px(p)} cy={py(p)} r="2" fill="var(--accent)" />
      ))}
      {/* Y-axis labels */}
      {yTicks.map((t, i) => (
        <text key={`yl${i}`} x={PAD_L - 4} y={t.yPos + 3}
          textAnchor="end" fontSize="9" fill="var(--text-dim)">{t.label}</text>
      ))}
      {/* X-axis labels */}
      {xTicks.map((t, i) => (
        <text key={`xl${i}`} x={t.xPos} y={H - 4}
          textAnchor="middle" fontSize="9" fill="var(--text-dim)">{t.label}</text>
      ))}
    </svg>
  );
}

function EntityControls({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);
  const id = entity.entity_id;

  switch (domain) {
    case 'light':
    case 'switch':
    case 'input_boolean': {
      const isOn = entity.state === 'on';
      const brightness = entity.attributes.brightness as number | undefined;
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isOn ? 'active' : ''}`}
              onClick={() => callService(domain, 'turn_on', id)}>On</button>
            <button className={`detail-btn ${!isOn ? 'active' : ''}`}
              onClick={() => callService(domain, 'turn_off', id)}>Off</button>
            <button className="detail-btn"
              onClick={() => callService(domain, 'toggle', id)}>Toggle</button>
          </div>
          {domain === 'light' && (
            <div className="detail-slider-row">
              <label>Brightness</label>
              <input type="range" min={0} max={255}
                value={brightness ?? 0}
                onChange={(e) => callService('light', 'turn_on', id, { brightness: Number(e.target.value) })} />
              <span>{brightness !== undefined ? `${Math.round((brightness / 255) * 100)}%` : '--'}</span>
            </div>
          )}
        </div>
      );
    }
    case 'lock': {
      const isLocked = entity.state === 'locked';
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isLocked ? 'active' : ''}`}
              onClick={() => callService('lock', 'lock', id)}>Lock</button>
            <button className={`detail-btn ${!isLocked ? 'active' : ''}`}
              onClick={() => callService('lock', 'unlock', id)}>Unlock</button>
          </div>
        </div>
      );
    }
    case 'cover': {
      const pos = entity.attributes.current_position as number | undefined;
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className="detail-btn"
              onClick={() => callService('cover', 'open_cover', id)}>Open</button>
            <button className="detail-btn"
              onClick={() => callService('cover', 'stop_cover', id)}>Stop</button>
            <button className="detail-btn"
              onClick={() => callService('cover', 'close_cover', id)}>Close</button>
          </div>
          <div className="detail-slider-row">
            <label>Position</label>
            <input type="range" min={0} max={100}
              value={pos ?? 0}
              onChange={(e) => callService('cover', 'set_cover_position', id, { position: Number(e.target.value) })} />
            <span>{pos !== undefined ? `${pos}%` : '--'}</span>
          </div>
        </div>
      );
    }
    case 'fan': {
      const isOn = entity.state === 'on';
      const pct = entity.attributes.percentage as number | undefined;
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isOn ? 'active' : ''}`}
              onClick={() => callService('fan', 'turn_on', id)}>On</button>
            <button className={`detail-btn ${!isOn ? 'active' : ''}`}
              onClick={() => callService('fan', 'turn_off', id)}>Off</button>
          </div>
          <div className="detail-slider-row">
            <label>Speed</label>
            <input type="range" min={0} max={100}
              value={pct ?? 0}
              onChange={(e) => callService('fan', 'set_percentage', id, { percentage: Number(e.target.value) })} />
            <span>{pct !== undefined ? `${pct}%` : '--'}</span>
          </div>
        </div>
      );
    }
    case 'climate': {
      const temp = entity.attributes.temperature as number | undefined;
      const modes = (entity.attributes.hvac_modes as string[]) || ['off', 'heat', 'cool', 'auto'];
      return (
        <div className="detail-controls">
          <div className="detail-slider-row">
            <label>Target</label>
            <input type="range" min={10} max={35} step={0.5}
              value={temp ?? 20}
              onChange={(e) => callService('climate', 'set_temperature', id, { temperature: Number(e.target.value) })} />
            <span>{temp ?? '--'}&deg;</span>
          </div>
          <div className="detail-btn-row">
            {modes.map((m) => (
              <button key={m} className={`detail-btn ${entity.state === m ? 'active' : ''}`}
                onClick={() => callService('climate', 'set_hvac_mode', id, { hvac_mode: m })}>{m}</button>
            ))}
          </div>
        </div>
      );
    }
    case 'alarm_control_panel': {
      const actions = [
        { label: 'Disarm', service: 'disarm' },
        { label: 'Home', service: 'arm_home' },
        { label: 'Away', service: 'arm_away' },
        { label: 'Night', service: 'arm_night' },
      ];
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            {actions.map((a) => (
              <button key={a.service} className={`detail-btn ${
                entity.state === (a.service === 'disarm' ? 'disarmed' : `armed_${a.service.replace('arm_', '')}`) ? 'active' : ''
              }`}
                onClick={() => callService('alarm_control_panel', a.service, id)}>{a.label}</button>
            ))}
          </div>
        </div>
      );
    }
    case 'automation': {
      const isOn = entity.state === 'on';
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className="detail-btn"
              onClick={() => callService('automation', 'trigger', id)}>Trigger</button>
            <button className={`detail-btn ${isOn ? 'active' : ''}`}
              onClick={() => callService('automation', isOn ? 'turn_off' : 'turn_on', id)}>
              {isOn ? 'Disable' : 'Enable'}
            </button>
          </div>
        </div>
      );
    }
    case 'scene':
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className="detail-btn"
              onClick={() => callService('scene', 'turn_on', id)}>Activate</button>
          </div>
        </div>
      );
    case 'input_number': {
      const min = (entity.attributes.min as number) ?? 0;
      const max = (entity.attributes.max as number) ?? 100;
      const step = (entity.attributes.step as number) ?? 1;
      const val = parseFloat(entity.state) || 0;
      return (
        <div className="detail-controls">
          <div className="detail-slider-row">
            <label>Value</label>
            <input type="range" min={min} max={max} step={step}
              value={val}
              onChange={(e) => callService('input_number', 'set_value', id, { value: Number(e.target.value) })} />
            <span>{val}</span>
          </div>
        </div>
      );
    }
    case 'input_select': {
      const options = (entity.attributes.options as string[]) || [];
      return (
        <div className="detail-controls">
          <div className="detail-select-row">
            <select
              value={entity.state}
              onChange={(e) => callService('input_select', 'select_option', id, { option: e.target.value })}
            >
              {options.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
              {!options.includes(entity.state) && (
                <option value={entity.state}>{entity.state}</option>
              )}
            </select>
          </div>
        </div>
      );
    }
    case 'input_text':
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className="detail-btn"
              onClick={() => {
                const val = prompt('Enter value:');
                if (val !== null) callService('input_text', 'set_value', id, { value: val });
              }}>Set Value</button>
          </div>
        </div>
      );
    case 'media_player': {
      const volume = entity.attributes.volume_level as number | undefined;
      const source = entity.attributes.source as string | undefined;
      const mediaTitle = entity.attributes.media_title as string | undefined;
      const isPlaying = entity.state === 'playing';
      const isOff = entity.state === 'off';
      return (
        <div className="detail-controls">
          {mediaTitle && <div className="detail-meta">Now playing: {mediaTitle}</div>}
          {source && <div className="detail-meta">Source: {source}</div>}
          <div className="detail-btn-row">
            {isOff ? (
              <button className="detail-btn"
                onClick={() => callService('media_player', 'turn_on', id)}>On</button>
            ) : (
              <>
                <button className={`detail-btn ${isPlaying ? 'active' : ''}`}
                  onClick={() => callService('media_player', 'media_play', id)}>Play</button>
                <button className={`detail-btn ${entity.state === 'paused' ? 'active' : ''}`}
                  onClick={() => callService('media_player', 'media_pause', id)}>Pause</button>
                <button className="detail-btn"
                  onClick={() => callService('media_player', 'media_stop', id)}>Stop</button>
                <button className="detail-btn"
                  onClick={() => callService('media_player', 'turn_off', id)}>Off</button>
              </>
            )}
          </div>
          {volume !== undefined && !isOff && (
            <div className="detail-slider-row">
              <label>Volume</label>
              <input type="range" min={0} max={1} step={0.01}
                value={volume}
                onChange={(e) => callService('media_player', 'volume_set', id, { volume_level: Number(e.target.value) })} />
              <span>{Math.round(volume * 100)}%</span>
            </div>
          )}
        </div>
      );
    }
    case 'vacuum': {
      const isCleaning = entity.state === 'cleaning';
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isCleaning ? 'active' : ''}`}
              onClick={() => callService('vacuum', 'start', id)}>Start</button>
            <button className="detail-btn"
              onClick={() => callService('vacuum', 'stop', id)}>Stop</button>
            <button className={`detail-btn ${entity.state === 'docked' ? 'active' : ''}`}
              onClick={() => callService('vacuum', 'return_to_base', id)}>Dock</button>
          </div>
        </div>
      );
    }
    case 'number': {
      const min = (entity.attributes.min as number) ?? 0;
      const max = (entity.attributes.max as number) ?? 100;
      const step = (entity.attributes.step as number) ?? 1;
      const val = parseFloat(entity.state) || 0;
      return (
        <div className="detail-controls">
          <div className="detail-slider-row">
            <label>Value</label>
            <input type="range" min={min} max={max} step={step}
              value={val}
              onChange={(e) => callService('number', 'set_value', id, { value: Number(e.target.value) })} />
            <span>{val}</span>
          </div>
        </div>
      );
    }
    case 'select': {
      const options = (entity.attributes.options as string[]) || [];
      return (
        <div className="detail-controls">
          <div className="detail-select-row">
            <select
              value={entity.state}
              onChange={(e) => callService('select', 'select_option', id, { option: e.target.value })}
            >
              {options.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
              {!options.includes(entity.state) && (
                <option value={entity.state}>{entity.state}</option>
              )}
            </select>
          </div>
        </div>
      );
    }
    case 'button':
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className="detail-btn"
              onClick={() => callService('button', 'press', id)}>Press</button>
          </div>
        </div>
      );
    case 'siren': {
      const isOn = entity.state === 'on';
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isOn ? 'active' : ''}`}
              onClick={() => callService('siren', 'turn_on', id)}>On</button>
            <button className={`detail-btn ${!isOn ? 'active' : ''}`}
              onClick={() => callService('siren', 'turn_off', id)}>Off</button>
          </div>
        </div>
      );
    }
    case 'valve': {
      const isOpen = entity.state === 'open';
      return (
        <div className="detail-controls">
          <div className="detail-btn-row">
            <button className={`detail-btn ${isOpen ? 'active' : ''}`}
              onClick={() => callService('valve', 'open_valve', id)}>Open</button>
            <button className={`detail-btn ${!isOpen ? 'active' : ''}`}
              onClick={() => callService('valve', 'close_valve', id)}>Close</button>
          </div>
        </div>
      );
    }
    default:
      return null;
  }
}

function AttributeEditor({ entity }: { entity: EntityState }) {
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editVal, setEditVal] = useState('');
  const attrs = Object.entries(entity.attributes);

  const commitEdit = useCallback((key: string, rawVal: string) => {
    // Try to parse as JSON (numbers, booleans, arrays, objects), fall back to string
    let parsed: unknown;
    try { parsed = JSON.parse(rawVal); } catch { parsed = rawVal; }
    const newAttrs = { ...entity.attributes, [key]: parsed };
    fetch(`/api/states/${entity.entity_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: entity.state, attributes: newAttrs }),
    }).then((r) => {
      if (r.ok) toastSuccess(`Set ${key}`);
      else toastError(`Failed to set ${key}`);
    });
    setEditingKey(null);
  }, [entity]);

  if (attrs.length === 0) return null;

  return (
    <div className="detail-section">
      <h4>Attributes</h4>
      <table className="detail-attrs">
        <tbody>
          {attrs.map(([key, val]) => (
            <tr key={key}>
              <td className="attr-key">{key}</td>
              <td className="attr-val">
                {editingKey === key ? (
                  <div className="attr-edit-row">
                    <input
                      type="text"
                      className="attr-edit-input"
                      value={editVal}
                      onChange={(e) => setEditVal(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') commitEdit(key, editVal);
                        if (e.key === 'Escape') setEditingKey(null);
                      }}
                      autoFocus
                    />
                    <button className="attr-edit-btn" onClick={() => commitEdit(key, editVal)}>OK</button>
                    <button className="attr-edit-btn" onClick={() => setEditingKey(null)}>X</button>
                  </div>
                ) : (
                  <span
                    className="attr-val-clickable"
                    onClick={() => {
                      setEditingKey(key);
                      setEditVal(typeof val === 'object' ? JSON.stringify(val) : String(val));
                    }}
                    title="Click to edit"
                  >
                    {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ServiceCallDialog({ entityId, onClose }: { entityId: string; onClose: () => void }) {
  const domain = getDomain(entityId);
  const [svcDomain, setSvcDomain] = useState(domain);
  const [service, setService] = useState('');
  const [dataJson, setDataJson] = useState('{}');
  const [error, setError] = useState('');

  const submit = () => {
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(dataJson);
    } catch {
      setError('Invalid JSON');
      return;
    }
    callService(svcDomain, service, entityId, data);
    onClose();
  };

  return (
    <div className="svc-dialog">
      <h4>Call Service</h4>
      <div className="svc-row">
        <label>Domain</label>
        <input type="text" value={svcDomain} onChange={(e) => setSvcDomain(e.target.value)} />
      </div>
      <div className="svc-row">
        <label>Service</label>
        <input type="text" value={service} onChange={(e) => setService(e.target.value)}
          placeholder="e.g. turn_on, set_value" />
      </div>
      <div className="svc-row">
        <label>Data (JSON)</label>
        <textarea rows={3} value={dataJson} onChange={(e) => { setDataJson(e.target.value); setError(''); }} />
      </div>
      {error && <div className="svc-error">{error}</div>}
      <div className="detail-btn-row">
        <button className="detail-btn" onClick={submit} disabled={!service.trim()}>Call</button>
        <button className="detail-btn" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}

interface StatsBucket {
  hour: string;
  min: number;
  max: number;
  mean: number;
  count: number;
}

function StatsPanel({ entityId }: { entityId: string }) {
  const [stats, setStats] = useState<StatsBucket[]>([]);

  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    fetch(`/api/statistics/${encodeURIComponent(entityId)}?start=${start.toISOString()}&end=${now.toISOString()}`)
      .then((r) => r.json())
      .then((data: StatsBucket[]) => setStats(data))
      .catch(() => setStats([]));
  }, [entityId]);

  if (stats.length === 0) return null;

  const allMin = Math.min(...stats.map((s) => s.min));
  const allMax = Math.max(...stats.map((s) => s.max));
  const allMean = stats.reduce((a, s) => a + s.mean * s.count, 0) / Math.max(1, stats.reduce((a, s) => a + s.count, 0));
  const total = stats.reduce((a, s) => a + s.count, 0);

  return (
    <div className="detail-section">
      <h4>Statistics (24h)</h4>
      <div className="stats-summary">
        <div className="stats-kv"><span className="stats-label">Min</span><span className="stats-val">{allMin.toFixed(1)}</span></div>
        <div className="stats-kv"><span className="stats-label">Max</span><span className="stats-val">{allMax.toFixed(1)}</span></div>
        <div className="stats-kv"><span className="stats-label">Mean</span><span className="stats-val">{allMean.toFixed(1)}</span></div>
        <div className="stats-kv"><span className="stats-label">Samples</span><span className="stats-val">{total}</span></div>
      </div>
    </div>
  );
}

export default function EntityDetail({ entity, onClose, onPrev, onNext }: Props) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [editState, setEditState] = useState('');
  const [editing, setEditing] = useState(false);
  const [showSvcDialog, setShowSvcDialog] = useState(false);
  // Track entity state changes to auto-refresh history
  const stateKey = `${entity.entity_id}:${entity.state}:${entity.last_changed}`;

  useEffect(() => {
    const fetchHistory = () => {
      const now = new Date();
      const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const url = `/api/history/period/${encodeURIComponent(entity.entity_id)}?start=${start.toISOString()}&end=${now.toISOString()}`;
      fetch(url)
        .then((r) => r.json())
        .then((data: HistoryEntry[]) => setHistory(data.slice(-200)))
        .catch(() => setHistory([]));
    };
    fetchHistory();
  }, [entity.entity_id, stateKey]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && onPrev) { e.preventDefault(); onPrev(); }
      if (e.key === 'ArrowRight' && onNext) { e.preventDefault(); onNext(); }
      if (e.key === 'e') { setEditState(entity.state); setEditing(true); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, onPrev, onNext, entity.state]);

  const hasNumericHistory = history.some((h) => isNumeric(h.state));

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-header">
          <div className="detail-nav">
            {onPrev && <button className="detail-nav-btn" onClick={onPrev} title="Previous (Left arrow)">&larr;</button>}
          </div>
          <div className="detail-title">
            <h3>{getFriendlyName(entity)}</h3>
            <span className="detail-entity-id">{entity.entity_id}</span>
          </div>
          <div className="detail-nav">
            {onNext && <button className="detail-nav-btn" onClick={onNext} title="Next (Right arrow)">&rarr;</button>}
            <button className="detail-close" onClick={onClose}>X</button>
          </div>
        </div>

        <div className="detail-state">
          {editing ? (
            <div className="detail-state-edit">
              <input
                type="text"
                className="detail-state-input"
                value={editState}
                onChange={(e) => setEditState(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    fetch(`/api/states/${entity.entity_id}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ state: editState, attributes: entity.attributes }),
                    });
                    setEditing(false);
                  }
                  if (e.key === 'Escape') setEditing(false);
                }}
                autoFocus
              />
              <button className="detail-btn" onClick={() => {
                fetch(`/api/states/${entity.entity_id}`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ state: editState, attributes: entity.attributes }),
                });
                setEditing(false);
              }}>Set</button>
              <button className="detail-btn" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          ) : (
            <span
              className="detail-state-value detail-state-clickable"
              onClick={() => { setEditState(entity.state); setEditing(true); }}
              title="Click to edit state"
            >
              {entity.state}
            </span>
          )}
          <span className="detail-state-time">
            Changed {formatTime(entity.last_changed)}
          </span>
        </div>

        <EntityControls entity={entity} />

        <AttributeEditor entity={entity} />

        <div className="detail-section">
          <button className="detail-btn svc-call-btn" onClick={() => setShowSvcDialog(!showSvcDialog)}>
            {showSvcDialog ? 'Hide' : 'Call Service...'}
          </button>
          {showSvcDialog && (
            <ServiceCallDialog entityId={entity.entity_id} onClose={() => setShowSvcDialog(false)} />
          )}
        </div>

        {hasNumericHistory && (
          <div className="detail-section">
            <h4>History (24h)</h4>
            <HistoryChart entries={history} />
          </div>
        )}

        {isNumeric(entity.state) && <StatsPanel entityId={entity.entity_id} />}

        {history.length > 0 && (
          <div className="detail-section">
            <h4>{hasNumericHistory ? 'State Log' : 'History (24h)'}</h4>
            <div className="detail-history">
              {history.slice().reverse().slice(0, 50).map((entry, i) => (
                <div key={i} className="history-row">
                  <span className="history-state">{entry.state}</span>
                  <span className="history-time">{formatTime(entry.last_changed)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
