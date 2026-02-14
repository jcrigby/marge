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

export default function IntegrationManager() {
  const [integrations, setIntegrations] = useState<IntegrationSummary[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [zigbee, setZigbee] = useState<ZigbeeDetail | null>(null);
  const [zwave, setZwave] = useState<ZwaveDetail | null>(null);
  const [tasmota, setTasmota] = useState<TasmotaDetail | null>(null);
  const [esphome, setEsphome] = useState<EsphomeDetail | null>(null);
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
        }
      })
      .catch(() => {
        toastError(`Failed to load ${integrationId} details`);
      })
      .finally(() => setLoading(null));
  }, [expanded]);

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
