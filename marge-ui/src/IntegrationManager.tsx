import { useEffect, useState, useCallback } from 'react';
import { toastSuccess, toastError } from './Toast';

interface IntegrationSummary {
  id: string;
  name: string;
  status: string;
  device_count: number;
}

interface ZigbeeDevice {
  friendly_name: string;
  ieee_address: string;
  manufacturer: string;
  model_id: string;
  power_source: string;
  supported: boolean;
}

interface ZigbeeDetail {
  bridge_state: string;
  device_count: number;
  devices: ZigbeeDevice[];
  permit_join: boolean;
}

interface ZwaveNode {
  id: number;
  name: string;
  manufacturer: string;
  product_label: string;
  status: string;
  ready: boolean;
}

interface ZwaveDetail {
  connected: boolean;
  node_count: number;
  nodes: ZwaveNode[];
}

interface TasmotaDevice {
  topic_name: string;
  friendly_name: string;
  module: string;
  firmware_version: string;
  ip_address: string;
  online: boolean;
}

interface TasmotaDetail {
  device_count: number;
  devices: TasmotaDevice[];
}

interface EsphomeDevice {
  prefix: string;
  name: string;
  ip_address: string;
  online: boolean;
  component_count: number;
}

interface EsphomeDetail {
  device_count: number;
  devices: EsphomeDevice[];
}

interface ShellyDevice {
  ip: string;
  mac: string;
  device_type: string;
  name: string | null;
  gen: number;
  firmware: string | null;
  online: boolean;
  last_seen: string | null;
}

interface ShellyDetail {
  device_count: number;
  devices: ShellyDevice[];
}

interface HueBridgeInfo {
  ip: string;
  username: string;
  name: string;
  model_id: string;
  sw_version: string;
  online: boolean;
  light_count: number;
  sensor_count: number;
  last_polled: string | null;
}

interface HueDetail {
  bridge_count: number;
  device_count: number;
  bridges: HueBridgeInfo[];
}

interface CastDeviceInfo {
  ip: string;
  name: string;
  model_name: string;
  mac: string;
  firmware: string;
  uuid: string;
  online: boolean;
  last_seen: string | null;
}

interface CastDetail {
  device_count: number;
  devices: CastDeviceInfo[];
}

interface SonosDeviceInfo {
  ip: string;
  name: string;
  model: string;
  serial: string;
  software_version: string;
  uuid: string;
  zone_name: string;
  online: boolean;
  last_seen: string | null;
  is_coordinator: boolean;
  volume_level: number;
  is_volume_muted: boolean;
  source: string;
}

interface SonosDetail {
  device_count: number;
  devices: SonosDeviceInfo[];
}

interface MatterDeviceInfo {
  node_id: number;
  name: string;
  vendor_name: string;
  product_name: string;
  device_type: string;
  online: boolean;
}

interface MatterDetail {
  status: string;
  device_count: number;
  devices: MatterDeviceInfo[];
  server_version: string | null;
}

function StatusDot({ online }: { online: boolean }) {
  return (
    <span
      className={`integration-dot ${online ? 'dot-online' : 'dot-offline'}`}
      title={online ? 'Online' : 'Offline'}
    />
  );
}

