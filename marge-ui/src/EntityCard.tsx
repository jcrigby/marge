import { useState } from 'react';
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

// Climate card with interactive controls
function ClimateCard({ entity }: { entity: EntityState }) {
  const temp = entity.attributes.temperature as number | undefined;
  const currentTemp = entity.attributes.current_temperature as number | undefined;
  const hvacMode = entity.state;
  const modes = (entity.attributes.hvac_modes as string[]) || ['off', 'heat', 'cool', 'auto'];

  const setTemp = (delta: number) => {
    const target = (temp || 20) + delta;
    callService('climate', 'set_temperature', entity.entity_id, { temperature: target });
  };

  const setMode = (mode: string) => {
    callService('climate', 'set_hvac_mode', entity.entity_id, { hvac_mode: mode });
  };

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
      <div className="card-actions">
        <button onClick={() => setTemp(-0.5)}>-</button>
        <button onClick={() => setTemp(+0.5)}>+</button>
      </div>
      <div className="card-mode-select">
        {modes.map((m) => (
          <button
            key={m}
            className={`mode-btn ${m === hvacMode ? 'active' : ''}`}
            onClick={() => setMode(m)}
          >
            {m}
          </button>
        ))}
      </div>
    </div>
  );
}

// Fan card with speed control
function FanCard({ entity }: { entity: EntityState }) {
  const isOn = entity.state === 'on';
  const percentage = entity.attributes.percentage as number | undefined;

  const toggle = () => {
    callService('fan', isOn ? 'turn_off' : 'turn_on', entity.entity_id);
  };

  const setSpeed = (val: number) => {
    callService('fan', 'set_percentage', entity.entity_id, { percentage: val });
  };

  return (
    <div className={`card card-fan ${isOn ? 'is-on' : 'is-off'}`}>
      <div className="card-header" onClick={toggle}>
        <span className="card-icon">{domainIcon('fan')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
        <span className={`card-state ${isOn ? 'state-on' : 'state-off'}`}>
          {entity.state}
        </span>
      </div>
      {isOn && (
        <div className="card-slider">
          <input
            type="range"
            min={0}
            max={100}
            value={percentage ?? 0}
            onChange={(e) => setSpeed(Number(e.target.value))}
          />
          <span className="slider-label">{percentage ?? 0}%</span>
        </div>
      )}
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

// Input number card with slider
function InputNumberCard({ entity }: { entity: EntityState }) {
  const min = (entity.attributes.min as number) ?? 0;
  const max = (entity.attributes.max as number) ?? 100;
  const step = (entity.attributes.step as number) ?? 1;
  const unit = (entity.attributes.unit_of_measurement as string) || '';
  const val = parseFloat(entity.state) || 0;

  const setValue = (v: number) => {
    callService('input_number', 'set_value', entity.entity_id, { value: v });
  };

  return (
    <div className="card card-input-number">
      <div className="card-header">
        <span className="card-icon">{domainIcon('input_number')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
      </div>
      <div className="card-value">
        <span className="value-number">{entity.state}</span>
        {unit && <span className="value-unit">{unit}</span>}
      </div>
      <div className="card-slider">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={val}
          onChange={(e) => setValue(Number(e.target.value))}
        />
        <span className="slider-label">{val}</span>
      </div>
    </div>
  );
}

// Input select card with dropdown
function InputSelectCard({ entity }: { entity: EntityState }) {
  const options = (entity.attributes.options as string[]) || [];

  const selectOption = (option: string) => {
    callService('input_select', 'select_option', entity.entity_id, { option });
  };

  return (
    <div className="card card-input-select">
      <div className="card-header">
        <span className="card-icon">{domainIcon('input_select')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
      </div>
      <div className="card-select-wrap">
        <select
          value={entity.state}
          onChange={(e) => selectOption(e.target.value)}
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

// Input text card with text field
function InputTextCard({ entity }: { entity: EntityState }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entity.state);

  const submit = () => {
    callService('input_text', 'set_value', entity.entity_id, { value: draft });
    setEditing(false);
  };

  return (
    <div className="card card-input-text">
      <div className="card-header">
        <span className="card-icon">{domainIcon('input_text')}</span>
        <span className="card-name">{getEntityName(entity.entity_id)}</span>
      </div>
      {editing ? (
        <div className="card-text-input">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            onBlur={submit}
            autoFocus
          />
        </div>
      ) : (
        <div
          className="card-text-display"
          onClick={() => { setDraft(entity.state); setEditing(true); }}
        >
          {entity.state || '\u00A0'}
        </div>
      )}
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
      return <SensorCard entity={entity} />;
    case 'input_number':
      return <InputNumberCard entity={entity} />;
    case 'input_select':
      return <InputSelectCard entity={entity} />;
    case 'input_text':
      return <InputTextCard entity={entity} />;
    case 'lock':
      return <LockCard entity={entity} />;
    case 'cover':
      return <CoverCard entity={entity} />;
    case 'climate':
      return <ClimateCard entity={entity} />;
    case 'fan':
      return <FanCard entity={entity} />;
    case 'automation':
    case 'scene':
      return <AutomationCard entity={entity} />;
    default:
      return <GenericCard entity={entity} />;
  }
}
