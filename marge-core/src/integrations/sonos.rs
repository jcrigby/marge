#![allow(dead_code)]
//! Sonos speaker integration (Phase 7 SS 7.4)
//!
//! Supports Sonos speakers (Play:1, Play:5, Beam, Arc, Move, Era, etc.)
//! via their local HTTP API on port 1400.
//! - Device description: GET /xml/device_description.xml
//! - Zone player status: GET /status/zp
//! - Entity creation: media_player.sonos_{zone_name}
//! - Background poller for state synchronization

use std::sync::Arc;
use std::time::Duration;

use dashmap::DashMap;
use serde::Serialize;
use serde_json::Value;

use crate::api::AppState;

/// Supported features bitmask for media_player entities (HA-compatible).
/// These mirror Home Assistant's MediaPlayerEntityFeature values.
const SUPPORT_PAUSE: u32 = 1;
const SUPPORT_VOLUME_SET: u32 = 4;
const SUPPORT_VOLUME_MUTE: u32 = 8;
const SUPPORT_PLAY: u32 = 16384;
const SUPPORT_STOP: u32 = 4096;
const SUPPORT_PLAY_MEDIA: u32 = 512;
const SUPPORT_SELECT_SOURCE: u32 = 2048;
const SUPPORT_GROUPING: u32 = 524288;

/// Combined supported features for Sonos speakers.
const SONOS_SUPPORTED_FEATURES: u32 = SUPPORT_PAUSE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PLAY
    | SUPPORT_STOP
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_GROUPING;

/// A Sonos device tracked by the integration.
#[derive(Debug, Clone, Serialize)]
pub struct SonosDevice {
    pub ip: String,
    pub name: String,
    pub model: String,
    pub serial: String,
    pub software_version: String,
    pub uuid: String,
    pub zone_name: String,
    pub online: bool,
    pub last_seen: Option<String>,
    pub is_coordinator: bool,
    pub volume_level: f64,
    pub is_volume_muted: bool,
    pub source: String,
}

/// The Sonos integration manager.
pub struct SonosIntegration {
    /// Known devices keyed by UUID.
    devices: Arc<DashMap<String, SonosDevice>>,
    /// App state for entity creation.
    app: Arc<AppState>,
    /// HTTP client with timeout.
    client: reqwest::Client,
}

impl SonosIntegration {
    /// Create a new Sonos integration with a 3-second HTTP timeout.
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

    /// Probe a Sonos device at the given IP via GET /xml/device_description.xml.
    /// Parses the XML response with basic string matching (no XML parser dep).
    pub async fn add_device(&self, ip: &str) -> Result<SonosDevice, String> {
        let url = format!("http://{}:1400/xml/device_description.xml", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("Failed to reach Sonos at {}: {}", ip, e))?;

        let body = resp.text().await
            .map_err(|e| format!("Failed to read response from {}: {}", ip, e))?;

        // Parse key fields from the XML using basic string extraction.
        let zone_name = extract_xml_tag(&body, "roomName")
            .or_else(|| extract_xml_tag(&body, "friendlyName"))
            .unwrap_or_else(|| format!("Sonos {}", &ip[ip.len().saturating_sub(3)..]));
        let model = extract_xml_tag(&body, "modelName")
            .unwrap_or_else(|| "Sonos Speaker".to_string());
        let serial = extract_xml_tag(&body, "serialNum")
            .unwrap_or_else(|| "unknown".to_string());
        let software_version = extract_xml_tag(&body, "softwareVersion")
            .or_else(|| extract_xml_tag(&body, "hardwareVersion"))
            .unwrap_or_else(|| "unknown".to_string());
        let uuid = extract_xml_tag(&body, "UDN")
            .map(|u| u.trim_start_matches("uuid:").to_string())
            .unwrap_or_else(|| format!("sonos_{}", serial));
        let friendly_name = extract_xml_tag(&body, "friendlyName")
            .unwrap_or_else(|| zone_name.clone());

        // Check if the response looks like a Sonos device
        let is_sonos = body.contains("Sonos") || body.contains("sonos")
            || body.contains("rincon") || body.contains("Rincon");
        if !is_sonos {
            return Err(format!("Device at {} does not appear to be a Sonos speaker", ip));
        }

        let now = chrono::Utc::now().to_rfc3339();

        let device = SonosDevice {
            ip: ip.to_string(),
            name: friendly_name,
            model,
            serial,
            software_version,
            uuid: uuid.clone(),
            zone_name,
            online: true,
            last_seen: Some(now),
            is_coordinator: true,
            volume_level: 0.0,
            is_volume_muted: false,
            source: String::new(),
        };

        tracing::info!(
            uuid = %uuid,
            ip = %ip,
            zone = %device.zone_name,
            model = %device.model,
            "Sonos device discovered: {}",
            device.name,
        );

        // Create the media_player entity
        self.update_entity(&device);

        self.devices.insert(uuid, device.clone());
        Ok(device)
    }