function ZigbeeView({ detail, onPermitJoin }: { detail: ZigbeeDetail; onPermitJoin: (enable: boolean) => void }) {
  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className={`integration-badge ${detail.bridge_state === 'online' ? 'badge-online' : 'badge-offline'}`}>
          Bridge: {detail.bridge_state}
        </span>
        <button
          className={`integration-badge ${detail.permit_join ? 'badge-active' : 'badge-inactive'}`}
          onClick={() => onPermitJoin(!detail.permit_join)}
          title={detail.permit_join ? 'Disable permit join' : 'Enable permit join (120s)'}
        >
          Permit Join: {detail.permit_join ? 'ON' : 'OFF'}
        </button>
      </div>
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>IEEE Address</th>
                <th>Manufacturer</th>
                <th>Model</th>
                <th>Power</th>
                <th>Supported</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.ieee_address}>
                  <td className="int-device-name">{d.friendly_name}</td>
                  <td className="int-device-addr">{d.ieee_address}</td>
                  <td>{d.manufacturer}</td>
                  <td>{d.model_id}</td>
                  <td>{d.power_source}</td>
                  <td className="int-device-check">{d.supported ? '\u2713' : '\u2717'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ZwaveView({ detail }: { detail: ZwaveDetail }) {
  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className={`integration-badge ${detail.connected ? 'badge-online' : 'badge-offline'}`}>
          {detail.connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>
      {detail.nodes.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Manufacturer</th>
                <th>Product</th>
                <th>Status</th>
                <th>Ready</th>
              </tr>
            </thead>
            <tbody>
              {detail.nodes.map((n) => (
                <tr key={n.id}>
                  <td className="int-device-id">{n.id}</td>
                  <td className="int-device-name">{n.name}</td>
                  <td>{n.manufacturer}</td>
                  <td>{n.product_label}</td>
                  <td>{n.status}</td>
                  <td className="int-device-check">{n.ready ? '\u2713' : '\u2717'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TasmotaView({ detail }: { detail: TasmotaDetail }) {
  return (
    <div className="integration-detail">
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Name</th>
                <th>Module</th>
                <th>Firmware</th>
                <th>IP Address</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.topic_name}>
                  <td className="int-device-addr">{d.topic_name}</td>
                  <td className="int-device-name">{d.friendly_name}</td>
                  <td>{d.module}</td>
                  <td>{d.firmware_version}</td>
                  <td className="int-device-addr">{d.ip_address}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
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

function EsphomeView({ detail }: { detail: EsphomeDetail }) {
  return (
    <div className="integration-detail">
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Prefix</th>
                <th>Name</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Components</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.prefix}>
                  <td className="int-device-addr">{d.prefix}</td>
                  <td className="int-device-name">{d.name}</td>
                  <td className="int-device-addr">{d.ip_address}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
                  </td>
                  <td className="int-device-id">{d.component_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ShellyView({ detail, onDiscover }: { detail: ShellyDetail; onDiscover: (ip: string) => void }) {
  const [ip, setIp] = useState('');

  const handleAdd = () => {
    const trimmed = ip.trim();
    if (trimmed) {
      onDiscover(trimmed);
      setIp('');
    }
  };

  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className="integration-badge badge-inactive">
          {detail.device_count} device{detail.device_count !== 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0' }}>
        <input
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="IP address (e.g. 192.168.1.100)"
          style={{
            flex: 1,
            padding: '0.35rem 0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
            color: 'var(--fg)',
            fontSize: '0.85rem',
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button
          onClick={handleAdd}
          className="integration-badge badge-active"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          Add Device
        </button>
      </div>
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>IP</th>
                <th>MAC</th>
                <th>Name</th>
                <th>Type</th>
                <th>Gen</th>
                <th>Firmware</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.mac}>
                  <td className="int-device-addr">{d.ip}</td>
                  <td className="int-device-addr">{d.mac}</td>
                  <td className="int-device-name">{d.name || '-'}</td>
                  <td>{d.device_type}</td>
                  <td className="int-device-id">{d.gen}</td>
                  <td>{d.firmware || '-'}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
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

function HueView({ detail, onPair, onAdd }: {
  detail: HueDetail;
  onPair: (ip: string) => void;
  onAdd: (ip: string, username: string) => void;
}) {
  const [ip, setIp] = useState('');
  const [username, setUsername] = useState('');
  const [mode, setMode] = useState<'pair' | 'add'>('pair');

  const handlePair = () => {
    const trimmed = ip.trim();
    if (trimmed) {
      onPair(trimmed);
      setIp('');
    }
  };

  const handleAdd = () => {
    const trimmedIp = ip.trim();
    const trimmedUser = username.trim();
    if (trimmedIp && trimmedUser) {
      onAdd(trimmedIp, trimmedUser);
      setIp('');
      setUsername('');
    }
  };

  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className="integration-badge badge-inactive">
          {detail.bridge_count} bridge{detail.bridge_count !== 1 ? 's' : ''}
        </span>
        <span className="integration-badge badge-inactive">
          {detail.device_count} device{detail.device_count !== 1 ? 's' : ''}
        </span>
        <button
          className={`integration-badge ${mode === 'pair' ? 'badge-active' : 'badge-inactive'}`}
          onClick={() => setMode(mode === 'pair' ? 'add' : 'pair')}
          style={{ cursor: 'pointer' }}
        >
          Mode: {mode === 'pair' ? 'Pair (Link Button)' : 'Add (Pre-paired)'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0', flexWrap: 'wrap' }}>
        <input
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="Bridge IP (e.g. 192.168.1.50)"
          style={{
            flex: 1,
            minWidth: '10rem',
            padding: '0.35rem 0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
            color: 'var(--fg)',
            fontSize: '0.85rem',
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') mode === 'pair' ? handlePair() : handleAdd(); }}
        />
        {mode === 'add' && (
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username / API key"
            style={{
              flex: 1,
              minWidth: '10rem',
              padding: '0.35rem 0.5rem',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              background: 'var(--bg)',
              color: 'var(--fg)',
              fontSize: '0.85rem',
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
          />
        )}
        <button
          onClick={mode === 'pair' ? handlePair : handleAdd}
          className="integration-badge badge-active"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          {mode === 'pair' ? 'Pair Bridge' : 'Add Bridge'}
        </button>
      </div>
      {mode === 'pair' && (
        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
          Press the link button on your Hue Bridge, then click "Pair Bridge".
        </div>
      )}
      {detail.bridges.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>IP</th>
                <th>Model</th>
                <th>Firmware</th>
                <th>Lights</th>
                <th>Sensors</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.bridges.map((b) => (
                <tr key={b.ip}>
                  <td className="int-device-name">{b.name}</td>
                  <td className="int-device-addr">{b.ip}</td>
                  <td>{b.model_id}</td>
                  <td>{b.sw_version}</td>
                  <td className="int-device-id">{b.light_count}</td>
                  <td className="int-device-id">{b.sensor_count}</td>
                  <td>
                    <StatusDot online={b.online} />
                    <span className="int-status-label">{b.online ? 'Online' : 'Offline'}</span>
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

function CastView({ detail, onDiscover }: { detail: CastDetail; onDiscover: (ip: string) => void }) {
  const [ip, setIp] = useState('');

  const handleAdd = () => {
    const trimmed = ip.trim();
    if (trimmed) {
      onDiscover(trimmed);
      setIp('');
    }
  };

  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className="integration-badge badge-inactive">
          {detail.device_count} device{detail.device_count !== 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0' }}>
        <input
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="Cast device IP (e.g. 192.168.1.200)"
          style={{
            flex: 1,
            padding: '0.35rem 0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
            color: 'var(--fg)',
            fontSize: '0.85rem',
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button
          onClick={handleAdd}
          className="integration-badge badge-active"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          Add Device
        </button>
      </div>
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Model</th>
                <th>IP</th>
                <th>MAC</th>
                <th>Firmware</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.uuid}>
                  <td className="int-device-name">{d.name}</td>
                  <td>{d.model_name}</td>
                  <td className="int-device-addr">{d.ip}</td>
                  <td className="int-device-addr">{d.mac}</td>
                  <td>{d.firmware}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
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

function SonosView({ detail, onDiscover }: { detail: SonosDetail; onDiscover: (ip: string) => void }) {
  const [ip, setIp] = useState('');

  const handleAdd = () => {
    const trimmed = ip.trim();
    if (trimmed) {
      onDiscover(trimmed);
      setIp('');
    }
  };

  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className="integration-badge badge-inactive">
          {detail.device_count} device{detail.device_count !== 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0' }}>
        <input
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="Sonos IP (e.g. 192.168.1.80)"
          style={{
            flex: 1,
            padding: '0.35rem 0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
            color: 'var(--fg)',
            fontSize: '0.85rem',
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button
          onClick={handleAdd}
          className="integration-badge badge-active"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          Add Speaker
        </button>
      </div>
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Zone</th>
                <th>Model</th>
                <th>IP</th>
                <th>Software</th>
                <th>Coordinator</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.uuid}>
                  <td className="int-device-name">{d.zone_name}</td>
                  <td>{d.model}</td>
                  <td className="int-device-addr">{d.ip}</td>
                  <td>{d.software_version}</td>
                  <td className="int-device-check">{d.is_coordinator ? '\u2713' : '\u2717'}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
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

function MatterView({ detail }: { detail: MatterDetail }) {
  return (
    <div className="integration-detail">
      <div className="integration-badges">
        <span className={`integration-badge ${detail.status === 'connected' ? 'badge-active' : 'badge-inactive'}`}>
          {detail.status}
        </span>
        <span className="integration-badge badge-inactive">
          {detail.device_count} device{detail.device_count !== 1 ? 's' : ''}
        </span>
        {detail.server_version && (
          <span className="integration-badge badge-inactive">
            v{detail.server_version}
          </span>
        )}
      </div>
      {detail.devices.length > 0 && (
        <div className="integration-table-wrap">
          <table className="integration-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Vendor</th>
                <th>Product</th>
                <th>Node</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.devices.map((d) => (
                <tr key={d.node_id}>
                  <td className="int-device-name">{d.name}</td>
                  <td>{d.device_type}</td>
                  <td>{d.vendor_name}</td>
                  <td>{d.product_name}</td>
                  <td>{d.node_id}</td>
                  <td>
                    <StatusDot online={d.online} />
                    <span className="int-status-label">{d.online ? 'Online' : 'Offline'}</span>
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

export default function IntegrationManager() {
  const [integrations, setIntegrations] = useState<IntegrationSummary[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [zigbee, setZigbee] = useState<ZigbeeDetail | null>(null);
  const [zwave, setZwave] = useState<ZwaveDetail | null>(null);
  const [tasmota, setTasmota] = useState<TasmotaDetail | null>(null);
  const [esphome, setEsphome] = useState<EsphomeDetail | null>(null);
  const [shellyDetail, setShellyDetail] = useState<ShellyDetail | null>(null);
  const [hueDetail, setHueDetail] = useState<HueDetail | null>(null);
  const [castDetail, setCastDetail] = useState<CastDetail | null>(null);
  const [sonosDetail, setSonosDetail] = useState<SonosDetail | null>(null);
  const [matterDetail, setMatterDetail] = useState<MatterDetail | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const fetchIntegrations = useCallback(() => {
    fetch('/api/integrations')
      .then((r) => r.json())
      .then(setIntegrations)
      .catch(() => setIntegrations([]));
  }, []);

  useEffect(() => {
    fetchIntegrations();
    const id = setInterval(fetchIntegrations, 5000);
    return () => clearInterval(id);
  }, [fetchIntegrations]);

  const toggleExpand = useCallback((integrationId: string) => {
    if (expanded === integrationId) {
      setExpanded(null);
      return;
    }
    setExpanded(integrationId);
    setLoading(integrationId);

    fetch(`/api/integrations/${integrationId}`)
      .then((r) => r.json())
      .then((data) => {
        switch (integrationId) {
          case 'zigbee2mqtt':
            setZigbee(data);
            break;
          case 'zwave':
            setZwave(data);
            break;
          case 'tasmota':
            setTasmota(data);
            break;
          case 'esphome':
            setEsphome(data);
            break;
          case 'shelly':
            setShellyDetail(data);
            break;
          case 'hue':
            setHueDetail(data);
            break;
          case 'cast':
            setCastDetail(data);
            break;
          case 'sonos':
            setSonosDetail(data);
            break;
          case 'matter':
            setMatterDetail(data);
            break;
        }
      })
      .catch(() => {
        toastError(`Failed to load ${integrationId} details`);
      })
      .finally(() => setLoading(null));
  }, [expanded]);

  const handleShellyDiscover = useCallback((ip: string) => {
    fetch('/api/integrations/shelly/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Shelly device discovered: ${data.device?.device_type || ip}`);
          // Refresh detail
          return fetch('/api/integrations/shelly').then((r2) => r2.json()).then(setShellyDetail);
        } else {
          toastError(`Discovery failed: ${data.message || 'Unknown error'}`);
        }
      })
      .catch(() => toastError('Failed to discover Shelly device'));
  }, []);

  const handleCastDiscover = useCallback((ip: string) => {
    fetch('/api/integrations/cast/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Cast device discovered: ${data.device?.name || ip}`);
          return fetch('/api/integrations/cast').then((r2) => r2.json()).then(setCastDetail);
        } else {
          toastError(`Discovery failed: ${data.message || 'Unknown error'}`);
        }
      })
      .catch(() => toastError('Failed to discover Cast device'));
  }, []);

  const handleSonosDiscover = useCallback((ip: string) => {
    fetch('/api/integrations/sonos/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Sonos speaker discovered: ${data.device?.zone_name || ip}`);
          return fetch('/api/integrations/sonos').then((r2) => r2.json()).then(setSonosDetail);
        } else {
          toastError(`Discovery failed: ${data.message || 'Unknown error'}`);
        }
      })
      .catch(() => toastError('Failed to discover Sonos speaker'));
  }, []);

  const handleHuePair = useCallback((ip: string) => {
    fetch('/api/integrations/hue/pair', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Hue bridge paired: ${data.bridge?.name || ip}`);
          return fetch('/api/integrations/hue').then((r2) => r2.json()).then(setHueDetail);
        } else if (data.result === 'partial') {
          toastSuccess(`Paired (username: ${data.username}) but config fetch failed`);
          return fetch('/api/integrations/hue').then((r2) => r2.json()).then(setHueDetail);
        } else {
          toastError(`Pairing failed: ${data.message || 'Unknown error'}`);
        }
      })
      .catch(() => toastError('Failed to pair Hue bridge'));
  }, []);

  const handleHueAdd = useCallback((ip: string, username: string) => {
    fetch('/api/integrations/hue/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip, username }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.result === 'ok') {
          toastSuccess(`Hue bridge added: ${data.bridge?.name || ip}`);
          return fetch('/api/integrations/hue').then((r2) => r2.json()).then(setHueDetail);
        } else {
          toastError(`Add bridge failed: ${data.message || 'Unknown error'}`);
        }
      })
      .catch(() => toastError('Failed to add Hue bridge'));
  }, []);

  const handlePermitJoin = useCallback((enable: boolean) => {
    fetch('/api/integrations/zigbee2mqtt/permit_join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enable, duration: 120 }),
    })
      .then((r) => {
        if (r.ok) {
          toastSuccess(enable ? 'Permit join enabled (120s)' : 'Permit join disabled');
          // Refresh detail
          return fetch('/api/integrations/zigbee2mqtt').then((r2) => r2.json()).then(setZigbee);
        } else {
          toastError('Failed to toggle permit join');
        }
      })
      .catch(() => toastError('Failed to toggle permit join'));
  }, []);

  return (
    <div className="integration-manager">
      <div className="automation-header">
        <h2 className="domain-title">
          Integrations
          <span className="domain-count">{integrations.length}</span>
        </h2>
      </div>

      {integrations.length === 0 ? (
        <div className="empty-state">No integrations found.</div>
      ) : (
        <div className="integration-grid">
          {integrations.map((int) => (
            <div key={int.id} className={`card integration-card ${expanded === int.id ? 'integration-expanded' : ''}`}>
              <div
                className="card-header integration-card-header"
                onClick={() => toggleExpand(int.id)}
              >
                <StatusDot online={int.status === 'online'} />
                <div className="card-name-block">
                  <span className="card-name">{int.name}</span>
                  <span className="card-entity-id">{int.id}</span>
                </div>
                <span className="domain-count">{int.device_count} devices</span>
                <span className="integration-chevron">
                  {expanded === int.id ? '\u25B2' : '\u25BC'}
                </span>
              </div>

              {expanded === int.id && (
                <div className="integration-devices">
                  {loading === int.id ? (
                    <div className="integration-loading">Loading...</div>
                  ) : (
                    <>
                      {int.id === 'zigbee2mqtt' && zigbee && (
                        <ZigbeeView detail={zigbee} onPermitJoin={handlePermitJoin} />
                      )}
                      {int.id === 'zwave' && zwave && (
                        <ZwaveView detail={zwave} />
                      )}
                      {int.id === 'tasmota' && tasmota && (
                        <TasmotaView detail={tasmota} />
                      )}
                      {int.id === 'esphome' && esphome && (
                        <EsphomeView detail={esphome} />
                      )}
                      {int.id === 'shelly' && shellyDetail && (
                        <ShellyView detail={shellyDetail} onDiscover={handleShellyDiscover} />
                      )}
                      {int.id === 'hue' && hueDetail && (
                        <HueView detail={hueDetail} onPair={handleHuePair} onAdd={handleHueAdd} />
                      )}
                      {int.id === 'cast' && castDetail && (
                        <CastView detail={castDetail} onDiscover={handleCastDiscover} />
                      )}
                      {int.id === 'sonos' && sonosDetail && (
                        <SonosView detail={sonosDetail} onDiscover={handleSonosDiscover} />
                      )}
                      {int.id === 'matter' && matterDetail && (
                        <MatterView detail={matterDetail} />
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
