# MARGE Ã¢â‚¬â€ System/Subsystem Specification (SSS)

**Document Number:** MRG-SSS-001  
**Version:** 0.1.0-DRAFT  
**Classification:** UNCLASSIFIED // FOUO (For Our Use Only)  
**Date:** 2026-02-11  
**Prepared For:** The Department of Not Running Python In Production  
**Prepared By:** Architecture Division, Marge Program Office  

---

## 0. PREFACE Ã¢â‚¬â€ "WHAT IF"

### The Problem Everyone Feels But Nobody Fixes

The world needs a smarthome platform that doesn't suck.

Home Assistant is *close*. Maddeningly close. A decade of passionate community effort has produced something remarkable: a system that integrates with over 2,000 devices and services, an automation engine that handles everything from "turn on the porch light at sunset" to byzantine HVAC scheduling, and a UI that Ã¢â‚¬â€ while not beautiful Ã¢â‚¬â€ is functional enough that normal humans can use it. The HA community has, through sheer collective stubbornness, reverse-engineered the functional requirements for what a smarthome platform needs to be. That knowledge is priceless.

But it's written in Python. And that sucks.

Not Python-the-language-for-scripts. Python-the-runtime-for-a-system-that-needs-to-respond-in-milliseconds-to-your-house-being-on-fire. The GIL. The memory footprint. The startup time that makes you watch a loading spinner while your thermostat forgets what temperature you wanted. The fact that a misbehaving integration for your novelty WiFi fish tank can deadlock the same event loop that controls your door locks. The dependency hell. The `asyncio` spaghetti. The 800MB memory baseline on a Raspberry Pi that should be running a house, not a Django project.

Every serious HA user has felt this. You're standing in your kitchen watching a light take 3 seconds to respond to a motion sensor and thinking: *this should not be this hard.*

### The Trap: "Let's Just Rewrite It"

The obvious reaction is: *let's rewrite Home Assistant in a real language.*

This is a trap.

A straight rewrite is how you spend three years building something that handles 12 integrations while HA adds 200 more. You're not just rewriting Python Ã¢â‚¬â€ you're rewriting a decade of edge-case discovery, protocol quirks, device-specific workarounds, and community knowledge baked into 2,000+ integration modules. You will never catch up. The Python is not the product. The *knowledge embedded in the Python* is the product.

### The Insight: Use HA as a Spec, Not a Codebase

So what if we don't rewrite it?

What if, instead, we treat Home Assistant as what it actually is: **the most comprehensive functional specification for a smarthome platform ever written.** Not by a product manager with a Confluence page, but by a million users filing issues, submitting PRs, and arguing about how thermostats should work.

Home Assistant tells us:

- **What entities need to exist** Ã¢â‚¬â€ 30+ domains, from lights to lawn mowers, each with carefully evolved state models, attributes, and device classes.
- **What automations need to do** Ã¢â‚¬â€ triggers, conditions, actions, templates, run modes, all refined by real users solving real problems.
- **What integrations need from a core platform** Ã¢â‚¬â€ and the answer is surprisingly simple. Most of the 2,000+ integrations follow about 5 patterns: poll an API, subscribe to events, normalize into entities, expose services.
- **What the API surface should look like** Ã¢â‚¬â€ REST, WebSocket, MQTT Discovery, all documented and battle-tested by thousands of third-party tools.
- **What the configuration language should be** Ã¢â‚¬â€ YAML automations that your non-technical spouse can almost read.

The play is: extract this decade of requirements discovery, then implement it in something that performs like a system controlling your physical environment should perform.

### Why Rust for the Core (and Not Go)

An earlier draft of this spec called for Go. It was a reasonable choice Ã¢â‚¬â€ fast compilation, great concurrency primitives, single binary deployment, and a lower learning curve for contributors.

Then someone who has spent 25 years building embedded systems pointed out the obvious: **Go in the cloud is a no-brainer. Go on an embedded device is something you've seen fail.**

Go still has a garbage collector. Go still has a runtime. Go still burns 30-40MB of RAM before you've written a line of application code. On a Raspberry Pi with 2GB of memory that's supposed to run your house Ã¢â‚¬â€ including your security system, your door locks, and your smoke detectors Ã¢â‚¬â€ that matters. When your smoke alarm triggers at 2 AM, the state machine that processes that event does not get to pause for garbage collection.

So the core Ã¢â‚¬â€ the state machine, the event bus, the automation engine, the thing that runs 24/7 on your SBC and must respond in microseconds Ã¢â‚¬â€ is written in Rust. No GC. No runtime. Predictable latency. A static binary under 20MB that starts in under 500ms.

But integrations? The plugin that polls your weather API every 15 minutes? The bridge to your Hue lights? Those can be written in Go, Python, TypeScript, or anything else that speaks gRPC or MQTT. They run as isolated processes. If the Go runtime's GC pauses while fetching your Spotify playlist, nobody cares Ã¢â‚¬â€ it can't touch the core.

This is the same architecture pattern that works in every serious embedded system: a hard real-time core with soft real-time peripherals.

### What This Document Is

This is the extraction of HA's decade of requirements discovery into a formal system specification Ã¢â‚¬â€ complete with protobuf schemas, interface contracts, and traceable requirements Ã¢â‚¬â€ for a clean-room reimplementation called **Marge**.

Its companion document, **MRG-CTS-001 (Conformance Test Suite Specification)**, is arguably more important. It defines ~1,200 black-box tests that validate correct behavior by talking to the SUT exclusively through its public APIs Ã¢â‚¬â€ REST, WebSocket, MQTT. Run the suite against HA-legacy: all green. Run it against Marge: all green. That's what "compatible" means. The narrative spec explains *why*. The test suite proves *whether*.

Marge is not a fork. It's not a port. It's a new system that speaks the same language as HA (literally Ã¢â‚¬â€ it parses your YAML, implements the same REST and WebSocket APIs, supports MQTT Discovery) but is built on fundamentally different foundations:

- **Rust core** Ã¢â‚¬â€ tokio async runtime, zero-cost abstractions, no GC, sub-100Ã‚Âµs state transitions, <15MB memory footprint.
- **MQTT as the backbone** Ã¢â‚¬â€ not a bolt-on integration, but the actual event bus. Your ESPHome devices are first-class citizens, not guests.
- **Integrations as isolated processes** Ã¢â‚¬â€ a crashed plugin can't take down your house. Each integration communicates via gRPC or MQTT with the core. Write them in Rust, Go, Python, or anything.
- **HA compatibility as a feature** Ã¢â‚¬â€ your `automations.yaml` works. Your MQTT devices auto-discover. Your API tools still connect. Migration is import, not rewrite.

And for the long tail of 2,000 HA integrations? A compatibility shim wraps existing Python integrations in a subprocess with a gRPC bridge. You get the ecosystem on day one while native integrations get written over time.

### Why "Marge"

Home Assistant Ã¢â€ ' Homer Ã¢â€ ' Marge. She's the one who actually keeps the household running while everyone else causes chaos. Which is literally what this software does.

There's a second reason. This project exists in the middle of what can only be described as an LLM agentic programming event Ã¢â‚¬" earthquake, tsunami, pick your natural disaster metaphor. A month ago, "Ralph loop" coding was the new hotness: put an LLM in a loop with your test suite, let it write code, run the tests, feed the errors back, iterate until green. Named after Ralph Wiggum from The Simpsons, because it's almost insultingly simple and it works anyway.

Marge is the next question: what happens when you give an LLM agent not just a test suite but a *complete formal specification* Ã¢â‚¬" SSS, conformance tests, theory of operations Ã¢â‚¬" and point it at a well-understood problem domain? The CTS is perfectly suited for this. It gives an objective pass/fail signal that doesn't care whether a human or an AI wrote the Rust. If the tests pass against HA-legacy and they pass against Marge, the implementation is correct. Period.

This project is exploring two things simultaneously: (1) can you build a production-grade HA workalike, and (2) can LLM-driven agentic coding do the heavy lifting when the specification is rigorous enough? The answer to the first question depends on the answer to the second, which is what makes it interesting.

