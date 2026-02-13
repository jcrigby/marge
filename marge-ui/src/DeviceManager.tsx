import { useEffect, useState, useCallback } from 'react';
import { toastSuccess, toastError } from './Toast';

interface DeviceInfo {
  device_id: string;
  name: string;
  manufacturer: string;
  model: string;
  area_id: string;
  entity_count: number;
  entities: string[];
}

export default function DeviceManager({ allEntityIds }: { allEntityIds: string[] }) {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newDevice, setNewDevice] = useState({ device_id: '', name: '', manufacturer: '', model: '', area_id: '' });
  const [assignDeviceId, setAssignDeviceId] = useState<string | null>(null);
  const [assignEntityId, setAssignEntityId] = useState('');

  const fetchDevices = useCallback(() => {
    fetch('/api/devices')
      .then((r) => r.json())
      .then(setDevices)
      .catch(() => setDevices([]));
  }, []);

  useEffect(() => {
    fetchDevices();
    const id = setInterval(fetchDevices, 5000);
    return () => clearInterval(id);
  }, [fetchDevices]);

  const createDevice = () => {
    if (!newDevice.device_id.trim() || !newDevice.name.trim()) return;
    fetch('/api/devices', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: newDevice.device_id.trim(),
        name: newDevice.name.trim(),
        manufacturer: newDevice.manufacturer.trim(),
        model: newDevice.model.trim(),
        area_id: newDevice.area_id.trim(),
      }),
    })
      .then((r) => {
        if (r.ok) {
          toastSuccess(`Device "${newDevice.name}" created`);
          setNewDevice({ device_id: '', name: '', manufacturer: '', model: '', area_id: '' });
          setShowCreate(false);
          setTimeout(fetchDevices, 300);
        } else {
          toastError('Failed to create device');
        }
      })
      .catch(() => toastError('Failed to create device'));
  };

  const deleteDevice = (device: DeviceInfo) => {
    fetch(`/api/devices/${device.device_id}`, { method: 'DELETE' })
      .then((r) => {
        if (r.ok) {
          toastSuccess(`Device "${device.name}" deleted`);
          setTimeout(fetchDevices, 300);
        } else {
          toastError('Failed to delete device');
        }
      });
  };

  const assignEntity = (deviceId: string) => {
    if (!assignEntityId.trim()) return;
    fetch(`/api/devices/${deviceId}/entities/${assignEntityId.trim()}`, { method: 'POST' })
      .then((r) => {
        if (r.ok) {
          toastSuccess(`Entity assigned to device`);
          setAssignDeviceId(null);
          setAssignEntityId('');
          setTimeout(fetchDevices, 300);
        } else {
          toastError('Failed to assign entity');
        }
      });
  };

  // Entities not assigned to any device (for suggestion)
  const assignedEntities = new Set(devices.flatMap((d) => d.entities));
  const unassignedEntities = allEntityIds.filter((eid) => !assignedEntities.has(eid));

  return (
    <div className="device-manager">
      <div className="automation-header">
        <h2 className="domain-title">
          Devices
          <span className="domain-count">{devices.length}</span>
        </h2>
        <button className="reload-btn" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : 'Add Device'}
        </button>
      </div>

      {showCreate && (
        <div className="device-create-form">
          <div className="device-form-grid">
            <input
              type="text"
              className="area-input"
              placeholder="Device ID (e.g., hue_bridge_01)"
              value={newDevice.device_id}
              onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
            />
            <input
              type="text"
              className="area-input"
              placeholder="Name"
              value={newDevice.name}
              onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
            />
            <input
              type="text"
              className="area-input"
              placeholder="Manufacturer (optional)"
              value={newDevice.manufacturer}
              onChange={(e) => setNewDevice({ ...newDevice, manufacturer: e.target.value })}
            />
            <input
              type="text"
              className="area-input"
              placeholder="Model (optional)"
              value={newDevice.model}
              onChange={(e) => setNewDevice({ ...newDevice, model: e.target.value })}
            />
            <input
              type="text"
              className="area-input"
              placeholder="Area ID (optional)"
              value={newDevice.area_id}
              onChange={(e) => setNewDevice({ ...newDevice, area_id: e.target.value })}
            />
          </div>
          <button className="reload-btn" onClick={createDevice}>Create Device</button>
        </div>
      )}

      {devices.length === 0 && !showCreate ? (
        <div className="empty-state">No devices registered. Add one above.</div>
      ) : (
        <div className="device-grid">
          {devices.map((dev) => (
            <div key={dev.device_id} className="card device-card">
              <div className="card-header">
                <span className="card-name">{dev.name}</span>
                <span className="domain-count">{dev.entity_count}</span>
              </div>
              <div className="device-meta">
                {dev.manufacturer && <span className="device-tag">{dev.manufacturer}</span>}
                {dev.model && <span className="device-tag">{dev.model}</span>}
                {dev.area_id && <span className="device-tag area-tag">{dev.area_id}</span>}
              </div>
              <div className="auto-id">{dev.device_id}</div>

              {dev.entities.length > 0 && (
                <div className="area-entities">
                  {dev.entities.map((eid) => (
                    <span key={eid} className="chip">{eid}</span>
                  ))}
                </div>
              )}

              <div className="device-actions">
                {assignDeviceId === dev.device_id ? (
                  <div className="device-assign-row">
                    <input
                      type="text"
                      className="area-input"
                      placeholder="Entity ID to assign..."
                      value={assignEntityId}
                      onChange={(e) => setAssignEntityId(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && assignEntity(dev.device_id)}
                      list={`unassigned-${dev.device_id}`}
                    />
                    <datalist id={`unassigned-${dev.device_id}`}>
                      {unassignedEntities.slice(0, 50).map((eid) => (
                        <option key={eid} value={eid} />
                      ))}
                    </datalist>
                    <button className="reload-btn" onClick={() => assignEntity(dev.device_id)}>Assign</button>
                    <button className="reload-btn" onClick={() => { setAssignDeviceId(null); setAssignEntityId(''); }}>Cancel</button>
                  </div>
                ) : (
                  <>
                    <button className="reload-btn" onClick={() => setAssignDeviceId(dev.device_id)}>
                      Assign Entity
                    </button>
                    <button className="reload-btn" onClick={() => deleteDevice(dev)}>Delete</button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
