# API Surface Map -- Marge vs Home Assistant

**Document Number:** MRG-API-001
**Version:** 0.1.0-DRAFT
**Classification:** UNCLASSIFIED // FOUO
**Date:** 2026-02-20
**Parent Documents:** MRG-SRM-001 (Service Replacement Methodology), MRG-CTS-001 (Conformance Test Suite)
**Prepared For:** The Department of Actually Documenting Your API Surface

---

## 1. DESIGN PHILOSOPHY

Marge implements a **superset** of Home Assistant's API surface. Every HA REST endpoint and WebSocket command that Marge implements behaves identically to HA (with known divergences documented in Section 6). HA clients -- including the companion mobile app, frontend dashboard, and third-party integrations -- work against Marge without modification.

Where HA and Marge diverge is in exposure model. HA restricts many operations to WebSocket-only commands (area management, device registry, logbook queries, history, statistics). Marge exposes all of these as REST endpoints in addition to the WebSocket equivalents. This means:

1. **HA-compatible clients** use the same REST and WebSocket APIs they always have. No changes required.
2. **Marge-native clients** can use REST for operations that would otherwise require maintaining a WebSocket connection and managing message IDs.
3. **The CTS** tags Marge-only REST endpoints with `@pytest.mark.marge_only` so they are skipped when running against HA.

The guiding principle: if HA exposes it, Marge exposes it the same way. If Marge adds something, it goes through REST (simpler, stateless, curl-friendly) and optionally through WebSocket as well.

---

## 2. REST API -- HA-COMPATIBLE ENDPOINTS

These endpoints exist on both Home Assistant and Marge. They are the core compatibility surface. All CTS tests that exercise these endpoints run against both targets.

| Endpoint | Method | Description | Notes |
|----------|--------|-------------|-------|
| `/api/` | GET | API status | Returns `{"message": "API running."}` |
| `/api/config` | GET | Core configuration | Returns location, units, version, components |
| `/api/states` | GET | All entity states | Returns array of entity state objects |
| `/api/states/:entity_id` | GET | Single entity state | 404 if entity not found |
| `/api/states/:entity_id` | POST | Create/update entity | HA returns 201 for new, 200 for update. Marge returns 200 for both (known divergence -- see Section 6). |
| `/api/services` | GET | List available services | Returns service definitions grouped by domain |
| `/api/services/:domain/:service` | POST | Call a service | HA returns flat array. Marge matched this in Phase 9.3. |
| `/api/events/:event_type` | POST | Fire an event | Returns `{"message": "Event ... fired."}` |
| `/api/template` | POST | Render a Jinja2 template | Body: `{"template": "..."}`. Returns rendered string. |
| `/api/health` | GET | Health check | HA returns `{"message":"API running."}`. Marge adds extra fields (`marge_only`). |

### 2.1 Authentication

All endpoints require a valid Bearer token in the `Authorization` header, except `/api/health` which is unauthenticated. Token format: `Bearer <long-lived-access-token>`.

### 2.2 Content Type

All endpoints accept and return `application/json`. Template rendering returns `text/plain`.

---

## 3. REST API -- MARGE-ONLY ENDPOINTS

These REST endpoints exist on Marge but **not** on Home Assistant. Where HA provides equivalent functionality, it does so exclusively via WebSocket commands (listed in the "HA Equivalent (WS)" column). Marge implements both the REST endpoint and the WebSocket command.

CTS tests for these endpoints are tagged `@pytest.mark.marge_only` and skipped when the test target is HA.

### 3.1 History and Logbook

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/api/history/:entity_id` | GET | `history/history_during_period` | Entity state history with optional time range |
| `/api/logbook` | GET | `logbook/get_events` | Global logbook events |
| `/api/logbook/:entity_id` | GET | `logbook/get_events` | Logbook events for a single entity |
| `/api/statistics/:entity_id` | GET | `recorder/statistics_during_period` | Statistical aggregations (mean, min, max, sum) |

### 3.2 Registry Management (Areas, Labels, Devices)

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/api/areas` | GET | `config/area_registry/list` | List all areas |
| `/api/areas` | POST | `config/area_registry/create` | Create a new area |
| `/api/areas/:id` | PUT | `config/area_registry/update` | Update an area |
| `/api/areas/:id` | DELETE | `config/area_registry/delete` | Delete an area |
| `/api/labels` | GET | `config/label_registry/list` | List all labels |
| `/api/labels` | POST | `config/label_registry/create` | Create a new label |
| `/api/labels/:id` | DELETE | `config/label_registry/delete` | Delete a label |
| `/api/devices` | GET | `config/device_registry/list` | List all devices |

