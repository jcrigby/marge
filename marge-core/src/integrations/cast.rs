#![allow(dead_code)]
//! Google Cast integration (Phase 7 SS 7.3)
//!
//! Supports Chromecast, Google Home, Nest Hub, and other Cast-enabled devices.
//! - Device info via HTTP GET http://<ip>:8008/setup/eureka_info
//! - Entity creation: media_player.cast_{name}
//! - Background poller for reachability and state sync
//! - Service stubs for media_player commands (play, pause, stop, volume_set, volume_mute)

use std::sync::Arc;
use std::time::Duration;

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::api::AppState;

/// A Google Cast device tracked by the integration.
#[derive(Debug, Clone, Serialize)]
pub struct CastDevice {
    pub ip: String,
    pub name: String,
    pub model_name: String,
    pub mac: String,
    pub firmware: String,
    pub uuid: String,
    pub online: bool,
    pub last_seen: Option<String>,
}

/// Response from GET /setup/eureka_info on a Cast device.
#[derive(Debug, Deserialize)]
struct EurekaInfo {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    model_name: Option<String>,
    #[serde(default)]
    mac_address: Option<String>,
    #[serde(default)]
    cast_build_revision: Option<String>,
    #[serde(default)]
    ssdp_udn: Option<String>,
    #[serde(default)]
    ip_address: Option<String>,
    #[serde(default)]
    locale: Option<LocaleInfo>,
}

#[derive(Debug, Deserialize)]
struct LocaleInfo {
    #[serde(default)]
    display_string: Option<String>,
}

/// HA-compatible supported features bitmask for media_player.
/// See: https://developers.home-assistant.io/docs/entity_media_player/#supported-features
const SUPPORT_PAUSE: u32 = 1;
const SUPPORT_VOLUME_SET: u32 = 4;
const SUPPORT_VOLUME_MUTE: u32 = 8;
const SUPPORT_PLAY: u32 = 16384;
const SUPPORT_STOP: u32 = 4096;

/// Combined supported features for Cast media_player entities.
const CAST_SUPPORTED_FEATURES: u32 =
    SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_PLAY | SUPPORT_STOP;

/// The Google Cast integration manager.
pub struct CastIntegration {
    /// Known devices keyed by UUID.
    devices: Arc<DashMap<String, CastDevice>>,
    /// App state for entity creation.
    app: Arc<AppState>,
    /// HTTP client with timeout.
    client: reqwest::Client,
}

