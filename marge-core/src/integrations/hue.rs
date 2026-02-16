#![allow(dead_code)]
//! Philips Hue Bridge integration (Phase 7 SS 7.2)
//!
//! Supports Hue Bridge REST API v2 (CLIP API) for lights, sensors, and groups.
//! - REST endpoints: /api/<username>/lights, /groups, /sensors
//! - Link button pairing: POST /api with {devicetype: "marge#instance"}
//! - Entity creation: light.hue_{bridge}_{name}, sensor.hue_{bridge}_{name}
//! - Background poller for state synchronization

use std::sync::Arc;
use std::time::Duration;

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::api::AppState;

/// A Philips Hue Bridge tracked by the integration.
#[derive(Debug, Clone, Serialize)]
pub struct HueBridge {
    pub ip: String,
    pub username: String,
    pub name: String,
    pub model_id: String,
    pub sw_version: String,
    pub online: bool,
    pub light_count: usize,
    pub sensor_count: usize,
    pub last_polled: Option<String>,
}

/// Response from POST /api (link button pairing).
#[derive(Debug, Deserialize)]
struct HuePairResponse {
    #[serde(default)]
    success: Option<HuePairSuccess>,
    #[serde(default)]
    error: Option<HuePairError>,
}

#[derive(Debug, Deserialize)]
struct HuePairSuccess {
    username: String,
}

#[derive(Debug, Deserialize)]
struct HuePairError {
    #[serde(rename = "type")]
    error_type: u32,
    description: String,
}

/// Bridge configuration response from /api/{username}/config.
#[derive(Debug, Deserialize)]
struct HueBridgeConfig {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    modelid: Option<String>,
    #[serde(default)]
    swversion: Option<String>,
    #[serde(default)]
    bridgeid: Option<String>,
}

/// Light state from /api/{username}/lights/{id}.
#[derive(Debug, Deserialize)]
struct HueLightState {
    #[serde(default)]
    on: Option<bool>,
    #[serde(default)]
    bri: Option<u8>,
    #[serde(default)]
    ct: Option<u32>,
    #[serde(default)]
    xy: Option<Vec<f64>>,
    #[serde(default)]
    reachable: Option<bool>,
}

/// Individual light from /api/{username}/lights.
#[derive(Debug, Deserialize)]
struct HueLight {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    state: Option<HueLightState>,
    #[serde(rename = "type", default)]
    light_type: Option<String>,
    #[serde(default)]
    modelid: Option<String>,
    #[serde(default)]
    manufacturername: Option<String>,
    #[serde(default)]
    uniqueid: Option<String>,
}

/// Individual sensor from /api/{username}/sensors.
#[derive(Debug, Deserialize)]
struct HueSensor {
    #[serde(default)]
    name: Option<String>,
    #[serde(rename = "type", default)]
    sensor_type: Option<String>,
    #[serde(default)]
    state: Option<Value>,
    #[serde(default)]
    modelid: Option<String>,
    #[serde(default)]
    manufacturername: Option<String>,
    #[serde(default)]
    uniqueid: Option<String>,
}

/// Light command for PUT /api/{username}/lights/{id}/state.
#[derive(Debug, Serialize, Default)]
pub struct HueLightCommand {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub on: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bri: Option<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ct: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub xy: Option<Vec<f64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transitiontime: Option<u16>,
}

/// The Hue integration manager.
pub struct HueIntegration {
    /// Known bridges keyed by IP address.
    bridges: Arc<DashMap<String, HueBridge>>,
    /// App state for entity creation.
    app: Arc<AppState>,
    /// HTTP client with timeout.
    client: reqwest::Client,
}

