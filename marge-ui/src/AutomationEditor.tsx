import { useState, useMemo } from 'react';
import { toastSuccess, toastError } from './Toast';

/* ── Types ───────────────────────────────────── */

interface TriggerState {
  platform: 'state' | 'time' | 'sun';
  entity_id: string;
  from: string;
  to: string;
  at: string;
  event: 'sunrise' | 'sunset';
  offset: string;
}

interface ConditionState {
  condition: 'state' | 'template' | 'time';
  entity_id: string;
  state: string;
  value_template: string;
  after: string;
  before: string;
}

interface ActionState {
  service: string;
  entity_id: string;
  data: string;
}

function newTrigger(): TriggerState {
  return { platform: 'state', entity_id: '', from: '', to: '', at: '', event: 'sunrise', offset: '' };
}

function newCondition(): ConditionState {
  return { condition: 'state', entity_id: '', state: '', value_template: '', after: '', before: '' };
}

function newAction(): ActionState {
  return { service: '', entity_id: '', data: '' };
}

/* ── YAML Serializer (hand-written, no deps) ── */

function indent(level: number): string {
  return '  '.repeat(level);
}

function yamlScalar(val: string): string {
  // Quote strings that might be misinterpreted as booleans or contain special chars
  if (/^(on|off|true|false|yes|no|null)$/i.test(val)) return `"${val}"`;
  if (/[:#\[\]{}&*!|>'"%@`]/.test(val) || val.includes('\n')) return `"${val.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
  if (val === '') return '""';
  return val;
}

function serializeTrigger(t: TriggerState): string {
  const lines: string[] = [];
  lines.push(`${indent(2)}- platform: ${t.platform}`);
  if (t.platform === 'state') {
    if (t.entity_id) lines.push(`${indent(3)}entity_id: ${yamlScalar(t.entity_id)}`);
    if (t.from) lines.push(`${indent(3)}from: ${yamlScalar(t.from)}`);
    if (t.to) lines.push(`${indent(3)}to: ${yamlScalar(t.to)}`);
  } else if (t.platform === 'time') {
    if (t.at) lines.push(`${indent(3)}at: ${yamlScalar(t.at)}`);
  } else if (t.platform === 'sun') {
    lines.push(`${indent(3)}event: ${t.event}`);
    if (t.offset) lines.push(`${indent(3)}offset: ${yamlScalar(t.offset)}`);
  }
  return lines.join('\n');
}

function serializeCondition(c: ConditionState): string {
  const lines: string[] = [];
  lines.push(`${indent(2)}- condition: ${c.condition}`);
  if (c.condition === 'state') {
    if (c.entity_id) lines.push(`${indent(3)}entity_id: ${yamlScalar(c.entity_id)}`);
    if (c.state) lines.push(`${indent(3)}state: ${yamlScalar(c.state)}`);
  } else if (c.condition === 'template') {
    if (c.value_template) lines.push(`${indent(3)}value_template: ${yamlScalar(c.value_template)}`);
  } else if (c.condition === 'time') {
    if (c.after) lines.push(`${indent(3)}after: ${yamlScalar(c.after)}`);
    if (c.before) lines.push(`${indent(3)}before: ${yamlScalar(c.before)}`);
  }
  return lines.join('\n');
}

function serializeAction(a: ActionState): string {
  const lines: string[] = [];
  lines.push(`${indent(2)}- service: ${a.service}`);
  if (a.entity_id) {
    lines.push(`${indent(3)}target:`);
    lines.push(`${indent(4)}entity_id: ${yamlScalar(a.entity_id)}`);
  }
  if (a.data.trim()) {
    try {
      const parsed = JSON.parse(a.data);
      lines.push(`${indent(3)}data:`);
      for (const [key, val] of Object.entries(parsed)) {
        lines.push(`${indent(4)}${key}: ${yamlScalar(String(val))}`);
      }
    } catch {
      // If JSON is invalid, skip data
    }
  }
  return lines.join('\n');
}

function buildYaml(
  id: string,
  alias: string,
  description: string,
  mode: string,
  triggers: TriggerState[],
  conditions: ConditionState[],
  actions: ActionState[],
): string {
  const lines: string[] = [];
  lines.push(`- id: ${yamlScalar(id)}`);
  lines.push(`  alias: ${yamlScalar(alias)}`);
  if (description) lines.push(`  description: ${yamlScalar(description)}`);
  lines.push(`  mode: ${mode}`);

  if (triggers.length > 0) {
    lines.push('  trigger:');
    for (const t of triggers) {
      lines.push(serializeTrigger(t));
    }
  }

  if (conditions.length > 0) {
    lines.push('  condition:');
    for (const c of conditions) {
      lines.push(serializeCondition(c));
    }
  }

  if (actions.length > 0) {
    lines.push('  action:');
    for (const a of actions) {
      lines.push(serializeAction(a));
    }
  }

  return lines.join('\n') + '\n';
}

function aliasToId(alias: string): string {
  return alias
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    || 'new_automation';
}

/* ── Component ───────────────────────────────── */

interface AutomationEditorProps {
  onClose: () => void;
  onSaved: () => void;
}

export default function AutomationEditor({ onClose, onSaved }: AutomationEditorProps) {
  const [alias, setAlias] = useState('');
  const [customId, setCustomId] = useState('');
  const [description, setDescription] = useState('');
  const [mode, setMode] = useState('single');
  const [triggers, setTriggers] = useState<TriggerState[]>([newTrigger()]);
  const [conditions, setConditions] = useState<ConditionState[]>([]);
  const [actions, setActions] = useState<ActionState[]>([newAction()]);
  const [saving, setSaving] = useState(false);

  const autoId = customId || aliasToId(alias);

  const preview = useMemo(
    () => buildYaml(autoId, alias, description, mode, triggers, conditions, actions),
    [autoId, alias, description, mode, triggers, conditions, actions],
  );

  /* ── Trigger helpers ── */
  const updateTrigger = (idx: number, patch: Partial<TriggerState>) => {
    setTriggers((prev) => prev.map((t, i) => (i === idx ? { ...t, ...patch } : t)));
  };
  const removeTrigger = (idx: number) => {
    setTriggers((prev) => prev.filter((_, i) => i !== idx));
  };

  /* ── Condition helpers ── */
  const updateCondition = (idx: number, patch: Partial<ConditionState>) => {
    setConditions((prev) => prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  };
  const removeCondition = (idx: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== idx));
  };

  /* ── Action helpers ── */
  const updateAction = (idx: number, patch: Partial<ActionState>) => {
    setActions((prev) => prev.map((a, i) => (i === idx ? { ...a, ...patch } : a)));
  };
  const removeAction = (idx: number) => {
    setActions((prev) => prev.filter((_, i) => i !== idx));
  };

  /* ── Save ── */
  const handleSave = async () => {
    if (!alias.trim()) {
      toastError('Alias is required');
      return;
    }
    if (actions.length === 0 || !actions.some((a) => a.service.trim())) {
      toastError('At least one action with a service is required');
      return;
    }

    setSaving(true);
    try {
      // Fetch existing YAML
      const resp = await fetch('/api/config/automation/yaml');
      if (!resp.ok) throw new Error('Failed to fetch existing YAML');
      const existing = await resp.text();

      // Append new automation
      const combined = existing.trimEnd() + '\n' + preview;

      // PUT combined YAML
      const saveResp = await fetch('/api/config/automation/yaml', {
        method: 'PUT',
        headers: { 'Content-Type': 'text/yaml' },
        body: combined,
      });
      const data = await saveResp.json();
      if (data.result === 'ok') {
        toastSuccess(`Created automation "${alias}" and reloaded ${data.automations_reloaded} automations`);
        onSaved();
      } else {
        toastError(data.message || 'Save failed');
      }
    } catch {
      toastError('Failed to save automation');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="auto-editor">
      <div className="yaml-editor-header">
        <span className="yaml-editor-title">New Automation</span>
        <button className="reload-btn" onClick={onClose}>Close</button>
      </div>

      {/* ── Header fields ── */}
      <div className="auto-editor-section">
        <div className="auto-editor-row">
          <label className="auto-editor-label">Alias</label>
          <input
            className="auto-editor-input"
            type="text"
            value={alias}
            onChange={(e) => setAlias(e.target.value)}
            placeholder="e.g. Turn on lights at sunset"
          />
        </div>
        <div className="auto-editor-row">
          <label className="auto-editor-label">ID</label>
          <input
            className="auto-editor-input"
            type="text"
            value={customId}
            onChange={(e) => setCustomId(e.target.value)}
            placeholder={aliasToId(alias) || 'auto-generated from alias'}
          />
        </div>
        <div className="auto-editor-row">
          <label className="auto-editor-label">Description</label>
          <input
            className="auto-editor-input"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
          />
        </div>
        <div className="auto-editor-row">
          <label className="auto-editor-label">Mode</label>
          <select
            className="auto-editor-select"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="single">single</option>
            <option value="restart">restart</option>
            <option value="queued">queued</option>
            <option value="parallel">parallel</option>
          </select>
        </div>
      </div>

      {/* ── Triggers ── */}
      <div className="auto-editor-section">
        <h3 className="domain-title">
          Triggers
          <span className="domain-count">{triggers.length}</span>
        </h3>
        {triggers.map((t, idx) => (
          <div key={idx} className="auto-editor-block">
            <div className="auto-editor-row">
              <label className="auto-editor-label">Platform</label>
              <select
                className="auto-editor-select"
                value={t.platform}
                onChange={(e) => updateTrigger(idx, { platform: e.target.value as TriggerState['platform'] })}
              >
                <option value="state">state</option>
                <option value="time">time</option>
                <option value="sun">sun</option>
              </select>
              <button className="auto-editor-remove-btn" onClick={() => removeTrigger(idx)} title="Remove trigger">X</button>
            </div>
            {t.platform === 'state' && (
              <>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">Entity ID</label>
                  <input className="auto-editor-input" type="text" value={t.entity_id} onChange={(e) => updateTrigger(idx, { entity_id: e.target.value })} placeholder="binary_sensor.motion" />
                </div>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">From</label>
                  <input className="auto-editor-input" type="text" value={t.from} onChange={(e) => updateTrigger(idx, { from: e.target.value })} placeholder="optional" />
                </div>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">To</label>
                  <input className="auto-editor-input" type="text" value={t.to} onChange={(e) => updateTrigger(idx, { to: e.target.value })} placeholder="optional" />
                </div>
              </>
            )}
            {t.platform === 'time' && (
              <div className="auto-editor-row">
                <label className="auto-editor-label">At</label>
                <input className="auto-editor-input" type="text" value={t.at} onChange={(e) => updateTrigger(idx, { at: e.target.value })} placeholder="HH:MM:SS" />
              </div>
            )}
            {t.platform === 'sun' && (
              <>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">Event</label>
                  <select className="auto-editor-select" value={t.event} onChange={(e) => updateTrigger(idx, { event: e.target.value as 'sunrise' | 'sunset' })}>
                    <option value="sunrise">sunrise</option>
                    <option value="sunset">sunset</option>
                  </select>
                </div>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">Offset</label>
                  <input className="auto-editor-input" type="text" value={t.offset} onChange={(e) => updateTrigger(idx, { offset: e.target.value })} placeholder="-00:30:00" />
                </div>
              </>
            )}
          </div>
        ))}
        <button className="auto-editor-add-btn" onClick={() => setTriggers((prev) => [...prev, newTrigger()])}>
          + Add Trigger
        </button>
      </div>

      {/* ── Conditions ── */}
      <div className="auto-editor-section">
        <h3 className="domain-title">
          Conditions
          <span className="domain-count">{conditions.length}</span>
        </h3>
        {conditions.map((c, idx) => (
          <div key={idx} className="auto-editor-block">
            <div className="auto-editor-row">
              <label className="auto-editor-label">Type</label>
              <select
                className="auto-editor-select"
                value={c.condition}
                onChange={(e) => updateCondition(idx, { condition: e.target.value as ConditionState['condition'] })}
              >
                <option value="state">state</option>
                <option value="template">template</option>
                <option value="time">time</option>
              </select>
              <button className="auto-editor-remove-btn" onClick={() => removeCondition(idx)} title="Remove condition">X</button>
            </div>
            {c.condition === 'state' && (
              <>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">Entity ID</label>
                  <input className="auto-editor-input" type="text" value={c.entity_id} onChange={(e) => updateCondition(idx, { entity_id: e.target.value })} placeholder="input_boolean.vacation_mode" />
                </div>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">State</label>
                  <input className="auto-editor-input" type="text" value={c.state} onChange={(e) => updateCondition(idx, { state: e.target.value })} placeholder="off" />
                </div>
              </>
            )}
            {c.condition === 'template' && (
              <div className="auto-editor-row">
                <label className="auto-editor-label">Template</label>
                <textarea
                  className="auto-editor-textarea"
                  value={c.value_template}
                  onChange={(e) => updateCondition(idx, { value_template: e.target.value })}
                  placeholder="{{ states('sensor.temperature') | float > 20 }}"
                  rows={3}
                />
              </div>
            )}
            {c.condition === 'time' && (
              <>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">After</label>
                  <input className="auto-editor-input" type="text" value={c.after} onChange={(e) => updateCondition(idx, { after: e.target.value })} placeholder="HH:MM:SS" />
                </div>
                <div className="auto-editor-row">
                  <label className="auto-editor-label">Before</label>
                  <input className="auto-editor-input" type="text" value={c.before} onChange={(e) => updateCondition(idx, { before: e.target.value })} placeholder="HH:MM:SS" />
                </div>
              </>
            )}
          </div>
        ))}
        <button className="auto-editor-add-btn" onClick={() => setConditions((prev) => [...prev, newCondition()])}>
          + Add Condition
        </button>
      </div>

      {/* ── Actions ── */}
      <div className="auto-editor-section">
        <h3 className="domain-title">
          Actions
          <span className="domain-count">{actions.length}</span>
        </h3>
        {actions.map((a, idx) => (
          <div key={idx} className="auto-editor-block">
            <div className="auto-editor-row">
              <label className="auto-editor-label">Service</label>
              <input className="auto-editor-input" type="text" value={a.service} onChange={(e) => updateAction(idx, { service: e.target.value })} placeholder="light.turn_on" />
              <button className="auto-editor-remove-btn" onClick={() => removeAction(idx)} title="Remove action">X</button>
            </div>
            <div className="auto-editor-row">
              <label className="auto-editor-label">Entity ID</label>
              <input className="auto-editor-input" type="text" value={a.entity_id} onChange={(e) => updateAction(idx, { entity_id: e.target.value })} placeholder="light.living_room" />
            </div>
            <div className="auto-editor-row">
              <label className="auto-editor-label">Data (JSON)</label>
              <textarea
                className="auto-editor-textarea"
                value={a.data}
                onChange={(e) => updateAction(idx, { data: e.target.value })}
                placeholder='{"brightness": 255}'
                rows={2}
              />
            </div>
          </div>
        ))}
        <button className="auto-editor-add-btn" onClick={() => setActions((prev) => [...prev, newAction()])}>
          + Add Action
        </button>
      </div>

      {/* ── YAML Preview ── */}
      <div className="auto-editor-section">
        <h3 className="domain-title">YAML Preview</h3>
        <textarea
          className="auto-editor-preview"
          value={preview}
          readOnly
          rows={Math.min(preview.split('\n').length + 1, 20)}
        />
      </div>

      {/* ── Bottom actions ── */}
      <div className="auto-editor-actions">
        <button className="reload-btn" onClick={onClose}>Cancel</button>
        <button
          className="reload-btn"
          onClick={handleSave}
          disabled={saving || !alias.trim()}
          style={{ fontWeight: 600 }}
        >
          {saving ? 'Saving...' : 'Save Automation'}
        </button>
      </div>
    </div>
  );
}