    /// Poll a single device by UUID, checking reachability and updating state.
    pub async fn poll_device(&self, uuid: &str) {
        let device = match self.devices.get(uuid) {
            Some(d) => d.clone(),
            None => return,
        };

        let result = self.fetch_device_status(&device.ip).await;

        match result {
            Ok(updates) => {
                let now = chrono::Utc::now().to_rfc3339();
                self.devices.entry(uuid.to_string()).and_modify(|d| {
                    d.online = true;
                    d.last_seen = Some(now);
                    if let Some(vol) = updates.volume_level {
                        d.volume_level = vol;
                    }
                    if let Some(muted) = updates.is_volume_muted {
                        d.is_volume_muted = muted;
                    }
                    if let Some(source) = updates.source {
                        d.source = source;
                    }
                });

                // Re-read updated device for entity creation
                if let Some(updated) = self.devices.get(uuid) {
                    self.update_entity(&updated);
                }
            }
            Err(e) => {
                tracing::warn!(uuid = %uuid, ip = %device.ip, "Sonos poll failed: {}", e);
                self.devices.entry(uuid.to_string()).and_modify(|d| {
                    d.online = false;
                });

                // Update entity to unavailable
                if let Some(updated) = self.devices.get(uuid) {
                    self.update_entity(&updated);
                }
            }
        }
    }

    /// Fetch device status from the Sonos HTTP API.
    /// Uses /status/zp for zone player status.
    async fn fetch_device_status(&self, ip: &str) -> Result<DeviceStatusUpdate, String> {
        let url = format!("http://{}:1400/status/zp", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("HTTP error: {}", e))?;

        let body = resp.text().await
            .map_err(|e| format!("Read error: {}", e))?;

        // Parse basic status from the zone player status page.
        // The /status/zp page returns an HTML/XML page with zone info.
        let is_coordinator = body.contains("Coordinator") || body.contains("coordinator");

        Ok(DeviceStatusUpdate {
            volume_level: None,
            is_volume_muted: None,
            source: None,
            is_coordinator: Some(is_coordinator),
        })
    }

    /// Create or update the media_player entity for a Sonos device.
    fn update_entity(&self, device: &SonosDevice) {
        let slug = slugify(&device.zone_name);
        let entity_id = format!("media_player.sonos_{}", slug);

        let state = if !device.online {
            "unavailable"
        } else {
            "idle"
        };

        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String(device.zone_name.clone()));
        attrs.insert("integration".to_string(), Value::String("sonos".to_string()));
        attrs.insert("ip_address".to_string(), Value::String(device.ip.clone()));
        attrs.insert("model".to_string(), Value::String(device.model.clone()));
        attrs.insert("serial_number".to_string(), Value::String(device.serial.clone()));
        attrs.insert("software_version".to_string(), Value::String(device.software_version.clone()));
        attrs.insert("uuid".to_string(), Value::String(device.uuid.clone()));
        attrs.insert("volume_level".to_string(), serde_json::json!(device.volume_level));
        attrs.insert("is_volume_muted".to_string(), serde_json::json!(device.is_volume_muted));
        attrs.insert("source".to_string(), Value::String(device.source.clone()));
        attrs.insert("is_coordinator".to_string(), serde_json::json!(device.is_coordinator));
        attrs.insert("supported_features".to_string(), serde_json::json!(SONOS_SUPPORTED_FEATURES));
        attrs.insert("device_class".to_string(), Value::String("speaker".to_string()));

