import { useEffect, useState, useCallback } from 'react';
import { toastError } from './Toast';

interface AreaInfo {
  area_id: string;
  name: string;
  entity_count: number;
  entities: string[];
}

export default function AreaManager({ allEntityIds }: { allEntityIds: string[] }) {
  const [areas, setAreas] = useState<AreaInfo[]>([]);
  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');

  const fetchAreas = useCallback(() => {
    fetch('/api/areas')
      .then((r) => r.json())
      .then(setAreas)
      .catch(() => setAreas([]));
  }, []);

  useEffect(() => {
    fetchAreas();
    const id = setInterval(fetchAreas, 5000);
    return () => clearInterval(id);
  }, [fetchAreas]);

  const createArea = () => {
    if (!newId.trim() || !newName.trim()) return;
    fetch('/api/areas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ area_id: newId.trim(), name: newName.trim() }),
    }).then((r) => {
      if (!r.ok) throw new Error(`${r.status}`);
      setNewId('');
      setNewName('');
      setTimeout(fetchAreas, 300);
    }).catch(() => toastError('Failed to create area'));
  };

  const deleteArea = (areaId: string) => {
    fetch(`/api/areas/${areaId}`, { method: 'DELETE' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchAreas, 300); })
      .catch(() => toastError('Failed to delete area'));
  };

  const assignEntity = (areaId: string, entityId: string) => {
    fetch(`/api/areas/${areaId}/entities/${entityId}`, { method: 'POST' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchAreas, 300); })
      .catch(() => toastError('Failed to assign entity'));
  };

  const unassignEntity = (areaId: string, entityId: string) => {
    fetch(`/api/areas/${areaId}/entities/${entityId}`, { method: 'DELETE' })
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); setTimeout(fetchAreas, 300); })
      .catch(() => toastError('Failed to unassign entity'));
  };

  return (
    <div className="area-manager">
      <h2 className="domain-title">
        Areas
        <span className="domain-count">{areas.length}</span>
      </h2>

      <div className="area-create">
        <input
          type="text"
          placeholder="Area ID (e.g., living_room)"
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
          onKeyDown={(e) => e.key === 'Enter' && createArea()}
        />
        <button className="reload-btn" onClick={createArea}>Create</button>
      </div>

      {areas.length === 0 ? (
        <div className="empty-state">No areas defined. Create one above.</div>
      ) : (
        <div className="area-grid">
          {areas.map((area) => (
            <div key={area.area_id} className="card area-card">
              <div className="card-header">
                <span className="card-name">{area.name}</span>
                <span className="domain-count">{area.entity_count}</span>
              </div>
              <div className="auto-id">{area.area_id}</div>
              {area.entities.length > 0 && (
                <div className="label-entities">
                  {area.entities.map((eid) => (
                    <span
                      key={eid}
                      className="chip label-entity-chip"
                      onClick={() => unassignEntity(area.area_id, eid)}
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
                      assignEntity(area.area_id, e.target.value);
                      e.target.value = '';
                    }
                  }}
                >
                  <option value="">Add entity...</option>
                  {allEntityIds
                    .filter((id) => !area.entities.includes(id))
                    .sort()
                    .map((id) => (
                      <option key={id} value={id}>{id}</option>
                    ))}
                </select>
              </div>
              <div className="card-actions">
                <button onClick={() => deleteArea(area.area_id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