impl CastIntegration {
    /// Create a new Cast integration with a 3-second HTTP timeout.
    pub fn new(app: Arc<AppState>) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(3))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());

        Self {
            devices: Arc::new(DashMap::new()),
            app,
            client,
        }
    }

    /// Probe a Cast device at the given IP via GET /setup/eureka_info,
    /// store it in the devices map, and create a media_player entity.
    pub async fn add_device(&self, ip: &str) -> Result<CastDevice, String> {
        let url = format!("http://{}:8008/setup/eureka_info", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("Failed to reach Cast device at {}: {}", ip, e))?;

        let info: EurekaInfo = resp.json().await
            .map_err(|e| format!("Invalid eureka_info response from {}: {}", ip, e))?;

        let name = info.name.unwrap_or_else(|| "Cast Device".to_string());
        let model_name = info.model_name.unwrap_or_else(|| "Chromecast".to_string());
        let mac = info.mac_address.unwrap_or_else(|| "unknown".to_string());
        let firmware = info.cast_build_revision.unwrap_or_else(|| "unknown".to_string());
        let uuid = info.ssdp_udn
            .map(|u| u.trim_start_matches("uuid:").to_string())
            .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
        let now = chrono::Utc::now().to_rfc3339();

        let device = CastDevice {
            ip: ip.to_string(),
            name: name.clone(),
            model_name: model_name.clone(),
            mac,
            firmware,
            uuid: uuid.clone(),
            online: true,
            last_seen: Some(now),
        };

        tracing::info!(
            uuid = %uuid,
            ip = %ip,
            model = %model_name,
            "Cast device discovered: {}",
            name,
        );

        self.devices.insert(uuid.clone(), device.clone());

        // Create media_player entity
        self.create_media_player_entity(&device);

        Ok(device)
    }

    /// Create or update the media_player entity for a Cast device.
    fn create_media_player_entity(&self, device: &CastDevice) {
        let name_slug = slugify(&device.name);
        let entity_id = format!("media_player.cast_{}", name_slug);

        let state = if device.online { "idle" } else { "off" };

        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String(device.name.clone()));
        attrs.insert("integration".to_string(), Value::String("cast".to_string()));
        attrs.insert("device_ip".to_string(), Value::String(device.ip.clone()));
        attrs.insert("model_name".to_string(), Value::String(device.model_name.clone()));
        attrs.insert("firmware_version".to_string(), Value::String(device.firmware.clone()));
        attrs.insert("cast_uuid".to_string(), Value::String(device.uuid.clone()));
        attrs.insert("volume_level".to_string(), serde_json::json!(0.5));
        attrs.insert("is_volume_muted".to_string(), serde_json::json!(false));
        attrs.insert("media_content_type".to_string(), Value::String("".to_string()));
        attrs.insert("supported_features".to_string(), serde_json::json!(CAST_SUPPORTED_FEATURES));

        self.app.state_machine.set(entity_id, state.to_string(), attrs);
    }

    /// Poll a single device by UUID, checking reachability and updating state.
    pub async fn poll_device(&self, uuid: &str) {
        let device = match self.devices.get(uuid) {
            Some(d) => d.clone(),
            None => return,
        };

        let url = format!("http://{}:8008/setup/eureka_info", device.ip);
        match self.client.get(&url).send().await {
            Ok(resp) => {
                if resp.status().is_success() {
                    // Optionally update name/model from fresh info
                    if let Ok(info) = resp.json::<EurekaInfo>().await {
                        let now = chrono::Utc::now().to_rfc3339();
                        let updated_name = info.name.unwrap_or_else(|| device.name.clone());
                        let updated_model = info.model_name.unwrap_or_else(|| device.model_name.clone());
                        let updated_firmware = info.cast_build_revision.unwrap_or_else(|| device.firmware.clone());

                        self.devices.entry(uuid.to_string()).and_modify(|d| {
                            d.online = true;
                            d.last_seen = Some(now);
                            d.name = updated_name.clone();
                            d.model_name = updated_model.clone();
                            d.firmware = updated_firmware.clone();
                        });

                        // Update entity with fresh info
                        if let Some(d) = self.devices.get(uuid) {
                            self.create_media_player_entity(&d);
                        }
                    } else {
                        let now = chrono::Utc::now().to_rfc3339();
                        self.devices.entry(uuid.to_string()).and_modify(|d| {
                            d.online = true;
                            d.last_seen = Some(now);
                        });
                    }
                } else {
                    self.mark_offline(uuid);
                }
            }
            Err(e) => {
                tracing::warn!(uuid = %uuid, ip = %device.ip, "Cast poll failed: {}", e);
                self.mark_offline(uuid);
            }
        }
    }

    /// Mark a device offline and update its entity state.
    fn mark_offline(&self, uuid: &str) {
        self.devices.entry(uuid.to_string()).and_modify(|d| {
            d.online = false;
        });

        if let Some(device) = self.devices.get(uuid) {
            let name_slug = slugify(&device.name);
            let entity_id = format!("media_player.cast_{}", name_slug);

            // Preserve existing attributes but update state to "off"
            if let Some(existing) = self.app.state_machine.get(&entity_id) {
                self.app.state_machine.set(entity_id, "off".to_string(), existing.attributes);
            }
        }
    }

    /// Handle a media_player service call for a Cast entity.
    /// Returns Ok(()) if the command was accepted (even as a stub).
    pub fn handle_service(&self, entity_id: &str, service: &str, data: &Value) -> Result<(), String> {
        // Verify this is a cast entity
        let existing = self.app.state_machine.get(entity_id)
            .ok_or_else(|| format!("Entity {} not found", entity_id))?;

        let integration = existing.attributes.get("integration")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if integration != "cast" {
            return Err(format!("Entity {} is not a cast device", entity_id));
        }

        let mut attrs = existing.attributes.clone();

        match service {
            "media_play" => {
                let new_state = "playing".to_string();
                self.app.state_machine.set(entity_id.to_string(), new_state, attrs);
                tracing::debug!(entity = %entity_id, "Cast: media_play");
            }
            "media_pause" => {
                let new_state = "paused".to_string();
                self.app.state_machine.set(entity_id.to_string(), new_state, attrs);
                tracing::debug!(entity = %entity_id, "Cast: media_pause");
            }
            "media_stop" => {
                attrs.insert("media_content_type".to_string(), Value::String("".to_string()));
                let new_state = "idle".to_string();
                self.app.state_machine.set(entity_id.to_string(), new_state, attrs);
                tracing::debug!(entity = %entity_id, "Cast: media_stop");
            }
            "volume_set" => {
                if let Some(level) = data.get("volume_level").and_then(|v| v.as_f64()) {
                    let clamped = level.clamp(0.0, 1.0);
                    attrs.insert("volume_level".to_string(), serde_json::json!(clamped));
                    self.app.state_machine.set(entity_id.to_string(), existing.state, attrs);
                    tracing::debug!(entity = %entity_id, volume = clamped, "Cast: volume_set");
                }
            }
            "volume_mute" => {
                if let Some(mute) = data.get("is_volume_muted").and_then(|v| v.as_bool()) {
                    attrs.insert("is_volume_muted".to_string(), serde_json::json!(mute));
                    self.app.state_machine.set(entity_id.to_string(), existing.state, attrs);
                    tracing::debug!(entity = %entity_id, muted = mute, "Cast: volume_mute");
                }
            }
            "turn_off" => {
                self.app.state_machine.set(entity_id.to_string(), "off".to_string(), attrs);
                tracing::debug!(entity = %entity_id, "Cast: turn_off");
            }
            "turn_on" => {
                self.app.state_machine.set(entity_id.to_string(), "idle".to_string(), attrs);
                tracing::debug!(entity = %entity_id, "Cast: turn_on");
            }
            other => {
                tracing::warn!(entity = %entity_id, service = %other, "Cast: unsupported service");
                return Err(format!("Unsupported Cast service: {}", other));
            }
        }

        Ok(())
    }

    /// List all known devices.
    pub fn devices(&self) -> Vec<CastDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Number of tracked devices.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }
}