        self.app.state_machine.set(entity_id, state.to_string(), attrs);
    }

    // ── Service Command Stubs ───────────────────────────────

    /// Send a play command to a Sonos device.
    pub async fn media_play(&self, uuid: &str) -> Result<(), String> {
        let device = self.devices.get(uuid)
            .ok_or_else(|| format!("Unknown device: {}", uuid))?;
        let _url = format!("http://{}:1400/MediaRenderer/AVTransport/Control", device.ip);
        // In a real implementation, we'd send a SOAP action here.
        // Stub: just log the intent.
        tracing::debug!(uuid = %uuid, "media_play stub called");
        Ok(())
    }

    /// Send a pause command to a Sonos device.
    pub async fn media_pause(&self, uuid: &str) -> Result<(), String> {
        let device = self.devices.get(uuid)
            .ok_or_else(|| format!("Unknown device: {}", uuid))?;
        let _url = format!("http://{}:1400/MediaRenderer/AVTransport/Control", device.ip);
        tracing::debug!(uuid = %uuid, "media_pause stub called");
        Ok(())
    }

    /// Send a stop command to a Sonos device.
    pub async fn media_stop(&self, uuid: &str) -> Result<(), String> {
        let device = self.devices.get(uuid)
            .ok_or_else(|| format!("Unknown device: {}", uuid))?;
        let _url = format!("http://{}:1400/MediaRenderer/AVTransport/Control", device.ip);
        tracing::debug!(uuid = %uuid, "media_stop stub called");
        Ok(())
    }

    /// Set volume level (0.0 - 1.0) on a Sonos device.
    pub async fn volume_set(&self, uuid: &str, level: f64) -> Result<(), String> {
        let device = self.devices.get(uuid)
            .ok_or_else(|| format!("Unknown device: {}", uuid))?;
        let _url = format!("http://{}:1400/MediaRenderer/RenderingControl/Control", device.ip);
        let _volume = (level.clamp(0.0, 1.0) * 100.0) as u32;
        tracing::debug!(uuid = %uuid, level = %level, "volume_set stub called");

        // Update local state optimistically
        drop(device);
        self.devices.entry(uuid.to_string()).and_modify(|d| {
            d.volume_level = level.clamp(0.0, 1.0);
        });
        Ok(())
    }

    /// Set mute state on a Sonos device.
    pub async fn volume_mute(&self, uuid: &str, mute: bool) -> Result<(), String> {
        let device = self.devices.get(uuid)
            .ok_or_else(|| format!("Unknown device: {}", uuid))?;
        let _url = format!("http://{}:1400/MediaRenderer/RenderingControl/Control", device.ip);
        tracing::debug!(uuid = %uuid, mute = %mute, "volume_mute stub called");

        drop(device);
        self.devices.entry(uuid.to_string()).and_modify(|d| {
            d.is_volume_muted = mute;
        });
        Ok(())
    }

    /// List all known devices.
    pub fn devices(&self) -> Vec<SonosDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Number of tracked devices.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }
}

/// Partial device status from polling.
struct DeviceStatusUpdate {
    volume_level: Option<f64>,
    is_volume_muted: Option<bool>,
    source: Option<String>,
    is_coordinator: Option<bool>,
}

/// Extract the text content of an XML tag using basic string matching.
/// e.g. extract_xml_tag("<foo>bar</foo>", "foo") => Some("bar")
fn extract_xml_tag(xml: &str, tag: &str) -> Option<String> {
    let open = format!("<{}>", tag);
    let close = format!("</{}>", tag);

    let start = xml.find(&open)?;
    let content_start = start + open.len();
    let end = xml[content_start..].find(&close)?;

    let content = xml[content_start..content_start + end].trim().to_string();
    if content.is_empty() {
        None
    } else {
        Some(content)
    }
}