### The Bet

The bet is simple: the hard part of building a smarthome platform is not the software engineering. It's figuring out what the software needs to do. HA already figured that out. We just need to build it like we mean it.

The second bet: anything that can be tested can be automated. Including the writing of the code that passes the tests.

---

## 1. SCOPE

### 1.1 Identification

This System/Subsystem Specification (SSS) establishes the requirements for the **Marge Home Automation Platform**, hereafter referred to as "Marge" or "the System." Marge is a high-performance, locally-hosted home automation system designed as a clean-room reimplementation of the functional requirements demonstrated by the Home Assistant (HA) open-source project, implemented with a Rust core engine and polyglot integration framework (Rust, Go, or any language via gRPC) with an MQTT-native backbone.

### 1.2 System Overview

Marge SHALL provide centralized monitoring, control, and automation of Internet of Things (IoT) devices within a residential or light-commercial environment. The system derives its functional specification from analysis of the Home Assistant project's 10+ years of community-driven requirements discovery, while implementing a fundamentally different technical architecture optimized for:

- **Performance**: Sub-100Ã‚Âµs state transitions, <15MB base memory footprint
- **Reliability**: No GC, no runtime overhead in the hot path, graceful degradation
- **Extensibility**: Strongly-typed integration SDK with compile-time guarantees
- **Migration**: YAML-compatible configuration layer enabling zero-friction HA migration

### 1.3 Document Overview

This specification is organized per MIL-STD-498 Ã‚Â§10.1 with modifications for sanity. Sections 3-4 define the system architecture and functional requirements. Section 5 defines interface requirements. Section 6 defines the integration framework. Section 7 defines non-functional requirements.

---

## 2. REFERENCED DOCUMENTS