/// Convert a name to a URL/entity-safe slug.
pub fn slugify(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { '_' })
        .collect::<String>()
        .trim_matches('_')
        .to_string()
        // Collapse multiple underscores
        .split('_')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

/// Spawn a background tokio task that polls all known Cast devices
/// at the specified interval.
pub fn start_cast_poller(integration: Arc<CastIntegration>, poll_interval_secs: u64) {
    tokio::spawn(async move {
        let interval = Duration::from_secs(poll_interval_secs);
        loop {
            // Collect UUIDs of known devices
            let uuids: Vec<String> = integration.devices
                .iter()
                .map(|e| e.key().clone())
                .collect();

            for uuid in uuids {
                integration.poll_device(&uuid).await;
            }

            tokio::time::sleep(interval).await;
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_integration() -> CastIntegration {
        let app = Arc::new(AppState {
            state_machine: StateMachine::new(256),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
            ws_connections: std::sync::atomic::AtomicU32::new(0),
            plugin_count: std::sync::atomic::AtomicUsize::new(0),
        });
        CastIntegration::new(app)
    }

    #[test]
    fn test_new_integration_empty() {
        let cast = make_integration();
        assert_eq!(cast.device_count(), 0);
        assert!(cast.devices().is_empty());
    }

    #[test]
    fn test_slugify() {
        assert_eq!(slugify("Living Room Speaker"), "living_room_speaker");
        assert_eq!(slugify("Kitchen Display #2"), "kitchen_display_2");
        assert_eq!(slugify("  Nest Hub  "), "nest_hub");
        assert_eq!(slugify("Chromecast-Ultra"), "chromecast_ultra");
        assert_eq!(slugify("my.device"), "my_device");
    }

    #[test]
    fn test_device_storage_and_entity_creation() {
        let cast = make_integration();

        let device = CastDevice {
            ip: "192.168.1.200".to_string(),
            name: "Living Room Speaker".to_string(),
            model_name: "Google Home".to_string(),
            mac: "AA:BB:CC:DD:EE:FF".to_string(),
            firmware: "1.56.270000".to_string(),
            uuid: "test-uuid-1234".to_string(),
            online: true,
            last_seen: Some(chrono::Utc::now().to_rfc3339()),
        };

        cast.devices.insert(device.uuid.clone(), device.clone());
        cast.create_media_player_entity(&device);

        assert_eq!(cast.device_count(), 1);

        let entity = cast.app.state_machine.get("media_player.cast_living_room_speaker");
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "idle");
        assert_eq!(
            entity.attributes.get("friendly_name").and_then(|v| v.as_str()),
            Some("Living Room Speaker")
        );
        assert_eq!(
            entity.attributes.get("integration").and_then(|v| v.as_str()),
            Some("cast")
        );
        assert_eq!(
            entity.attributes.get("model_name").and_then(|v| v.as_str()),
            Some("Google Home")
        );
        assert_eq!(
            entity.attributes.get("volume_level").and_then(|v| v.as_f64()),
            Some(0.5)
        );
        assert_eq!(
            entity.attributes.get("is_volume_muted").and_then(|v| v.as_bool()),
            Some(false)
        );
        assert_eq!(
            entity.attributes.get("supported_features").and_then(|v| v.as_u64()),
            Some(CAST_SUPPORTED_FEATURES as u64)
        );
    }

    #[test]
    fn test_service_media_play_pause_stop() {
        let cast = make_integration();

        // Create a device and entity
        let device = CastDevice {
            ip: "192.168.1.201".to_string(),
            name: "Bedroom TV".to_string(),
            model_name: "Chromecast".to_string(),
            mac: "11:22:33:44:55:66".to_string(),
            firmware: "1.56.270000".to_string(),
            uuid: "test-uuid-5678".to_string(),
            online: true,
            last_seen: None,
        };
        cast.devices.insert(device.uuid.clone(), device.clone());
        cast.create_media_player_entity(&device);

        let entity_id = "media_player.cast_bedroom_tv";

        // Play
        cast.handle_service(entity_id, "media_play", &serde_json::json!({})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(entity.state, "playing");

        // Pause
        cast.handle_service(entity_id, "media_pause", &serde_json::json!({})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(entity.state, "paused");

        // Stop
        cast.handle_service(entity_id, "media_stop", &serde_json::json!({})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(entity.state, "idle");
    }

    #[test]
    fn test_service_volume_set_and_mute() {
        let cast = make_integration();

        let device = CastDevice {
            ip: "192.168.1.202".to_string(),
            name: "Kitchen Hub".to_string(),
            model_name: "Nest Hub".to_string(),
            mac: "AA:BB:CC:DD:EE:00".to_string(),
            firmware: "2.0.0".to_string(),
            uuid: "test-uuid-vol".to_string(),
            online: true,
            last_seen: None,
        };
        cast.devices.insert(device.uuid.clone(), device.clone());
        cast.create_media_player_entity(&device);

        let entity_id = "media_player.cast_kitchen_hub";

        // Volume set
        cast.handle_service(entity_id, "volume_set", &serde_json::json!({"volume_level": 0.8})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(
            entity.attributes.get("volume_level").and_then(|v| v.as_f64()),
            Some(0.8)
        );

        // Volume clamp (> 1.0)
        cast.handle_service(entity_id, "volume_set", &serde_json::json!({"volume_level": 1.5})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(
            entity.attributes.get("volume_level").and_then(|v| v.as_f64()),
            Some(1.0)
        );

        // Mute
        cast.handle_service(entity_id, "volume_mute", &serde_json::json!({"is_volume_muted": true})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(
            entity.attributes.get("is_volume_muted").and_then(|v| v.as_bool()),
            Some(true)
        );

        // Unmute
        cast.handle_service(entity_id, "volume_mute", &serde_json::json!({"is_volume_muted": false})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(
            entity.attributes.get("is_volume_muted").and_then(|v| v.as_bool()),
            Some(false)
        );
    }

    #[test]
    fn test_service_turn_on_off() {
        let cast = make_integration();

        let device = CastDevice {
            ip: "192.168.1.203".to_string(),
            name: "Office Speaker".to_string(),
            model_name: "Google Home Mini".to_string(),
            mac: "FF:EE:DD:CC:BB:AA".to_string(),
            firmware: "1.50.0".to_string(),
            uuid: "test-uuid-onoff".to_string(),
            online: true,
            last_seen: None,
        };
        cast.devices.insert(device.uuid.clone(), device.clone());
        cast.create_media_player_entity(&device);

        let entity_id = "media_player.cast_office_speaker";

        // Turn off
        cast.handle_service(entity_id, "turn_off", &serde_json::json!({})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(entity.state, "off");

        // Turn on
        cast.handle_service(entity_id, "turn_on", &serde_json::json!({})).unwrap();
        let entity = cast.app.state_machine.get(entity_id).unwrap();
        assert_eq!(entity.state, "idle");
    }

    #[test]
    fn test_mark_offline_updates_entity() {
        let cast = make_integration();

        let device = CastDevice {
            ip: "192.168.1.204".to_string(),
            name: "Garage Speaker".to_string(),
            model_name: "Chromecast Audio".to_string(),
            mac: "00:11:22:33:44:55".to_string(),
            firmware: "1.40.0".to_string(),
            uuid: "test-uuid-offline".to_string(),
            online: true,
            last_seen: None,
        };
        cast.devices.insert(device.uuid.clone(), device.clone());
        cast.create_media_player_entity(&device);

        // Verify online
        let entity = cast.app.state_machine.get("media_player.cast_garage_speaker").unwrap();
        assert_eq!(entity.state, "idle");

        // Mark offline
        cast.mark_offline("test-uuid-offline");

        let device_ref = cast.devices.get("test-uuid-offline").unwrap();
        assert!(!device_ref.online);

        let entity = cast.app.state_machine.get("media_player.cast_garage_speaker").unwrap();
        assert_eq!(entity.state, "off");
    }

    #[test]
    fn test_eureka_info_parse() {
        let json = r#"{
            "name": "Living Room TV",
            "model_name": "Chromecast Ultra",
            "mac_address": "A4:77:33:11:22:33",
            "cast_build_revision": "1.56.270000",
            "ssdp_udn": "uuid:abcd-1234-efgh-5678",
            "ip_address": "192.168.1.100",
            "locale": {"display_string": "en-US"}
        }"#;
        let info: EurekaInfo = serde_json::from_str(json).unwrap();
        assert_eq!(info.name.as_deref(), Some("Living Room TV"));
        assert_eq!(info.model_name.as_deref(), Some("Chromecast Ultra"));
        assert_eq!(info.mac_address.as_deref(), Some("A4:77:33:11:22:33"));
        assert_eq!(info.cast_build_revision.as_deref(), Some("1.56.270000"));
        assert_eq!(info.ssdp_udn.as_deref(), Some("uuid:abcd-1234-efgh-5678"));
        assert_eq!(info.locale.unwrap().display_string.as_deref(), Some("en-US"));
    }
}