impl HueIntegration {
    /// Create a new Hue integration with a 5-second HTTP timeout.
    pub fn new(app: Arc<AppState>) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());

        Self {
            bridges: Arc::new(DashMap::new()),
            app,
            client,
        }
    }

    /// Initiate pairing with a Hue Bridge at the given IP.
    ///
    /// Requires the user to press the link button on the bridge first.
    /// POST /api with {devicetype: "marge#instance"} returns a username.
    pub async fn pair_bridge(&self, ip: &str) -> Result<String, String> {
        let url = format!("http://{}/api", ip);
        let payload = serde_json::json!({"devicetype": "marge#instance"});

        let resp = self.client.post(&url)
            .json(&payload)
            .send()
            .await
            .map_err(|e| format!("Failed to reach bridge at {}: {}", ip, e))?;

        let body: Vec<Value> = resp.json().await
            .map_err(|e| format!("Invalid pairing response from {}: {}", ip, e))?;

        // Hue API returns an array of objects
        if let Some(first) = body.first() {
            // Check for success
            if let Some(username) = first
                .get("success")
                .and_then(|s| s.get("username"))
                .and_then(|u| u.as_str())
            {
                tracing::info!(ip = %ip, "Hue bridge paired successfully");
                return Ok(username.to_string());
            }

            // Check for error
            if let Some(err) = first.get("error") {
                let desc = err.get("description")
                    .and_then(|d| d.as_str())
                    .unwrap_or("Unknown error");
                let error_type = err.get("type")
                    .and_then(|t| t.as_u64())
                    .unwrap_or(0);
                return Err(format!("Bridge error (type {}): {}", error_type, desc));
            }
        }

        Err("Unexpected response from bridge".to_string())
    }

    /// Add a pre-paired bridge by IP and username.
    /// Fetches bridge config and stores it in the bridges map.
    pub async fn add_bridge(&self, ip: &str, username: &str) -> Result<HueBridge, String> {
        let config_url = format!("http://{}/api/{}/config", ip, username);
        let resp = self.client.get(&config_url).send().await
            .map_err(|e| format!("Failed to reach bridge at {}: {}", ip, e))?;

        let config: HueBridgeConfig = resp.json().await
            .map_err(|e| format!("Invalid config response from {}: {}", ip, e))?;

        let bridge = HueBridge {
            ip: ip.to_string(),
            username: username.to_string(),
            name: config.name.unwrap_or_else(|| "Hue Bridge".to_string()),
            model_id: config.modelid.unwrap_or_else(|| "BSB002".to_string()),
            sw_version: config.swversion.unwrap_or_else(|| "unknown".to_string()),
            online: true,
            light_count: 0,
            sensor_count: 0,
            last_polled: None,
        };

        tracing::info!(
            ip = %ip,
            name = %bridge.name,
            model = %bridge.model_id,
            "Hue bridge added: {}",
            bridge.name,
        );

        self.bridges.insert(ip.to_string(), bridge.clone());
        Ok(bridge)
    }

    /// Poll a bridge for lights, sensors, and groups.
    /// Creates/updates Marge entities for each discovered device.
    pub async fn poll_bridge(&self, ip: &str) {
        let bridge = match self.bridges.get(ip) {
            Some(b) => b.clone(),
            None => return,
        };

        let bridge_slug = slugify(&bridge.name);

        // Poll lights
        let light_count = match self.poll_lights(ip, &bridge.username, &bridge_slug).await {
            Ok(n) => n,
            Err(e) => {
                tracing::warn!(ip = %ip, "Hue light poll failed: {}", e);
                self.bridges.entry(ip.to_string()).and_modify(|b| {
                    b.online = false;
                });
                return;
            }
        };

        // Poll sensors
        let sensor_count = match self.poll_sensors(ip, &bridge.username, &bridge_slug).await {
            Ok(n) => n,
            Err(e) => {
                tracing::warn!(ip = %ip, "Hue sensor poll failed: {}", e);
                0
            }
        };

        let now = chrono::Utc::now().to_rfc3339();
        self.bridges.entry(ip.to_string()).and_modify(|b| {
            b.online = true;
            b.light_count = light_count;
            b.sensor_count = sensor_count;
            b.last_polled = Some(now);
        });
    }

    /// Fetch lights from bridge and create/update Marge entities.
    async fn poll_lights(&self, ip: &str, username: &str, bridge_slug: &str) -> Result<usize, String> {
        let url = format!("http://{}/api/{}/lights", ip, username);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("HTTP error: {}", e))?;

        let lights: std::collections::HashMap<String, HueLight> = resp.json().await
            .map_err(|e| format!("JSON parse error: {}", e))?;

        let count = lights.len();

        for (light_id, light) in &lights {
            let name = light.name.as_deref().unwrap_or("unknown");
            let name_slug = slugify(name);
            let entity_id = format!("light.hue_{}_{}", bridge_slug, name_slug);

            let state_data = light.state.as_ref();
            let is_on = state_data
                .and_then(|s| s.on)
                .unwrap_or(false);
            let state = if is_on { "on" } else { "off" };

            let mut attrs = serde_json::Map::new();
            attrs.insert("friendly_name".to_string(), Value::String(name.to_string()));
            attrs.insert("integration".to_string(), Value::String("hue".to_string()));
            attrs.insert("bridge_ip".to_string(), Value::String(ip.to_string()));
            attrs.insert("hue_light_id".to_string(), Value::String(light_id.clone()));

            if let Some(light_type) = &light.light_type {
                attrs.insert("hue_type".to_string(), Value::String(light_type.clone()));
            }
            if let Some(model) = &light.modelid {
                attrs.insert("model_id".to_string(), Value::String(model.clone()));
            }
            if let Some(mfr) = &light.manufacturername {
                attrs.insert("manufacturer".to_string(), Value::String(mfr.clone()));
            }
            if let Some(uid) = &light.uniqueid {
                attrs.insert("unique_id".to_string(), Value::String(uid.clone()));
            }

            if let Some(state_data) = state_data {
                if let Some(bri) = state_data.bri {
                    attrs.insert("brightness".to_string(), serde_json::json!(bri));
                }
                if let Some(ct) = state_data.ct {
                    attrs.insert("color_temp".to_string(), serde_json::json!(ct));
                }
                if let Some(xy) = &state_data.xy {
                    if xy.len() == 2 {
                        attrs.insert("xy_color".to_string(), serde_json::json!(xy));
                    }
                }
                if let Some(reachable) = state_data.reachable {
                    attrs.insert("reachable".to_string(), serde_json::json!(reachable));
                }
            }

            self.app.state_machine.set(entity_id, state.to_string(), attrs);
        }

        Ok(count)
    }

    /// Fetch sensors from bridge and create/update Marge entities.
    async fn poll_sensors(&self, ip: &str, username: &str, bridge_slug: &str) -> Result<usize, String> {
        let url = format!("http://{}/api/{}/sensors", ip, username);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("HTTP error: {}", e))?;

        let sensors: std::collections::HashMap<String, HueSensor> = resp.json().await
            .map_err(|e| format!("JSON parse error: {}", e))?;

        let mut count = 0;

        for (_sensor_id, sensor) in &sensors {
            let name = sensor.name.as_deref().unwrap_or("unknown");
            let sensor_type = sensor.sensor_type.as_deref().unwrap_or("unknown");
            let name_slug = slugify(name);

            // Map Hue sensor types to entity types
            let (entity_id, state_value, device_class) = match sensor_type {
                "ZLLPresence" | "ZLLPresence " => {
                    let presence = sensor.state.as_ref()
                        .and_then(|s| s.get("presence"))
                        .and_then(|p| p.as_bool())
                        .unwrap_or(false);
                    let eid = format!("binary_sensor.hue_{}_{}", bridge_slug, name_slug);
                    let state = if presence { "on" } else { "off" };
                    (eid, state.to_string(), "motion")
                }
                "ZLLTemperature" => {
                    let temp = sensor.state.as_ref()
                        .and_then(|s| s.get("temperature"))
                        .and_then(|t| t.as_i64())
                        .unwrap_or(0);
                    // Hue reports temperature in 1/100 degree C
                    let temp_c = temp as f64 / 100.0;
                    let eid = format!("sensor.hue_{}_{}", bridge_slug, name_slug);
                    (eid, format!("{:.1}", temp_c), "temperature")
                }
                "ZLLLightLevel" => {
                    let light_level = sensor.state.as_ref()
                        .and_then(|s| s.get("lightlevel"))
                        .and_then(|l| l.as_u64())
                        .unwrap_or(0);
                    // Convert Hue light level (10000*log10(lux)+1) to lux
                    let lux = 10.0_f64.powf((light_level as f64 - 1.0) / 10000.0);
                    let eid = format!("sensor.hue_{}_{}", bridge_slug, name_slug);
                    (eid, format!("{:.1}", lux), "illuminance")
                }
                "Daylight" => {
                    let daylight = sensor.state.as_ref()
                        .and_then(|s| s.get("daylight"))
                        .and_then(|d| d.as_bool())
                        .unwrap_or(false);
                    let eid = format!("binary_sensor.hue_{}_{}", bridge_slug, name_slug);
                    let state = if daylight { "on" } else { "off" };
                    (eid, state.to_string(), "daylight")
                }
                // Skip CLIP and other non-physical sensor types
                _ if sensor_type.starts_with("CLIP") => continue,
                _ => {
                    let eid = format!("sensor.hue_{}_{}", bridge_slug, name_slug);
                    let state = sensor.state.as_ref()
                        .and_then(|s| s.get("status"))
                        .and_then(|st| st.as_i64())
                        .map(|v| v.to_string())
                        .unwrap_or_else(|| "unknown".to_string());
                    (eid, state, "none")
                }
            };

            let mut attrs = serde_json::Map::new();
            attrs.insert("friendly_name".to_string(), Value::String(name.to_string()));
            attrs.insert("integration".to_string(), Value::String("hue".to_string()));
            attrs.insert("bridge_ip".to_string(), Value::String(ip.to_string()));
            attrs.insert("device_class".to_string(), Value::String(device_class.to_string()));
            attrs.insert("hue_sensor_type".to_string(), Value::String(sensor_type.to_string()));

            if let Some(model) = &sensor.modelid {
                attrs.insert("model_id".to_string(), Value::String(model.clone()));
            }
            if let Some(mfr) = &sensor.manufacturername {
                attrs.insert("manufacturer".to_string(), Value::String(mfr.clone()));
            }
            if let Some(uid) = &sensor.uniqueid {
                attrs.insert("unique_id".to_string(), Value::String(uid.clone()));
            }

            // Add unit of measurement for temperature and light level
            match device_class {
                "temperature" => {
                    attrs.insert("unit_of_measurement".to_string(), Value::String("\u{00B0}C".to_string()));
                }
                "illuminance" => {
                    attrs.insert("unit_of_measurement".to_string(), Value::String("lx".to_string()));
                }
                _ => {}
            }

            self.app.state_machine.set(entity_id, state_value, attrs);
            count += 1;
        }

        Ok(count)
    }

    /// Send a light command to a specific light on a bridge.
    /// PUT /api/{username}/lights/{light_id}/state
    pub async fn send_light_command(
        &self,
        bridge_ip: &str,
        username: &str,
        light_id: &str,
        command: &HueLightCommand,
    ) -> Result<(), String> {
        let url = format!("http://{}/api/{}/lights/{}/state", bridge_ip, username, light_id);
        self.client.put(&url)
            .json(command)
            .send()
            .await
            .map_err(|e| format!("Light command failed: {}", e))?;
        Ok(())
    }

    /// List all known bridges.
    pub fn bridges(&self) -> Vec<HueBridge> {
        self.bridges.iter().map(|e| e.value().clone()).collect()
    }

    /// Number of tracked bridges.
    pub fn bridge_count(&self) -> usize {
        self.bridges.len()
    }

    /// Total device count across all bridges (lights + sensors).
    pub fn device_count(&self) -> usize {
        self.bridges.iter().map(|e| e.light_count + e.sensor_count).sum()
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

/// Spawn a background tokio task that polls all known Hue bridges
/// at the specified interval.
pub fn start_hue_poller(integration: Arc<HueIntegration>, poll_interval_secs: u64) {
    tokio::spawn(async move {
        let interval = Duration::from_secs(poll_interval_secs);
        loop {
            // Collect IPs of known bridges
            let ips: Vec<String> = integration.bridges
                .iter()
                .map(|e| e.key().clone())
                .collect();

            for ip in ips {
                integration.poll_bridge(&ip).await;
            }

            tokio::time::sleep(interval).await;
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_integration() -> HueIntegration {
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
        HueIntegration::new(app)
    }

    #[test]
    fn test_new_integration_empty() {
        let hue = make_integration();
        assert_eq!(hue.bridge_count(), 0);
        assert_eq!(hue.device_count(), 0);
        assert!(hue.bridges().is_empty());
    }

    #[test]
    fn test_bridge_storage() {
        let hue = make_integration();

        hue.bridges.insert("192.168.1.50".to_string(), HueBridge {
            ip: "192.168.1.50".to_string(),
            username: "testuser123".to_string(),
            name: "Living Room Bridge".to_string(),
            model_id: "BSB002".to_string(),
            sw_version: "1953188020".to_string(),
            online: true,
            light_count: 5,
            sensor_count: 3,
            last_polled: None,
        });

        assert_eq!(hue.bridge_count(), 1);
        assert_eq!(hue.device_count(), 8);

        let bridges = hue.bridges();
        assert_eq!(bridges.len(), 1);
        assert_eq!(bridges[0].name, "Living Room Bridge");
        assert_eq!(bridges[0].model_id, "BSB002");
    }

    #[test]
    fn test_light_entity_creation() {
        let hue = make_integration();

        // Simulate a light entity the way poll_lights would create it
        let entity_id = "light.hue_living_room_couch_lamp".to_string();
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String("Couch Lamp".to_string()));
        attrs.insert("integration".to_string(), Value::String("hue".to_string()));
        attrs.insert("bridge_ip".to_string(), Value::String("192.168.1.50".to_string()));
        attrs.insert("brightness".to_string(), serde_json::json!(254));
        attrs.insert("color_temp".to_string(), serde_json::json!(370));
        attrs.insert("xy_color".to_string(), serde_json::json!([0.4573, 0.41]));

        hue.app.state_machine.set(entity_id.clone(), "on".to_string(), attrs);

        let entity = hue.app.state_machine.get(&entity_id);
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "on");
        assert_eq!(
            entity.attributes.get("friendly_name").and_then(|v| v.as_str()),
            Some("Couch Lamp")
        );
        assert_eq!(
            entity.attributes.get("integration").and_then(|v| v.as_str()),
            Some("hue")
        );
        assert_eq!(
            entity.attributes.get("brightness").and_then(|v| v.as_u64()),
            Some(254)
        );
        assert_eq!(
            entity.attributes.get("color_temp").and_then(|v| v.as_u64()),
            Some(370)
        );
    }

    #[test]
    fn test_sensor_entity_creation() {
        let hue = make_integration();

        // Simulate a motion sensor entity
        let entity_id = "binary_sensor.hue_hallway_motion".to_string();
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String("Hallway Motion".to_string()));
        attrs.insert("integration".to_string(), Value::String("hue".to_string()));
        attrs.insert("device_class".to_string(), Value::String("motion".to_string()));
        attrs.insert("hue_sensor_type".to_string(), Value::String("ZLLPresence".to_string()));

        hue.app.state_machine.set(entity_id.clone(), "on".to_string(), attrs);

        let entity = hue.app.state_machine.get(&entity_id);
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "on");
        assert_eq!(
            entity.attributes.get("device_class").and_then(|v| v.as_str()),
            Some("motion")
        );
    }

    #[test]
    fn test_temperature_sensor_entity() {
        let hue = make_integration();

        // Simulate a temperature sensor (Hue reports in 1/100 C, we convert)
        let entity_id = "sensor.hue_office_temperature".to_string();
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String("Office Temperature".to_string()));
        attrs.insert("integration".to_string(), Value::String("hue".to_string()));
        attrs.insert("device_class".to_string(), Value::String("temperature".to_string()));
        attrs.insert("unit_of_measurement".to_string(), Value::String("\u{00B0}C".to_string()));

        hue.app.state_machine.set(entity_id.clone(), "22.5".to_string(), attrs);

        let entity = hue.app.state_machine.get(&entity_id);
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "22.5");
        assert_eq!(
            entity.attributes.get("unit_of_measurement").and_then(|v| v.as_str()),
            Some("\u{00B0}C")
        );
    }

    #[test]
    fn test_slugify() {
        assert_eq!(slugify("Living Room"), "living_room");
        assert_eq!(slugify("Couch Lamp #1"), "couch_lamp_1");
        assert_eq!(slugify("  Kitchen  "), "kitchen");
        assert_eq!(slugify("hallway-motion"), "hallway_motion");
        assert_eq!(slugify("BSB002"), "bsb002");
    }

    #[test]
    fn test_light_command_serialization() {
        let cmd = HueLightCommand {
            on: Some(true),
            bri: Some(200),
            ct: Some(370),
            xy: None,
            transitiontime: Some(4),
        };

        let json = serde_json::to_value(&cmd).unwrap();
        assert_eq!(json.get("on").and_then(|v| v.as_bool()), Some(true));
        assert_eq!(json.get("bri").and_then(|v| v.as_u64()), Some(200));
        assert_eq!(json.get("ct").and_then(|v| v.as_u64()), Some(370));
        assert!(json.get("xy").is_none()); // skipped when None
        assert_eq!(json.get("transitiontime").and_then(|v| v.as_u64()), Some(4));
    }
}