| ID | Document | Relevance |
|---|---|---|
| MRG-CTS-001 | Marge Conformance Test Suite Specification | Executable specification Ã¢â‚¬â€ the actual acceptance criteria |
| MRG-OPS-001 | Marge Theory of Operations | Deployment, operations, failure recovery, migration, maintenance |
| HA-ARCH-CORE | [HA Core Architecture](https://github.com/home-assistant/developers.home-assistant/blob/master/docs/architecture/core.md) | Event Bus, State Machine, Service Registry specification |
| HA-ARCH-DEV | [HA Devices & Services](https://github.com/home-assistant/developers.home-assistant/blob/master/docs/architecture/devices-and-services.md) | Entity model, integration patterns |
| HA-API-REST | [HA REST API](https://developers.home-assistant.io/docs/api/rest/) | External API surface |
| HA-API-WS | [HA WebSocket API](https://developers.home-assistant.io/docs/api/websocket/) | Real-time API surface |
| HA-AUTO | [HA Automation YAML](https://www.home-assistant.io/docs/automation/yaml/) | Automation grammar specification |
| MQTT-5.0 | OASIS MQTT v5.0 Specification | Wire protocol for device communication |
| DELFT-2019 | [TU Delft HA Architecture Analysis](https://se.ewi.tudelft.nl/desosa2019/chapters/home-assistant/) | Independent architectural documentation |

---

## 3. SYSTEM-WIDE DESIGN DECISIONS

### 3.1 Language Selection

| Component | Language | Rationale |
|---|---|---|
| Core Engine (state machine, event bus, automation engine, MQTT interface) | Rust (tokio async runtime) | Zero-cost abstractions, no GC, predictable sub-ms latency, memory safety without runtime overhead. This is the thing that runs 24/7 on a Pi controlling your door locks Ã¢â‚¬â€ it doesn't get to hiccup. |
| Integration SDK | Rust (native) + Go (convenience) + gRPC (polyglot) | Rust for integrations that need to be fast (Z-Wave, Zigbee). Go for integrations where developer velocity matters more than nanoseconds (cloud API pollers, REST wrappers). gRPC for everything else Ã¢â‚¬â€ Python, Node, whatever. |
| HTTP/WebSocket API Server | Rust (axum/tower) | Shares the core process, zero serialization overhead to state machine |
| Frontend | TypeScript + React | Industry standard, component ecosystem, WebSocket native |
| Configuration | YAML (HA-compatible) + TOML (native) | Migration path + ergonomic native config |
| Database | SQLite (embedded, via rusqlite) + optional TimescaleDB | Zero-config default, scalable option for power users |

**Why Rust and not Go for the core:** We spent the entire motivation section dunking on Python's runtime overhead, GC pauses, and memory bloat. Go improves on all of those Ã¢â‚¬â€ but it still has a garbage collector, still has a runtime, and still burns 30-40MB before you've done anything useful. On a Raspberry Pi with 2GB of RAM running a home security system, that matters. Go is a no-brainer in the cloud. Go on an embedded device is something we've seen fail. The core that sits on your SBC and must respond in microseconds to "the smoke detector went off" is written in Rust. The integration that polls your weather API every 15 minutes can be written in Go, Python, or a napkin Ã¢â‚¬â€ it doesn't matter because it's in a separate process.

### 3.2 Architectural Principles

1. **MQTT-Native**: MQTT is not a bolt-on integration; it is the internal message bus. All entity state changes, service calls, and events flow through MQTT topics with well-defined topic hierarchies.

2. **Entity-First**: The entity model (derived from HA's decade of refinement) is the fundamental abstraction. Everything is an entity with a domain, state, attributes, and capabilities.

3. **Integration as Process**: Unlike HA's in-process Python integrations, Marge integrations run as isolated processes communicating via gRPC or MQTT. A misbehaving integration cannot crash the core.

4. **Configuration Compatibility**: Marge SHALL parse HA's `configuration.yaml`, `automations.yaml`, and entity configuration with Ã¢â€°Â¥90% compatibility for standard configurations.

5. **Local-First**: The system SHALL operate fully without internet connectivity. Cloud integrations are optional bridges, not dependencies.

### 3.3 Key Architectural Differences from Home Assistant

| Aspect | Home Assistant | Marge |
|---|---|---|
| Runtime | Python 3.12 + asyncio | Rust (tokio) core, polyglot integrations |
| Integration isolation | In-process (shared GIL) | Out-of-process (gRPC/MQTT) |
| State machine | Python dict + event bus | Lock-free concurrent map (dashmap) + MQTT pub/sub |
| Event bus | In-memory Python | MQTT broker (embedded rumqttd or external Mosquitto) |
| Entity polling | asyncio DataUpdateCoordinator | Per-integration async task with backpressure |
| Configuration | YAML only | YAML (compat) + TOML (native) + API |
| Frontend | Polymer/Lit web components | React + WebSocket |
| Plugin language | Python only | Any (via gRPC). Rust native, Go native, Python via shim |
| Database | SQLAlchemy + SQLite/MariaDB/PostgreSQL | rusqlite (embedded) + optional TimescaleDB |
| Startup time | 30-120s typical | Target: <2s core, <5s with integrations |
| Memory baseline | 300-800MB typical | Target: <15MB core, <100MB with integrations |

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 Core Engine (CSCI-CORE)

The Core Engine provides the four fundamental services identified in HA's architecture, reimplemented for performance:

#### 4.1.1 Event Bus (CSC-EVTBUS)

**Derived from:** HA-ARCH-CORE Ã¢â‚¬â€ "Event Bus: facilitates the firing and listening of events Ã¢â‚¬â€ the beating heart of Home Assistant."

The Event Bus SHALL be implemented as an MQTT topic hierarchy with the following structure:

```
marge/events/{event_type}                    # Event publication
marge/events/state_changed/{domain}/{entity}  # State change events
marge/events/call_service/{domain}/{service}  # Service call events
marge/events/automation_triggered/{auto_id}   # Automation trigger events
marge/events/system/{event}                   # System lifecycle events
```

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| EVTBUS-001 | The Event Bus SHALL support publish/subscribe semantics with topic wildcards | P1 |
| EVTBUS-002 | Events SHALL be serialized as Protocol Buffers with JSON fallback for debugging | P1 |
| EVTBUS-003 | The Event Bus SHALL support QoS 0 (fire-and-forget) and QoS 1 (at-least-once) delivery | P1 |
| EVTBUS-004 | Event throughput SHALL exceed 50,000 events/second on reference hardware (RPi 4) | P1 |
| EVTBUS-005 | The Event Bus SHALL support retained messages for last-known-good state | P1 |
| EVTBUS-006 | Event latency from publication to subscriber delivery SHALL be <100Ã‚Âµs for local subscribers | P2 |
| EVTBUS-007 | The Event Bus SHALL provide event replay from a configurable rolling buffer (default: 1000 events) | P3 |

**Event Schema (protobuf):**

```protobuf
message Event {
  string event_type = 1;
  google.protobuf.Timestamp time_fired = 2;
  google.protobuf.Struct data = 3;
  Context context = 4;
  string origin = 5;  // "LOCAL", "REMOTE", "INTEGRATION"
}

message Context {
  string id = 1;
  optional string parent_id = 2;
  optional string user_id = 3;
}
```

#### 4.1.2 State Machine (CSC-STATE)

**Derived from:** HA-ARCH-CORE Ã¢â‚¬â€ "State Machine: keeps track of the states of things and fires a state_changed event when a state has been changed."

The State Machine SHALL maintain the authoritative state of all entities in the system.

**State Object Schema:**

```protobuf
message State {
  string entity_id = 1;           // Format: "{domain}.{object_id}"
  string state = 2;               // String representation of current state
  google.protobuf.Struct attributes = 3;
  google.protobuf.Timestamp last_changed = 4;  // When state value changed
  google.protobuf.Timestamp last_reported = 5;  // When any update received
  google.protobuf.Timestamp last_updated = 6;  // When state or attributes changed
  Context context = 7;
}
```

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| STATE-001 | The State Machine SHALL store state in a concurrent-safe map (dashmap or arc-swap) keyed by entity_id | P1 |
| STATE-002 | State reads SHALL be lock-free (arc-swap atomic pointer pattern) | P1 |
| STATE-003 | State writes SHALL fire a `state_changed` event on the Event Bus containing old_state and new_state | P1 |
| STATE-004 | The State Machine SHALL support Ã¢â€°Â¥50,000 simultaneous entities | P1 |
| STATE-005 | State persistence SHALL write to SQLite on a configurable interval (default: 5 minutes) with WAL mode | P1 |
| STATE-006 | State SHALL distinguish between `last_changed` (state value change), `last_updated` (state or attribute change), and `last_reported` (any write, even if unchanged) | P1 |
| STATE-007 | The State Machine SHALL support optimistic state updates with rollback on integration NACK | P2 |
| STATE-008 | The State Machine SHALL write `unavailable` state for any registered entity not backed by an active integration | P1 |

#### 4.1.3 Service Registry (CSC-SVREG)

**Derived from:** HA-ARCH-CORE Ã¢â‚¬â€ "Service Registry: listens on the event bus for call_service events and allows other code to register service actions."

The Service Registry maps domain-scoped service names to handler functions, enabling both internal and external callers to invoke actions on entities.

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| SVREG-001 | Services SHALL be registered under `{domain}.{service_name}` namespace | P1 |
| SVREG-002 | Service calls SHALL support target specifiers: `entity_id`, `device_id`, `area_id`, `label_id` | P1 |
| SVREG-003 | Service schemas SHALL be defined in protobuf with JSON Schema fallback for dynamic integrations | P1 |
| SVREG-004 | Service calls SHALL support synchronous (blocking) and asynchronous (fire-and-forget) modes | P1 |
| SVREG-005 | The Service Registry SHALL support response data from services (SupportsResponse pattern) | P2 |
| SVREG-006 | Service calls SHALL be traceable via Context propagation | P1 |

#### 4.1.4 Entity Registry (CSC-ENTREG)

**Derived from:** HA-ARCH-DEV Ã¢â‚¬â€ "The entity registry will write an unavailable state for any registered entity that is not currently backed by an entity object."

The Entity Registry provides persistent metadata storage for entities across restarts.

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| ENTREG-001 | The Entity Registry SHALL persist entity metadata including unique_id, device associations, custom names, disabled status, and icon overrides | P1 |
| ENTREG-002 | Entity IDs SHALL follow the format `{domain}.{object_id}` where object_id is auto-generated from device/integration info or user-specified | P1 |
| ENTREG-003 | The Entity Registry SHALL support entity disable/enable without losing configuration | P1 |
| ENTREG-004 | The Entity Registry SHALL support entity renaming by users without breaking automations (alias system) | P2 |

#### 4.1.5 Device Registry (CSC-DEVREG)

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| DEVREG-001 | The Device Registry SHALL group entities by physical device with manufacturer, model, firmware version, and connection info | P1 |
| DEVREG-002 | Device lifecycle operations (disable, delete, re-enable) SHALL cascade to all child entities | P1 |
| DEVREG-003 | The Device Registry SHALL support device areas for spatial organization | P1 |
| DEVREG-004 | The Device Registry SHALL support device labels for arbitrary tagging | P2 |

---

### 4.2 Entity Platform System (CSCI-ENTITY)

**Derived from:** HA's 30+ entity domains that standardize device interaction.

The Entity Platform System defines the contract between integrations and the core. Each domain specifies required states, attributes, device classes, and service actions.

#### 4.2.1 Entity Base Contract

All entities SHALL implement the following base trait:

```rust
use std::collections::HashMap;
use std::time::Duration;
use anyhow::Result;

#[async_trait]
pub trait Entity: Send + Sync {
    // Identity
    fn entity_id(&self) -> &str;          // e.g., "light.kitchen"
    fn unique_id(&self) -> &str;          // Integration-specific unique identifier
    fn domain(&self) -> &str;             // e.g., "light", "switch", "sensor"
    
    // State
    fn state(&self) -> &str;              // Current state string
    fn attributes(&self) -> &HashMap<String, serde_json::Value>;
    fn available(&self) -> bool;          // Whether the entity is reachable
    
    // Metadata
    fn name(&self) -> &str;
    fn device_class(&self) -> Option<&str>;
    fn unit_of_measurement(&self) -> Option<&str>;
    fn icon(&self) -> Option<&str>;
    
    // Lifecycle
    async fn on_added(&mut self) -> Result<()>;
    async fn on_removed(&mut self) -> Result<()>;
    
    // Update patterns
    fn should_poll(&self) -> bool { false }  // default: push-based
    fn poll_interval(&self) -> Duration { Duration::from_secs(30) }
    async fn update(&mut self) -> Result<()> { Ok(()) }
}
```

#### 4.2.2 Core Entity Domains

The following domains SHALL be implemented in Phase 1, derived from HA's most-used entity types:

| Domain | States | Key Attributes | Service Actions | Device Classes |
|---|---|---|---|---|
| `light` | `on`, `off` | brightness, color_temp, rgb_color, effect, color_mode | turn_on, turn_off, toggle | Ã¢â‚¬â€ |
| `switch` | `on`, `off` | Ã¢â‚¬â€ | turn_on, turn_off, toggle | outlet, switch |
| `sensor` | numeric/string value | unit_of_measurement, state_class | Ã¢â‚¬â€ | temperature, humidity, power, energy, battery, pressure, illuminance, voltage, current, +60 more |
| `binary_sensor` | `on`, `off` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | motion, door, window, smoke, gas, moisture, vibration, occupancy, +20 more |
| `climate` | `off`, `heat`, `cool`, `heat_cool`, `auto`, `dry`, `fan_only` | temperature, target_temp_high/low, current_temperature, humidity, hvac_modes, fan_modes, preset_modes | set_temperature, set_hvac_mode, set_fan_mode, set_preset_mode | Ã¢â‚¬â€ |
| `cover` | `open`, `closed`, `opening`, `closing` | current_position, current_tilt_position | open, close, stop, set_position, set_tilt_position | awning, blind, curtain, damper, door, garage, gate, shade, shutter, window |
| `lock` | `locked`, `unlocked`, `locking`, `unlocking`, `jammed` | Ã¢â‚¬â€ | lock, unlock, open | Ã¢â‚¬â€ |
| `media_player` | `off`, `on`, `idle`, `playing`, `paused`, `buffering` | volume_level, is_volume_muted, media_content_id, media_title, source, source_list | turn_on, turn_off, play_media, volume_set, media_play, media_pause, media_stop, select_source | tv, speaker, receiver |
| `camera` | `idle`, `recording`, `streaming` | frontend_stream_type | turn_on, turn_off, snapshot | Ã¢â‚¬â€ |
| `alarm_control_panel` | `disarmed`, `armed_home`, `armed_away`, `armed_night`, `armed_vacation`, `pending`, `arming`, `triggered` | code_format, changed_by | arm_home, arm_away, arm_night, arm_vacation, disarm, trigger | Ã¢â‚¬â€ |
| `fan` | `on`, `off` | percentage, preset_mode, oscillating, direction | turn_on, turn_off, toggle, set_percentage, set_preset_mode, oscillate, set_direction | Ã¢â‚¬â€ |
| `button` | timestamp of last press | Ã¢â‚¬â€ | press | identify, restart, update |
| `number` | numeric value | min, max, step, mode | set_value | Same as sensor |
| `select` | string value | options | select_option | Ã¢â‚¬â€ |
| `text` | string value | min, max, pattern, mode | set_value | Ã¢â‚¬â€ |
| `event` | timestamp of last event | event_type, event_types | Ã¢â‚¬â€ | button, doorbell, motion |
| `update` | `on` (available), `off` (up-to-date) | installed_version, latest_version, release_url, release_summary | install, skip | firmware, software |
| `device_tracker` | `home`, `not_home`, zone name | source_type, latitude, longitude, gps_accuracy, battery | Ã¢â‚¬â€ | Ã¢â‚¬â€ |
| `person` | `home`, `not_home`, zone name | latitude, longitude, gps_accuracy, source, user_id | Ã¢â‚¬â€ | Ã¢â‚¬â€ |
| `scene` | timestamp of last activated | Ã¢â‚¬â€ | turn_on | Ã¢â‚¬â€ |
| `script` | `on`, `off` | last_triggered | turn_on, turn_off, toggle | Ã¢â‚¬â€ |
| `automation` | `on`, `off` | last_triggered, current | turn_on, turn_off, trigger, toggle | Ã¢â‚¬â€ |
| `input_boolean` | `on`, `off` | Ã¢â‚¬â€ | turn_on, turn_off, toggle | Ã¢â‚¬â€ |
| `input_number` | numeric value | min, max, step, mode | set_value | Ã¢â‚¬â€ |
| `input_select` | string value | options | select_option | Ã¢â‚¬â€ |
| `input_text` | string value | min, max, pattern, mode | set_value | Ã¢â‚¬â€ |
| `input_datetime` | datetime string | has_date, has_time, timestamp | set_datetime | Ã¢â‚¬â€ |
| `weather` | `clear-night`, `cloudy`, `fog`, `hail`, `lightning`, `rainy`, `snowy`, `sunny`, `windy`, etc. | temperature, humidity, pressure, wind_speed, forecast | get_forecasts | Ã¢â‚¬â€ |
| `vacuum` | `cleaning`, `docked`, `paused`, `idle`, `returning`, `error` | battery_level, fan_speed | start, stop, pause, return_to_base, clean_spot, set_fan_speed | Ã¢â‚¬â€ |
| `water_heater` | `off`, `eco`, `electric`, `gas`, `heat_pump`, `high_demand`, `performance` | temperature, target_temp, min_temp, max_temp, operation_list | set_temperature, set_operation_mode | Ã¢â‚¬â€ |
| `humidifier` | `on`, `off` | humidity, target_humidity, min_humidity, max_humidity, mode, available_modes | turn_on, turn_off, set_humidity, set_mode | humidifier, dehumidifier |
| `siren` | `on`, `off` | available_tones, duration, volume_level, tone | turn_on, turn_off | Ã¢â‚¬â€ |
| `valve` | `open`, `closed`, `opening`, `closing` | current_position | open, close, set_position | gas, water |
| `lawn_mower` | `mowing`, `docked`, `paused`, `error` | Ã¢â‚¬â€ | start_mowing, dock, pause | Ã¢â‚¬â€ |
| `calendar` | `on` (event active), `off` | message, start_time, end_time, location, description | create_event | Ã¢â‚¬â€ |
| `todo` | numeric (items count) | Ã¢â‚¬â€ | add_item, update_item, remove_item, get_items | Ã¢â‚¬â€ |
| `image` | timestamp of last update | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ |
| `tts` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | say (speak) | Ã¢â‚¬â€ |
| `notify` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | send_message | Ã¢â‚¬â€ |

#### 4.2.3 State Classes (for `sensor` domain)

| State Class | Description | Use Case |
|---|---|---|
| `measurement` | Instantaneous reading | Temperature, humidity, power |
| `total` | Monotonically increasing total | Total energy, total gas |
| `total_increasing` | Total that may reset to 0 | Utility meter readings |

---

### 4.3 Automation Engine (CSCI-AUTO)

**Derived from:** HA-AUTO Ã¢â‚¬â€ The trigger-condition-action automation model.

#### 4.3.1 Automation Structure

```yaml
# Marge automation format (HA-compatible)
automations:
  - id: "unique_auto_id"
    alias: "Human-readable name"
    description: "Optional description"
    mode: single | restart | queued | parallel  # Run mode
    max: 10                                      # Max concurrent (queued/parallel)
    
    triggers:
      - trigger: <trigger_type>
        <trigger_config>
    
    conditions:                 # AND by default
      - condition: <condition_type>
        <condition_config>
    
    actions:
      - action: <domain>.<service>
        target:
          entity_id: <entity_id>
        data:
          <service_data>
```

#### 4.3.2 Trigger Types

| Trigger Type | Description | Key Parameters |
|---|---|---|
| `state` | Entity state change | entity_id, from, to, for (duration), attribute |
| `numeric_state` | Numeric threshold crossing | entity_id, above, below, attribute, for |
| `time` | Specific time of day | at (time or input_datetime entity) |
| `time_pattern` | Recurring time pattern | hours, minutes, seconds (with `/` for intervals) |
| `sun` | Solar events | event (sunrise/sunset), offset |
| `zone` | Geofence entry/exit | entity_id, zone, event (enter/leave) |
| `event` | Event bus event | event_type, event_data (match filter) |
| `mqtt` | MQTT message received | topic, payload (match filter), qos |
| `webhook` | HTTP webhook call | webhook_id, allowed_methods |
| `template` | Template evaluates to true | value_template |
| `calendar` | Calendar event start/end | entity_id, event (start/end), offset |
| `device` | Device-specific trigger | device_id, type, subtype |
| `tag` | NFC tag scan | tag_id, device_id |
| `persistent_notification` | Notification lifecycle | notification_id, update_type |
| `conversation` | Voice/text command | command (sentence pattern) |

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| AUTO-001 | The Automation Engine SHALL evaluate triggers in parallel with no shared mutable state | P1 |
| AUTO-002 | Trigger-to-action latency SHALL be <5ms for state triggers on reference hardware | P1 |
| AUTO-003 | The `for` duration parameter SHALL survive system restarts (persistent timers) | P1 |
| AUTO-004 | The Engine SHALL support trigger IDs for multi-trigger automations with conditional branching | P1 |
| AUTO-005 | Trigger variables SHALL be accessible in conditions and actions via `trigger.*` namespace | P1 |

#### 4.3.3 Condition Types

| Condition Type | Description |
|---|---|
| `state` | Entity is in a specific state |
| `numeric_state` | Entity numeric value above/below threshold |
| `time` | Current time within a range |
| `sun` | Before/after sunrise/sunset |
| `zone` | Entity in a zone |
| `template` | Jinja2-compatible template evaluates true |
| `and` | All sub-conditions true |
| `or` | Any sub-condition true |
| `not` | Inverts sub-conditions |
| `trigger` | Matches specific trigger ID |
| `device` | Device-specific condition |

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| COND-001 | Conditions SHALL be evaluated as AND by default (all must be true) | P1 |
| COND-002 | Conditions SHALL support nesting via and/or/not logical operators | P1 |
| COND-003 | Template conditions SHALL support a Jinja2-compatible template engine | P1 |
| COND-004 | Condition evaluation SHALL short-circuit (stop on first false for AND, first true for OR) | P1 |

#### 4.3.4 Action Types

| Action Type | Description |
|---|---|
| `action` (service call) | Call a registered service |
| `delay` | Wait for a duration |
| `wait_template` | Wait until a template evaluates true |
| `wait_for_trigger` | Wait for a specific trigger |
| `condition` | Inline condition check (stops execution if false) |
| `event` | Fire a custom event |
| `choose` | If/else branching |
| `if` | Simplified if/then/else |
| `repeat` | Loop with while/until/count |
| `parallel` | Execute actions in parallel |
| `sequence` | Explicit sequential execution |
| `variables` | Set local variables |
| `stop` | Stop automation execution |
| `set_conversation_response` | Return voice response |

#### 4.3.5 Run Modes

| Mode | Behavior When Triggered While Running |
|---|---|
| `single` | Ignore new trigger (default) |
| `restart` | Stop current run, start new |
| `queued` | Queue new run (max configurable) |
| `parallel` | Run simultaneously (max configurable) |

#### 4.3.6 Template Engine

**Derived from:** HA's Jinja2-based template system.

The template engine SHALL provide a Jinja2-compatible syntax with the following built-in functions:

```
# State access
states('sensor.temperature')              Ã¢â€ â€™ "23.5"
states.sensor.temperature                 Ã¢â€ â€™ "23.5"
state_attr('sensor.temp', 'unit')         Ã¢â€ â€™ "Ã‚Â°C"
is_state('light.kitchen', 'on')           Ã¢â€ â€™ true
is_state_attr('light.kitchen', 'brightness', 255) Ã¢â€ â€™ true

# Time functions
now()                                     Ã¢â€ â€™ current datetime
utcnow()                                  Ã¢â€ â€™ current UTC datetime
today_at('08:00')                         Ã¢â€ â€™ today at 8:00 AM
as_timestamp(state)                       Ã¢â€ â€™ unix timestamp

# Math/filters
value | float                             Ã¢â€ â€™ float conversion
value | int                               Ã¢â€ â€™ int conversion
value | round(2)                           Ã¢â€ â€™ round to 2 decimals
states.sensor.temp.state | float | round(1)

# Collection filters
expand('group.all_lights')                Ã¢â€ â€™ list of entities in group
area_entities('Living Room')              Ã¢â€ â€™ list of entities in area
device_entities('device_id')              Ã¢â€ â€™ list of entities for device
label_entities('label')                   Ã¢â€ â€™ list of entities with label

# Conditional
iif(condition, true_val, false_val)       Ã¢â€ â€™ inline if
```

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| TMPL-001 | The template engine SHALL parse HA-compatible Jinja2 templates | P1 |
| TMPL-002 | Template rendering SHALL be sandboxed (no filesystem, network, or system access) | P1 |
| TMPL-003 | Template rendering SHALL timeout after 5 seconds (configurable) | P1 |
| TMPL-004 | The template engine SHALL be implemented in Rust (evaluate minijinja crate Ã¢â‚¬â€ purpose-built Jinja2 compatibility) or via WASM-sandboxed fallback | P1 |

---

### 4.4 Scene System (CSC-SCENE)

Scenes capture and restore a set of entity states.

```yaml
scenes:
  - id: "movie_time"
    name: "Movie Time"
    entities:
      light.living_room:
        state: "on"
        brightness: 50
        rgb_color: [255, 147, 41]
      media_player.tv:
        state: "on"
        source: "HDMI 1"
      cover.blinds:
        state: "closed"
```

---

### 4.5 Script System (CSC-SCRIPT)

Scripts are reusable action sequences that can be triggered by automations, services, or users.

```yaml
scripts:
  morning_routine:
    alias: "Morning Routine"
    mode: single
    fields:
      brightness:
        description: "Light brightness"
        default: 200
        selector:
          number:
            min: 0
            max: 255
    sequence:
      - action: light.turn_on
        target:
          area_id: kitchen
        data:
          brightness: "{{ brightness }}"
      - delay: "00:00:30"
      - action: media_player.play_media
        target:
          entity_id: media_player.kitchen_speaker
        data:
          media_content_id: "news_briefing"
          media_content_type: "music"
```

---

### 4.6 Blueprint System (CSC-BLUEPRINT)

Blueprints are parameterized automation/script templates that can be shared and instantiated.

```yaml
blueprint:
  name: "Motion-activated Light"
  description: "Turn on a light when motion is detected"
  domain: automation
  input:
    motion_entity:
      name: "Motion Sensor"
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    light_target:
      name: "Light"
      selector:
        target:
          entity:
            domain: light
    no_motion_wait:
      name: "Wait time"
      default: 120
      selector:
        number:
          min: 0
          max: 3600
          unit_of_measurement: seconds

triggers:
  - trigger: state
    entity_id: !input motion_entity
    from: "off"
    to: "on"
actions:
  - action: light.turn_on
    target: !input light_target
  - wait_for_trigger:
      - trigger: state
        entity_id: !input motion_entity
        from: "on"
        to: "off"
  - delay: !input no_motion_wait
  - action: light.turn_off
    target: !input light_target
```

---

### 4.7 History & Recorder (CSCI-RECORDER)

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| REC-001 | The Recorder SHALL persist all state changes to SQLite with WAL mode | P1 |
| REC-002 | The Recorder SHALL support configurable inclusion/exclusion filters by domain, entity, and glob pattern | P1 |
| REC-003 | The Recorder SHALL support automatic purging of old data (configurable retention, default: 10 days) | P1 |
| REC-004 | History queries SHALL support time-range, entity, and aggregate (min, max, mean) filters | P1 |
| REC-005 | The Recorder SHALL support optional export to TimescaleDB for long-term storage | P3 |
| REC-006 | The Recorder SHALL batch writes (configurable commit interval, default: 1 second) to minimize I/O | P1 |
| REC-007 | Statistics (hourly/daily/monthly aggregates) SHALL be computed and stored for `sensor` entities with `state_class` | P2 |

---

### 4.8 Energy Management (CSC-ENERGY)

| ID | Requirement | Priority |
|---|---|---|
| ENERGY-001 | The system SHALL track energy consumption per device, area, and whole-home | P2 |
| ENERGY-002 | The system SHALL support grid consumption, solar production, battery storage, and gas tracking | P2 |
| ENERGY-003 | Energy data SHALL be computed from `sensor` entities with `state_class: total_increasing` and `device_class: energy` | P2 |

---

## 5. INTERFACE REQUIREMENTS

### 5.1 External API (CSCI-API)

#### 5.1.1 REST API

**Derived from:** HA-API-REST

The REST API SHALL provide the following endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/` | API status check |
| GET | `/api/config` | System configuration |
| GET | `/api/states` | All entity states |
| GET | `/api/states/{entity_id}` | Single entity state |
| POST | `/api/states/{entity_id}` | Update entity state |
| GET | `/api/events` | List event listeners |
| POST | `/api/events/{event_type}` | Fire an event |
| GET | `/api/services` | List available services |
| POST | `/api/services/{domain}/{service}` | Call a service |
| GET | `/api/history/period/{timestamp}` | History data |
| POST | `/api/template` | Render a template |
| POST | `/api/config/core/check_config` | Validate configuration |

**Authentication:** Bearer token (long-lived access tokens) and OAuth 2.0 flow.

#### 5.1.2 WebSocket API

The WebSocket API SHALL provide real-time bidirectional communication:

```json
// Client Ã¢â€ â€™ Server: Subscribe to state changes
{
  "id": 1,
  "type": "subscribe_events",
  "event_type": "state_changed"
}

// Server Ã¢â€ â€™ Client: Event notification
{
  "id": 1,
  "type": "event",
  "event": {
    "event_type": "state_changed",
    "data": {
      "entity_id": "light.kitchen",
      "old_state": { "state": "off", ... },
      "new_state": { "state": "on", ... }
    },
    "time_fired": "2026-02-11T12:00:00Z",
    "context": { "id": "...", "user_id": "..." }
  }
}
```

**Key WebSocket Commands:**

| Command | Description |
|---|---|
| `subscribe_events` | Subscribe to event types |
| `unsubscribe_events` | Unsubscribe |
| `get_states` | Fetch all current states |
| `call_service` | Invoke a service |
| `get_config` | Get system config |
| `get_services` | List services |
| `get_panels` | Get UI panel config |
| `subscribe_trigger` | Subscribe to a specific trigger pattern |
| `render_template` | Render and subscribe to template changes |

**Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| API-001 | The REST API SHALL be HA-compatible for all documented endpoints | P1 |
| API-002 | The WebSocket API SHALL support Ã¢â€°Â¥500 concurrent connections | P1 |
| API-003 | Authentication SHALL support both long-lived tokens and OAuth 2.0 | P1 |
| API-004 | The API SHALL support CORS with configurable allowed origins | P2 |
| API-005 | All API responses SHALL include proper rate limiting headers | P3 |

### 5.2 MQTT Interface (CSCI-MQTT)

#### 5.2.1 Internal MQTT (Embedded Broker)

Marge SHALL embed an MQTT v5.0 broker for internal communication. External clients MAY connect to this broker for custom integrations.

**Internal Topic Hierarchy:**

```
marge/                           # Root namespace
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ state/{domain}/{entity_id}      # Retained state (JSON)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ events/{event_type}             # Event stream
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ services/{domain}/{service}     # Service call requests
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ services/{domain}/{service}/response  # Service responses
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ discovery/                      # Auto-discovery announcements
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ {domain}/{node_id}/{object_id}/config  # HA MQTT Discovery compatible
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ...
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ integration/{integration_id}/   # Integration-specific topics
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ status                      # online/offline (LWT)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ command                     # Commands to integration
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ telemetry                   # Integration health data
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ system/                         # System lifecycle
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ status                      # System online/offline
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ log/{level}                 # Log stream
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ health                      # Health check
```

#### 5.2.2 HA MQTT Discovery Compatibility

Marge SHALL support the [HA MQTT Discovery protocol](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery) for zero-configuration device onboarding.

```
# Discovery topic format (HA-compatible):
homeassistant/{domain}/{node_id}/{object_id}/config

# Example: ESP device advertising a temperature sensor
homeassistant/sensor/esp32_kitchen/temperature/config
{
  "name": "Kitchen Temperature",
  "state_topic": "esp32/kitchen/temperature",
  "unit_of_measurement": "Ã‚Â°C",
  "device_class": "temperature",
  "state_class": "measurement",
  "unique_id": "esp32_kitchen_temp",
  "device": {
    "identifiers": ["esp32_kitchen"],
    "name": "Kitchen ESP32",
    "model": "ESP32-DevKit",
    "manufacturer": "Espressif"
  }
}
```

Marge SHALL also listen on `marge/` prefix for native discovery.

---

### 5.3 Frontend Interface (CSCI-UI)

#### 5.3.1 Dashboard System

**Derived from:** HA's Lovelace dashboard system.

The frontend SHALL be a React-based SPA communicating via WebSocket API.

**Dashboard Configuration:**

```yaml
dashboards:
  - title: "Home"
    path: "home"
    icon: "mdi:home"
    views:
      - title: "Overview"
        path: "overview"
        type: masonry  # masonry | sidebar | panel
        cards:
          - type: entities
            title: "Living Room"
            entities:
              - entity: light.living_room
              - entity: sensor.living_room_temperature
              - entity: climate.living_room
          
          - type: history-graph
            title: "Temperature History"
            hours_to_show: 24
            entities:
              - entity: sensor.living_room_temperature
              - entity: sensor.outside_temperature
          
          - type: thermostat
            entity: climate.living_room
          
          - type: media-control
            entity: media_player.living_room_tv
```

**Core Card Types:**

| Card Type | Description |
|---|---|
| `entities` | List of entity rows with state/toggle |
| `button` | Single entity button with icon |
| `light` | Light control with brightness/color |
| `thermostat` | Climate control dial |
| `media-control` | Media player controls |
| `history-graph` | Entity history chart |
| `gauge` | Numeric gauge/dial |
| `sensor` | Single sensor display |
| `alarm-panel` | Alarm keypad |
| `camera` | Camera feed |
| `map` | Location map |
| `weather-forecast` | Weather display |
| `energy` | Energy dashboard |
| `grid` | Grid layout container |
| `horizontal-stack` | Horizontal card container |
| `vertical-stack` | Vertical card container |
| `conditional` | Show card based on condition |
| `markdown` | Markdown content |
| `iframe` | Embedded webpage |
| `custom:*` | Custom card (plugin system) |

---

## 6. INTEGRATION FRAMEWORK (CSCI-INTEG)

### 6.1 Integration Architecture

Unlike HA's in-process Python model, Marge integrations operate as **isolated processes** communicating via gRPC or MQTT. The core itself is a single Rust binary; integrations can be Rust (compiled in or separate), Go, Python, or anything that speaks gRPC/MQTT:

```
Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
Ã¢â€â€š              MARGE CORE (Rust binary)            Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€šEvent Bus Ã¢â€â€š Ã¢â€â€šState Mach.Ã¢â€â€š Ã¢â€â€š Service Registry Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š  (MQTT)  Ã¢â€â€š Ã¢â€â€š (dashmap) Ã¢â€â€š Ã¢â€â€š                  Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€š       Ã¢â€â€š             Ã¢â€â€š                Ã¢â€â€š             Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š         Integration Manager (tokio)           Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š    (gRPC server + MQTT bridge + lifecycle)    Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€š     Ã¢â€â€š          Ã¢â€â€š          Ã¢â€â€š          Ã¢â€â€š             Ã¢â€â€š
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
      Ã¢â€â€š          Ã¢â€â€š          Ã¢â€â€š          Ã¢â€â€š
 Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
 Ã¢â€â€šZ-Wave  Ã¢â€â€š Ã¢â€â€šESPHome Ã¢â€â€š Ã¢â€â€šHue     Ã¢â€â€š Ã¢â€â€šCustom  Ã¢â€â€š
 Ã¢â€â€šPlugin  Ã¢â€â€š Ã¢â€â€šPlugin  Ã¢â€â€š Ã¢â€â€šPlugin  Ã¢â€â€š Ã¢â€â€šPlugin  Ã¢â€â€š
 Ã¢â€â€š(Rust)  Ã¢â€â€š Ã¢â€â€š(Rust)  Ã¢â€â€š Ã¢â€â€š(Go)    Ã¢â€â€š Ã¢â€â€š(Any)   Ã¢â€â€š
 Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
  Separate    Separate    Separate    Separate
  Process     Process     Process     Process
```

### 6.2 Integration SDK (Rust Ã¢â‚¬â€ Native)

```rust
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Top-level trait for a Marge integration.
#[async_trait]
pub trait Integration: Send + Sync {
    // Metadata
    fn manifest(&self) -> &Manifest;
    
    // Lifecycle
    async fn setup(&mut self, config: &ConfigEntry) -> Result<()>;
    async fn teardown(&mut self) -> Result<()>;
    
    // Entity discovery
    fn platforms(&self) -> Vec<Box<dyn Platform>>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub domain: String,
    pub name: String,
    pub version: String,
    pub documentation: Option<String>,
    pub dependencies: Vec<String>,
    pub iot_class: IoTClass,         // LocalPush, LocalPolling, CloudPush, CloudPolling
    pub config_flow: bool,
    pub protocols: Vec<String>,      // mqtt, zwave, zigbee, http, etc.
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IoTClass {
    LocalPush,
    LocalPolling,
    CloudPush,
    CloudPolling,
    Calculated,
}

#[async_trait]
pub trait Platform: Send + Sync {
    fn domain(&self) -> &str;        // "light", "switch", etc.
    async fn setup_entry(&mut self, entry: &ConfigEntry) -> Result<Vec<Box<dyn Entity>>>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigEntry {
    pub entry_id: String,
    pub domain: String,
    pub title: String,
    pub data: HashMap<String, serde_json::Value>,
    pub options: HashMap<String, serde_json::Value>,
    pub unique_id: Option<String>,
    pub source: String,              // "user", "discovery", "import"
}
```

### 6.2.1 Integration SDK (Go Ã¢â‚¬â€ Convenience)

For integration authors who prefer developer velocity over bare-metal performance (cloud API pollers, REST wrappers, etc.), a Go SDK is provided that communicates with the core via gRPC:

```go
package marge

// Integration is the top-level interface for a Marge integration in Go.
// The Go SDK handles gRPC communication with the Rust core transparently.
type Integration interface {
    Manifest() Manifest
    Setup(ctx context.Context, config ConfigEntry) error
    Teardown(ctx context.Context) error
    Platforms() []Platform
}

type Platform interface {
    Domain() string
    SetupEntry(ctx context.Context, entry ConfigEntry) ([]Entity, error)
}
```

The Go SDK is a thin wrapper around the gRPC protocol (Ã‚Â§6.3). Integration authors write idiomatic Go; the SDK marshals everything into protobuf and handles the process lifecycle. This is the recommended path for integrations that poll cloud APIs, wrap REST services, or don't need microsecond response times.

### 6.3 Integration Communication Protocol (gRPC)

```protobuf
service IntegrationService {
    // Core lifecycle
    rpc Setup(SetupRequest) returns (SetupResponse);
    rpc Teardown(TeardownRequest) returns (TeardownResponse);
    
    // Entity management
    rpc GetEntities(GetEntitiesRequest) returns (GetEntitiesResponse);
    rpc UpdateState(StateUpdate) returns (StateUpdateResponse);
    
    // Service calls (core Ã¢â€ â€™ integration)
    rpc HandleServiceCall(ServiceCallRequest) returns (ServiceCallResponse);
    
    // Streaming state updates (integration Ã¢â€ â€™ core)
    rpc StreamStateUpdates(stream StateUpdate) returns (stream Acknowledgement);
    
    // Health
    rpc HealthCheck(HealthRequest) returns (HealthResponse);
}
```

### 6.4 Integration Classification

**Derived from:** HA's IoT class system.

| IoT Class | Description | Update Pattern |
|---|---|---|
| `local_push` | Local device pushes updates | Subscribe to device events |
| `local_polling` | Local device polled for state | Periodic HTTP/TCP queries |
| `cloud_push` | Cloud API pushes updates | Webhook/WebSocket from cloud |
| `cloud_polling` | Cloud API polled for state | Periodic HTTP API calls |
| `calculated` | No device communication | Computed from other entities |

### 6.5 Integration Patterns

#### Pattern 1: MQTT Device (Zero-Code)
Devices that speak MQTT with HA Discovery need NO custom integration. The built-in MQTT integration handles them automatically via discovery topics.

#### Pattern 2: Rust Native Plugin
For maximum performance and type safety. Compiles as a separate binary or optionally as a feature-flagged crate linked into the core. Used for protocol-heavy integrations (Z-Wave, Zigbee, ESPHome).

#### Pattern 3: Go Plugin (Convenience SDK)
For integrations where developer velocity matters more than nanoseconds. The Go SDK wraps gRPC communication transparently. Ideal for cloud API pollers, REST wrappers, and anything that doesn't need microsecond response times.

#### Pattern 4: gRPC Polyglot Plugin
For any language. Implement the `IntegrationService` gRPC interface. The core manages the process lifecycle. Write your integration in Node.js, Python, Java, whatever Ã¢â‚¬â€ if it speaks gRPC, it works.

#### Pattern 5: HA Integration Shim
A compatibility layer that wraps existing HA Python integrations in a subprocess, translating between HA's Python API and Marge's gRPC protocol. This enables a migration path for the long tail of integrations.

```
Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
Ã¢â€â€š    HA Compatibility Shim    Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š  Python 3.12 Runtime  Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š  HA Core (minimal)    Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š  Target Integration   Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€š              Ã¢â€â€š              Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š   gRPC Ã¢â€ â€ HA Bridge    Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
```

### 6.6 Priority Integrations (Phase 1)

| Integration | Protocol | IoT Class | Complexity |
|---|---|---|---|
| MQTT | MQTT v5.0 | local_push | Low (native) |
| Z-Wave JS | WebSocket to zwavejs2mqtt | local_push | Medium |
| Zigbee (ZHA) | Serial + zigpy | local_push | High |
| ESPHome | Native API (protobuf) | local_push | Medium |
| Philips Hue | REST + SSE | local_push | Medium |
| HomeKit | HAP | local_push | High |
| Matter | Matter SDK | local_push | Very High |
| REST/HTTP | HTTP | cloud_polling | Low |
| Command Line | exec | local_polling | Low |
| Template | Ã¢â‚¬â€ | calculated | Low |
| Group | Ã¢â‚¬â€ | calculated | Low |
| Sun | Ã¢â‚¬â€ | calculated | Low |
| Time/Date | Ã¢â‚¬â€ | calculated | Low |

---

## 7. NON-FUNCTIONAL REQUIREMENTS

### 7.1 Performance

| ID | Requirement | Target | Priority |
|---|---|---|---|
| PERF-001 | Core startup time (no integrations) | <500 milliseconds | P1 |
| PERF-002 | Full startup time (20 integrations, 500 entities) | <3 seconds | P1 |
| PERF-003 | Base memory footprint (core only) | <15 MB | P1 |
| PERF-004 | Working memory (500 entities, 20 integrations) | <100 MB | P1 |
| PERF-005 | State change latency (write Ã¢â€ â€™ event delivery) | <100 Ã‚Âµs | P1 |
| PERF-006 | Automation trigger-to-action latency | <5 ms | P1 |
| PERF-007 | API request latency (REST GET /states) | <2 ms | P2 |
| PERF-008 | WebSocket event delivery latency | <500 Ã‚Âµs | P2 |
| PERF-009 | Event bus throughput | >50,000 events/sec | P2 |
| PERF-010 | Concurrent WebSocket connections | Ã¢â€°Â¥1,000 | P2 |
| PERF-011 | Core binary size (stripped, static) | <20 MB | P2 |

### 7.2 Reliability

| ID | Requirement | Priority |
|---|---|---|
| REL-001 | Integration crash SHALL NOT crash the core engine | P1 |
| REL-002 | The system SHALL recover from integration failures with automatic restart (configurable backoff) | P1 |
| REL-003 | The system SHALL maintain state across power loss via WAL-mode SQLite | P1 |
| REL-004 | The system SHALL support watchdog monitoring and automatic restart | P1 |
| REL-005 | Automation timers SHALL persist across restarts | P1 |
| REL-006 | The system SHALL support graceful shutdown with state flush | P1 |

### 7.3 Security

| ID | Requirement | Priority |
|---|---|---|
| SEC-001 | All external APIs SHALL require authentication | P1 |
| SEC-002 | The system SHALL support TLS for all network interfaces | P1 |
| SEC-003 | Integration processes SHALL run with minimal OS privileges (seccomp/AppArmor profiles) | P2 |
| SEC-004 | Secrets in configuration SHALL be stored encrypted at rest | P1 |
| SEC-005 | The system SHALL support user accounts with role-based access control | P2 |
| SEC-006 | The MQTT broker SHALL support ACLs per integration | P2 |

### 7.4 Deployment

| ID | Requirement | Priority |
|---|---|---|
| DEP-001 | The core engine SHALL be distributable as a single statically-linked Rust binary (musl target) | P1 |
| DEP-002 | The system SHALL support deployment via Docker/OCI container | P1 |
| DEP-003 | The system SHALL support Raspberry Pi 4+ (ARM64) as reference hardware | P1 |
| DEP-004 | The system SHALL support x86_64 Linux as primary development target | P1 |
| DEP-005 | The system SHALL support cross-compilation for all target architectures | P2 |

### 7.5 HA Migration Compatibility

| ID | Requirement | Priority |
|---|---|---|
| MIG-001 | The system SHALL parse HA `configuration.yaml` with Ã¢â€°Â¥90% compatibility for core config | P1 |
| MIG-002 | The system SHALL parse HA `automations.yaml` with Ã¢â€°Â¥95% compatibility | P1 |
| MIG-003 | The system SHALL import HA entity registry and device registry | P2 |
| MIG-004 | The system SHALL provide a migration wizard for guided HA Ã¢â€ â€™ Marge transition | P3 |
| MIG-005 | The REST and WebSocket APIs SHALL be HA-compatible for existing tool/dashboard support | P1 |

---

## 8. DEVELOPMENT PHASING

### Phase 0: Foundation (Weeks 1-4)
- [ ] Project scaffolding, CI/CD, testing framework
- [ ] Embedded MQTT broker integration
- [ ] Core State Machine implementation
- [ ] Event Bus (MQTT-backed)
- [ ] Service Registry
- [ ] Entity and Device Registries
- [ ] Configuration parser (YAML + TOML)
- [ ] SQLite persistence layer

### Phase 1: Core Engine (Weeks 5-8)
- [ ] Entity Platform System (base + top 10 domains)
- [ ] Automation Engine (triggers, conditions, actions)
- [ ] Template Engine (Jinja2-compatible in Go)
- [ ] Scene and Script systems
- [ ] REST API (HA-compatible)
- [ ] WebSocket API (HA-compatible)
- [ ] Basic authentication (long-lived tokens)

### Phase 2: First Integrations (Weeks 9-12)
- [ ] MQTT integration (with HA Discovery)
- [ ] REST/HTTP integration
- [ ] Command Line integration
- [ ] Template, Group, Sun, Time integrations
- [ ] Integration Manager (process lifecycle)
- [ ] gRPC integration protocol
- [ ] ESPHome integration

### Phase 3: Frontend (Weeks 13-16)
- [ ] React dashboard framework
- [ ] Core card types (entities, button, light, thermostat, gauge, history-graph)
- [ ] Dashboard configuration parser
- [ ] WebSocket state synchronization
- [ ] Mobile-responsive layout
- [ ] Entity detail dialogs

### Phase 4: Protocol Integrations (Weeks 17-24)
- [ ] Z-Wave JS integration
- [ ] Zigbee (ZHA) integration
- [ ] Philips Hue integration
- [ ] HomeKit integration
- [ ] HA Python Compatibility Shim

### Phase 5: Polish & Migration (Weeks 25-30)
- [ ] HA migration wizard
- [ ] Energy management dashboard
- [ ] Long-term statistics
- [ ] Blueprint system
- [ ] Custom card plugin system
- [ ] OAuth 2.0 authentication
- [ ] Documentation

---

## 9. RISK REGISTER

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| RISK-001 | Jinja2-compatible template engine in Rust is complex to implement | High | High | Evaluate existing Rust template libs (tera, minijinja Ã¢â‚¬â€ minijinja is literally designed as Jinja2-compatible); fall back to WASM-sandboxed Python for templates only if needed |
| RISK-002 | Integration isolation via separate processes adds latency | Medium | Low | Benchmark early; use Unix domain sockets for local IPC; MQTT is already fast; Rust native integrations can be compiled into the core as feature flags |
| RISK-003 | HA YAML compatibility is a moving target | High | High | Pin to a specific HA release for compatibility baseline (2024.12); the Conformance Test Suite (MRG-CTS-001) runs against both HA-legacy and Marge in CI Ã¢â‚¬â€ behavioral drift is caught automatically |
| RISK-004 | Z-Wave/Zigbee protocol complexity | High | Medium | Leverage existing zwavejs2mqtt and zigpy libraries; don't rewrite protocol stacks |
| RISK-005 | Frontend development is a massive effort | High | High | Start with API-first design; consider forking HA frontend initially; React rewrite as Phase 3 |
| RISK-006 | Single developer resource constraint | Critical | High | Prioritize ruthlessly; Phase 0-2 are MVP; Phase 3+ can be community-driven |
| RISK-007 | HA Python Compatibility Shim performance | Medium | Medium | Accept that shimmed integrations run slower; use as migration bridge only |
| RISK-008 | Rust learning curve for integration contributors | Medium | High | Go SDK provides an easier on-ramp for non-systems developers; gRPC protocol means any language works; reserve Rust for core and performance-critical integrations |
| RISK-009 | Rust compile times slow iteration speed | Medium | Medium | Use `cargo check` and `cargo clippy` for fast feedback; workspace with small crates; `mold` linker; integration development happens in Go/Python anyway |

---

## 10. GLOSSARY

| Term | Definition |
|---|---|
| **Entity** | The fundamental data unit representing a device capability (e.g., a light's on/off state, a sensor's temperature reading) |
| **Domain** | A category of entity types (e.g., `light`, `sensor`, `switch`) that defines the entity's state schema and available services |
| **Device Class** | A sub-classification within a domain that affects presentation and behavior (e.g., `motion` within `binary_sensor`) |
| **State** | The current value of an entity (a string), plus a set of typed attributes |
| **Service** | A callable action registered under `{domain}.{action_name}` (e.g., `light.turn_on`) |
| **Integration** | A plugin that connects external devices or services to Marge's entity model |
| **Config Entry** | A persistent configuration record for an integration instance |
| **Automation** | A trigger-condition-action rule that reacts to system events |
| **Scene** | A saved snapshot of entity states that can be restored |
| **Script** | A reusable sequence of actions |
| **Blueprint** | A parameterized automation/script template |
| **Area** | A named physical location used to group devices and entities |
| **Label** | An arbitrary tag applied to entities for flexible grouping |

---

## APPENDIX A: ENTITY_ID NAMING CONVENTION

Format: `{domain}.{object_id}`

- `domain`: One of the registered entity domains (see Ã‚Â§4.2.2)
- `object_id`: Snake_case identifier, auto-generated or user-specified

Examples:
```
light.kitchen_ceiling
sensor.outdoor_temperature
binary_sensor.front_door_motion
climate.living_room_thermostat
switch.garage_outlet
lock.front_door
alarm_control_panel.home
```

---

## APPENDIX B: EVENT TYPES (CORE)

| Event Type | Fired When | Data |
|---|---|---|
| `state_changed` | Any entity state change | entity_id, old_state, new_state |
| `call_service` | Service invocation | domain, service, service_data |
| `automation_triggered` | Automation fires | name, entity_id, variables |
| `script_started` | Script begins execution | name, entity_id |
| `component_loaded` | Integration loaded | component |
| `marge_start` | System startup complete | Ã¢â‚¬â€ |
| `marge_stop` | System shutdown initiated | Ã¢â‚¬â€ |
| `marge_final_write` | Last DB write before shutdown | Ã¢â‚¬â€ |
| `time_changed` | Every second (internal clock) | now |
| `timer_out_of_sync` | System clock drift detected | Ã¢â‚¬â€ |
| `entity_registry_updated` | Entity registry change | action, entity_id |
| `device_registry_updated` | Device registry change | action, device_id |
| `area_registry_updated` | Area registry change | action, area_id |

---

## APPENDIX C: CONFIGURATION SCHEMA (NATIVE TOML)

```toml
[marge]
name = "Home"
latitude = 40.3916
longitude = -111.8508
elevation = 1400
unit_system = "us_customary"  # or "metric"
time_zone = "America/Denver"
currency = "USD"

[mqtt]
broker = "embedded"           # "embedded" or "external"
port = 1883
websocket_port = 8083
# External broker config (if broker = "external")
# host = "192.168.1.100"
# username = "marge"
# password = "!secret mqtt_password"

[http]
port = 8123
ssl_certificate = ""
ssl_key = ""
cors_allowed_origins = ["*"]

[recorder]
db_url = "sqlite:///data/marge.db"
purge_keep_days = 10
commit_interval = 1  # seconds

[logger]
default = "info"
[logger.logs]
"marge.core" = "debug"
"marge.integration.zwave" = "warning"
```

---

**END OF DOCUMENT**

*"The best software specification is the one that was written before the code."*  
*Ã¢â‚¬â€ Every program manager who never wrote code*