/// Convert a name to a URL/entity-safe slug.
fn slugify(name: &str) -> String {
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

/// Spawn a background tokio task that polls all known Sonos devices
/// at the specified interval.
pub fn start_sonos_poller(integration: Arc<SonosIntegration>, poll_interval_secs: u64) {
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

    fn make_integration() -> SonosIntegration {
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
        SonosIntegration::new(app)
    }

    #[test]
    fn test_new_integration_empty() {
        let sonos = make_integration();
        assert_eq!(sonos.device_count(), 0);
        assert!(sonos.devices().is_empty());
    }

    #[test]
    fn test_device_storage_and_count() {
        let sonos = make_integration();

        sonos.devices.insert("RINCON_001".to_string(), SonosDevice {
            ip: "192.168.1.80".to_string(),
            name: "Living Room - Sonos Play:5".to_string(),
            model: "Sonos Play:5".to_string(),
            serial: "AA-BB-CC-DD-EE-FF".to_string(),
            software_version: "78.1-43210".to_string(),
            uuid: "RINCON_001".to_string(),
            zone_name: "Living Room".to_string(),
            online: true,
            last_seen: None,
            is_coordinator: true,
            volume_level: 0.25,
            is_volume_muted: false,
            source: String::new(),
        });

        assert_eq!(sonos.device_count(), 1);

        sonos.devices.insert("RINCON_002".to_string(), SonosDevice {
            ip: "192.168.1.81".to_string(),
            name: "Kitchen - Sonos One".to_string(),
            model: "Sonos One".to_string(),
            serial: "11-22-33-44-55-66".to_string(),
            software_version: "78.1-43210".to_string(),
            uuid: "RINCON_002".to_string(),
            zone_name: "Kitchen".to_string(),
            online: true,
            last_seen: None,
            is_coordinator: true,
            volume_level: 0.50,
            is_volume_muted: false,
            source: String::new(),
        });

        assert_eq!(sonos.device_count(), 2);
        assert_eq!(sonos.devices().len(), 2);
    }

    #[test]
    fn test_entity_creation() {
        let sonos = make_integration();

        let device = SonosDevice {
            ip: "192.168.1.80".to_string(),
            name: "Living Room - Sonos Arc".to_string(),
            model: "Sonos Arc".to_string(),
            serial: "AA-BB-CC-DD-EE-FF".to_string(),
            software_version: "78.1-43210".to_string(),
            uuid: "RINCON_001".to_string(),
            zone_name: "Living Room".to_string(),
            online: true,
            last_seen: None,
            is_coordinator: true,
            volume_level: 0.35,
            is_volume_muted: false,
            source: "TV".to_string(),
        };

        sonos.update_entity(&device);

        let entity = sonos.app.state_machine.get("media_player.sonos_living_room");
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "idle");
        assert_eq!(
            entity.attributes.get("friendly_name").and_then(|v| v.as_str()),
            Some("Living Room")
        );
        assert_eq!(
            entity.attributes.get("integration").and_then(|v| v.as_str()),
            Some("sonos")
        );
        assert_eq!(
            entity.attributes.get("model").and_then(|v| v.as_str()),
            Some("Sonos Arc")
        );
        assert_eq!(
            entity.attributes.get("volume_level").and_then(|v| v.as_f64()),
            Some(0.35)
        );
        assert_eq!(
            entity.attributes.get("is_volume_muted").and_then(|v| v.as_bool()),
            Some(false)
        );
        assert_eq!(
            entity.attributes.get("source").and_then(|v| v.as_str()),
            Some("TV")
        );
        assert_eq!(
            entity.attributes.get("device_class").and_then(|v| v.as_str()),
            Some("speaker")
        );
        assert_eq!(
            entity.attributes.get("supported_features").and_then(|v| v.as_u64()),
            Some(SONOS_SUPPORTED_FEATURES as u64)
        );
    }

    #[test]
    fn test_unavailable_entity() {
        let sonos = make_integration();

        let device = SonosDevice {
            ip: "192.168.1.80".to_string(),
            name: "Bedroom - Sonos Move".to_string(),
            model: "Sonos Move".to_string(),
            serial: "FF-EE-DD-CC-BB-AA".to_string(),
            software_version: "78.1-43210".to_string(),
            uuid: "RINCON_003".to_string(),
            zone_name: "Bedroom".to_string(),
            online: false,
            last_seen: None,
            is_coordinator: false,
            volume_level: 0.0,
            is_volume_muted: false,
            source: String::new(),
        };

        sonos.update_entity(&device);

        let entity = sonos.app.state_machine.get("media_player.sonos_bedroom");
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "unavailable");
        assert_eq!(
            entity.attributes.get("is_coordinator").and_then(|v| v.as_bool()),
            Some(false)
        );
    }

    #[test]
    fn test_slugify() {
        assert_eq!(slugify("Living Room"), "living_room");
        assert_eq!(slugify("Kitchen"), "kitchen");
        assert_eq!(slugify("Master Bedroom"), "master_bedroom");
        assert_eq!(slugify("  Patio  "), "patio");
        assert_eq!(slugify("Home Theater #1"), "home_theater_1");
        assert_eq!(slugify("Sonos-Arc"), "sonos_arc");
    }

    #[test]
    fn test_extract_xml_tag() {
        let xml = r#"<root><roomName>Living Room</roomName><modelName>Sonos Arc</modelName></root>"#;
        assert_eq!(extract_xml_tag(xml, "roomName"), Some("Living Room".to_string()));
        assert_eq!(extract_xml_tag(xml, "modelName"), Some("Sonos Arc".to_string()));
        assert_eq!(extract_xml_tag(xml, "missing"), None);

        // Test with whitespace
        let xml2 = "<UDN>  uuid:RINCON_001  </UDN>";
        assert_eq!(extract_xml_tag(xml2, "UDN"), Some("uuid:RINCON_001".to_string()));

        // Test empty tag
        let xml3 = "<empty></empty>";
        assert_eq!(extract_xml_tag(xml3, "empty"), None);
    }

    #[test]
    fn test_supported_features_bitmask() {
        // Verify the bitmask includes all expected features
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_PAUSE != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_VOLUME_SET != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_VOLUME_MUTE != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_PLAY != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_STOP != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_PLAY_MEDIA != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_SELECT_SOURCE != 0);
        assert!(SONOS_SUPPORTED_FEATURES & SUPPORT_GROUPING != 0);
    }
}