### 3.3 Configuration Introspection

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/api/config/automation/config` | GET | N/A | Parsed automation configuration |
| `/api/config/automation/yaml` | GET | N/A | Raw automation YAML |
| `/api/config/scene/config` | GET | N/A | Parsed scene configuration |
| `/api/config/scene/yaml` | GET | N/A | Raw scene YAML |
| `/api/automations/reload` | POST | `automation/reload` (service) | Trigger hot-reload of automation YAML |

### 3.4 Notifications and Search

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/api/notifications` | GET | `persistent_notification/subscribe` | List active persistent notifications |
| `/api/states/search` | GET | `search/related` (partial) | Entity search with domain, area, and label filters |

### 3.5 Operations

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/api/backup` | GET | N/A | Download backup tarball (tar.gz of DB + config) |
| `/api/restore` | POST | N/A | Upload and apply restore tarball |
| `/api/sim/time` | POST | N/A | Simulation time control (set/advance virtual clock) |

### 3.6 Infrastructure

| Endpoint | Method | HA Equivalent (WS) | Description |
|----------|--------|---------------------|-------------|
| `/metrics` | GET | N/A | Prometheus-format metrics |
| `/api/webhooks/:id` | POST | N/A | Webhook receiver (sets state + fires event) |
| `/api/integrations/*` | GET/POST | N/A | Bridge status and control per integration |
| `/api/auth/tokens` | GET/POST/DELETE | N/A | Long-lived access token management |
| `/api/users` | GET/POST/DELETE | N/A | Local user account management |

---

## 4. WEBSOCKET API -- IMPLEMENTED COMMANDS

Marge's WebSocket endpoint is `ws://<host>:8124/api/websocket`. The protocol follows HA's WebSocket API: JSON messages with `id`, `type`, and command-specific fields. Authentication uses the `auth` message type with `access_token`.

### 4.1 Core Commands

| Command | HA Compatible | Notes |
|---------|---------------|-------|
| `auth` | Yes | First message after connection. Returns `auth_ok` or `auth_invalid`. |
| `ping` | Yes | Returns `pong` with matching `id`. |
| `subscribe_events` | Yes | Subscribe to all events or a specific `event_type`. |
| `unsubscribe_events` | Yes | Unsubscribe by subscription ID. |
| `get_states` | Yes | Returns all entity states. |
| `call_service` | Yes | Call a service by domain and service name. |
| `fire_event` | Yes | Fire a custom event. |
| `get_services` | **DIVERGENT** | Marge returns list-of-dicts. HA returns `{domain: {service: {...}}}`. See Section 6. |
| `get_config` | Yes | Returns core configuration. |
| `render_template` | Yes | Render a Jinja2 template. Response format may differ from HA. |

### 4.2 Registry Commands

| Command | HA Compatible | Notes |
|---------|---------------|-------|
| `config/area_registry/list` | Yes | |
| `config/area_registry/create` | Yes | |
| `config/area_registry/update` | Yes | |
| `config/area_registry/delete` | Yes | |
| `config/device_registry/list` | Yes | |
| `config/entity_registry/list` | Yes | |
| `config/entity_registry/update` | Partial | Only supports `friendly_name`, `icon`, `area_id`. |
| `config/label_registry/list` | Yes | |
| `config/label_registry/create` | Yes | |
| `config/label_registry/delete` | Yes | |

### 4.3 Notification and UI Commands

| Command | HA Compatible | Notes |
|---------|---------------|-------|
| `get_notifications` | Marge-only | HA uses `persistent_notification/subscribe` instead. |
| `persistent_notification/dismiss` | Yes | |
| `lovelace/config` | Stub | Returns minimal empty config to prevent frontend errors. |
| `subscribe_trigger` | Partial | Basic trigger subscription. Not all trigger types supported. |

---

## 5. WEBSOCKET API -- MISSING HA COMMANDS (GAP LIST)

Commands that HA clients may expect but Marge does not yet implement. Prioritized by likelihood of being called by standard HA frontends and integrations.

### 5.1 Priority 1 -- Low Complexity, High Impact

These are registry operations that HA frontends call frequently. Each is a straightforward CRUD operation against an existing in-memory data structure.

| Command | Complexity | Description |
|---------|------------|-------------|
| `config/device_registry/update` | Low | Update device name, area, disabled_by |
| `config/entity_registry/get` | Low | Get a single entity's registry entry |
| `config/entity_registry/remove` | Low | Remove entity from registry |
| `config/label_registry/update` | Low | Update label name, color, icon |

### 5.2 Priority 2 -- Medium Complexity, REST Equivalent Exists

Marge already exposes these via REST. The WebSocket commands are needed for HA frontend compatibility but the underlying data layer exists.

| Command | Complexity | Description |
|---------|------------|-------------|
| `logbook/get_events` | Medium | Query logbook events (Marge has `/api/logbook`) |
| `history/history_during_period` | Medium | Query entity history (Marge has `/api/history/:entity_id`) |
| `history/list_statistic_ids` | Low | List available statistics identifiers |
| `history/statistics_during_period` | Medium | Query statistics (Marge has `/api/statistics/:entity_id`) |

### 5.3 Priority 3 -- Higher Complexity or Niche Usage

| Command | Complexity | Description |
|---------|------------|-------------|
| `logbook/event_stream` | High | Real-time logbook event streaming over WebSocket |
| `recorder/get_statistics_metadata` | Low | Metadata about recorded statistics |
| `search/related` | Medium | Find entities related by area, device, or integration |

---

## 6. KNOWN CONFORMANCE DIVERGENCES

Issues identified during Phase 9 dual-target CTS verification. Each entry documents the difference, its impact on client compatibility, and its current resolution status.

### 6.1 Fixed

| Issue | Impact | Resolution |
|-------|--------|------------|
| Service response format: Marge returned `{"changed_states": [...]}`, HA returns `[...]` | High -- breaks any client parsing service call responses | Fixed in Phase 9.3. Handler returns `Json<Vec<EntityState>>` directly. |

### 6.2 Open

| Issue | Impact | Status | Affected Tests |
|-------|--------|--------|----------------|
| WS `get_services` returns list-of-dicts, HA returns `{domain: {service: {...}}}` | Medium -- HA frontend parses the dict format | Open | 13 CTS tests |
| `POST /api/states` returns 200 for new entities, HA returns 201 | Low -- most clients ignore status code distinction | Open | 2 CTS tests |
| Context IDs use UUIDs (36 chars, dashes), HA uses ULIDs (26 chars, no dashes) | Low -- clients rarely parse context IDs | Open | 2 CTS tests |
| Template `int(3.14)` returns 3 (truncation), HA returns 0 (Jinja2 default) | Low -- edge case in template evaluation | Open | 7 CTS tests |
| Template `is_defined` returns the value itself, HA returns `true` | Low -- affects template conditionals | Open | (included in 7 above) |
| Service listing shows all 40+ static domains, HA only lists domains with loaded integrations | Low -- cosmetic difference in service explorer | Open | 23 CTS tests |

### 6.3 Conformance Metrics (Phase 9.7)

Dual-target CTS run against 1490 shared tests:

| Quadrant | Count | Percentage |
|----------|-------|------------|
| Both pass | 580 | 38.9% |
| Both fail | 1 | 0.1% |
| HA pass / Marge fail | 0 | 0.0% |
| Marge pass / HA fail | 909 | 61.0% |

The 0% HA-pass/Marge-fail rate means Marge passes every test that HA passes. The 909 Marge-pass/HA-fail tests break down into three buckets:

- **Bucket A** (285 tests, 31%): Marge-only endpoints. Need `marge_only` marker.
- **Bucket B** (555 tests, 61%): Tests create entities via `POST /api/states` then call services. HA rejects because entities are not registered with an integration platform. Marge is lenient. Tests need rewriting.
- **Bucket C** (69 tests, 8%): Real conformance bugs in Marge (the issues listed in Section 6.2).

---

## 7. REFERENCES

| Document | Identifier | Description |
|----------|------------|-------------|
| Service Replacement Methodology | MRG-SRM-001 | Socket-level shadow validation approach |
| Conformance Test Suite | MRG-CTS-001 | 1654 pytest tests across 125 files |
| Phase Tracker | `docs/phase-tracker.md` | Operational status of all implementation phases |
| Agent Memory | `docs/agent-memory.md` | Architectural decisions, gotchas, known issues |
| HA REST API Docs | `developers.home-assistant.io/docs/api/rest` | Official HA REST API reference |
| HA WebSocket API Docs | `developers.home-assistant.io/docs/api/websocket` | Official HA WebSocket API reference |

---

*End of document MRG-API-001.*
