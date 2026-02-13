import type { EntityState } from './types';
import { getDomain, getEntityName } from './types';
import { callService } from './ws';
import Sparkline from './Sparkline';

const DOMAIN_ICONS: Record<string, string> = {
  light: '\u{1F4A1}',
  switch: '\u{1F50C}',
  sensor: '\u{1F321}',
  binary_sensor: '\u{1F534}',
  climate: '\u{2744}',
  cover: '\u{1FA9F}',
  lock: '\u{1F512}',
  fan: '\u{1F32C}',
  alarm_control_panel: '\u{1F6A8}',
  automation: '\u{2699}',
  scene: '\u{1F3AC}',
  input_boolean: '\u{2611}',
  input_number: '\u{1F522}',
  input_select: '\u{1F4CB}',
  input_text: '\u{1F4DD}',
};

function domainIcon(domain: string): string {
  return DOMAIN_ICONS[domain] || '\u{1F4E6}';
}

// Toggle-style card for lights and switches
function ToggleCard({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);
  const isOn = entity.state === 'on';
  const brightness = entity.attributes.brightness as number | undefined;

  const toggle = () => {
    callService(domain, isOn ? 'turn_off' : 'turn_on', entity.entity_id);
  };

  const setBrightness = (val: number) => {
    callService(domain, 'turn_on', entity.entity_id, { brightness: val });
  };

  return (
    <div className={`card card-toggle ${isOn ? 'is-on' : 'is-off'}`}>
      <div className="card-header" onClick={toggle}>
        <span className="card-icon">{domainIcon(domain)}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className={`card-state ${isOn ? 'state-on' : 'state-off'}`}>
          {entity.state}
        </span>
      </div>
      {domain === 'light' && brightness !== undefined && isOn && (
        <div className="card-slider">
          <input
            type="range"
            min={0}
            max={255}
            value={brightness}
            onChange={(e) => setBrightness(Number(e.target.value))}
          />
          <span className="slider-label">{Math.round((brightness / 255) * 100)}%</span>
        </div>
      )}
    </div>
  );
}

// Sensor display card
function SensorCard({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);
  const unit = (entity.attributes.unit_of_measurement as string) || '';
  const deviceClass = (entity.attributes.device_class as string) || '';
  const isNumeric = !isNaN(parseFloat(entity.state));

  return (
    <div className="card card-sensor">
      <div className="card-header">
        <span className="card-icon">{domainIcon(domain)}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
      </div>
      <div className="card-value">
        <span className="value-number">{entity.state}</span>
        {unit && <span className="value-unit">{unit}</span>}
      </div>
      {isNumeric && <Sparkline entityId={entity.entity_id} />}
      {deviceClass && <div className="card-meta">{deviceClass}</div>}
    </div>
  );
}

// Lock card
function LockCard({ entity }: { entity: EntityState }) {
  const isLocked = entity.state === 'locked';
  const toggle = () => {
    callService('lock', isLocked ? 'unlock' : 'lock', entity.entity_id);
  };

  return (
    <div className={`card card-lock ${isLocked ? 'is-locked' : 'is-unlocked'}`}>
      <div className="card-header" onClick={toggle}>
        <span className="card-icon">{isLocked ? '\u{1F512}' : '\u{1F513}'}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className="card-state">{entity.state}</span>
      </div>
    </div>
  );
}

// Cover card
function CoverCard({ entity }: { entity: EntityState }) {
  const isOpen = entity.state === 'open';
  return (
    <div className={`card card-cover ${isOpen ? 'is-open' : 'is-closed'}`}>
      <div className="card-header">
        <span className="card-icon">{domainIcon('cover')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className="card-state">{entity.state}</span>
      </div>
      <div className="card-actions">
        <button onClick={() => callService('cover', 'open_cover', entity.entity_id)}>Open</button>
        <button onClick={() => callService('cover', 'stop_cover', entity.entity_id)}>Stop</button>
        <button onClick={() => callService('cover', 'close_cover', entity.entity_id)}>Close</button>
      </div>
    </div>
  );
}

// Climate card
function ClimateCard({ entity }: { entity: EntityState }) {
  const temp = entity.attributes.temperature as number | undefined;
  const currentTemp = entity.attributes.current_temperature as number | undefined;
  const hvacMode = entity.state;

  return (
    <div className="card card-climate">
      <div className="card-header">
        <span className="card-icon">{domainIcon('climate')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className="card-state">{hvacMode}</span>
      </div>
      <div className="card-value">
        {currentTemp !== undefined && (
          <span className="value-number">{currentTemp}&deg;</span>
        )}
        {temp !== undefined && (
          <span className="value-target">target: {temp}&deg;</span>
        )}
      </div>
    </div>
  );
}

// Automation/scene card
function AutomationCard({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);
  const trigger = () => {
    if (domain === 'automation') {
      callService('automation', 'trigger', entity.entity_id);
    } else if (domain === 'scene') {
      callService('scene', 'turn_on', entity.entity_id);
    }
  };

  return (
    <div className="card card-automation">
      <div className="card-header" onClick={trigger}>
        <span className="card-icon">{domainIcon(domain)}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className="card-state">{entity.state}</span>
      </div>
    </div>
  );
}

// Generic fallback card
function GenericCard({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);
  return (
    <div className="card card-generic">
      <div className="card-header">
        <span className="card-icon">{domainIcon(domain)}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className="card-state">{entity.state}</span>
      </div>
    </div>
  );
}

export default function EntityCard({ entity }: { entity: EntityState }) {
  const domain = getDomain(entity.entity_id);

  switch (domain) {
    case 'light':
    case 'switch':
    case 'input_boolean':
      return <ToggleCard entity={entity} />;
    case 'sensor':
    case 'binary_sensor':
    case 'input_number':
      return <SensorCard entity={entity} />;
    case 'lock':
      return <LockCard entity={entity} />;
    case 'cover':
      return <CoverCard entity={entity} />;
    case 'climate':
      return <ClimateCard entity={entity} />;
    case 'automation':
    case 'scene':
      return <AutomationCard entity={entity} />;
    default:
      return <GenericCard entity={entity} />;
  }
}
