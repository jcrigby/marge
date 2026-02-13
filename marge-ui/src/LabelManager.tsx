import { useEffect, useState, useCallback } from 'react';
import { toastError } from './Toast';

interface LabelInfo {
  label_id: string;
  name: string;
  color: string;
  entity_count: number;
  entities: string[];
}

export default function LabelManager({ allEntityIds }: { allEntityIds: string[] }) {
  const [labels, setLabels] = useState<LabelInfo[]>([]);
  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');
  const [newColor, setNewColor] = useState('#6c8cff');

  const fetchLabels = useCallback(() => {
    fetch('/api/labels')
      .then((r) => r.json())
      .then(setLabels)
      .catch(() => setLabels([]));
  }, []);

  useEffect(() => {
    fetchLabels();
    const id = setInterval(fetchLabels, 5000);
    return () => clearInterval(id);
  }, [fetchLabels]);

  const createLabel = () => {
    if (!newId.trim() || !newName.trim()) return;
    fetch('/api/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label_id: newId.trim(), name: newName.trim(), color: newColor }),
    }).then((r) => {
      if (!r.ok) throw new Error(`${r.status}`);
      setNewId('');
      setNewName('');
      setNewColor('#6c8cff');
      setTimeout(fetchLabels, 300);
    }).catch(() => toastError('Failed to create label'));
  };

  const deleteLabel = (labelId: string) => {
    fetch(`/api/labels/${labelId}`, { method: 'DELETE' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchLabels, 300); })
      .catch(() => toastError('Failed to delete label'));
  };

  const assignEntity = (labelId: string, entityId: string) => {
    fetch(`/api/labels/${labelId}/entities/${entityId}`, { method: 'POST' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchLabels, 300); })
      .catch(() => toastError('Failed to assign entity'));
  };

  const unassignEntity = (labelId: string, entityId: string) => {
    fetch(`/api/labels/${labelId}/entities/${entityId}`, { method: 'DELETE' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchLabels, 300); })
      .catch(() => toastError('Failed to unassign entity'));
  };

  // Entities not assigned to any label
  const assignedIds = new Set(labels.flatMap((l) => l.entities));
  const unassigned = allEntityIds.filter((id) => !assignedIds.has(id));

  return (
    <div className="label-manager">
      <h2 className="domain-title">
        Labels
        <span className="domain-count">{labels.length}</span>
      </h2>

      <div className="label-create">
        <input
          type="text"
          placeholder="Label ID (e.g., critical)"
          value={newId}
          onChange={(e) => setNewId(e.target.value)}
          className="area-input"
        />
        <input
          type="text"
          placeholder="Display Name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="area-input"
          onKeyDown={(e) => e.key === 'Enter' && createLabel()}
        />
        <input
          type="color"
          value={newColor}
          onChange={(e) => setNewColor(e.target.value)}
          className="label-color-picker"
          title="Label color"
        />
        <button className="reload-btn" onClick={createLabel}>Create</button>
      </div>

      {labels.length === 0 ? (
        <div className="empty-state">No labels defined. Create one above.</div>
      ) : (
        <div className="label-grid">
          {labels.map((label) => (
            <div key={label.label_id} className="card label-card">
              <div className="card-header">
                <span
                  className="label-dot"
                  style={{ background: label.color || 'var(--accent)' }}
                />
                <span className="card-name">{label.name}</span>
                <span className="domain-count">{label.entity_count}</span>
              </div>
              <div className="auto-id">{label.label_id}</div>
              {label.entities.length > 0 && (
                <div className="label-entities">
                  {label.entities.map((eid) => (
                    <span
                      key={eid}
                      className="chip label-entity-chip"
                      onClick={() => unassignEntity(label.label_id, eid)}
                      title="Click to remove"
                    >
                      {eid.split('.')[1]?.replace(/_/g, ' ')} &times;
                    </span>
                  ))}
                </div>
              )}
              <div className="label-assign-row">
                <select
                  className="area-input"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      assignEntity(label.label_id, e.target.value);
                      e.target.value = '';
                    }
                  }}
                >
                  <option value="">Add entity...</option>
                  {unassigned
                    .concat(allEntityIds.filter((id) => !label.entities.includes(id) && assignedIds.has(id)))
                    .sort()
                    .filter((id) => !label.entities.includes(id))
                    .map((id) => (
                      <option key={id} value={id}>{id}</option>
                    ))}
                </select>
              </div>
              <div className="card-actions">
                <button onClick={() => deleteLabel(label.label_id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
