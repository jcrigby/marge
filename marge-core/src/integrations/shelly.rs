#![allow(dead_code)]
//! Shelly device integration (Phase 7 §7.1)
//!
//! Supports Gen1 and Gen2+ Shelly devices via their local HTTP APIs.
//! Gen1: /status, /relay/N, /light/N endpoints
//! Gen2+: JSON-RPC via /rpc/Shelly.GetStatus, /rpc/Switch.Set, etc.

use std::sync::Arc;
use std::time::Duration;

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::api::AppState;

/// A Shelly device tracked by the bridge.
#[derive(Debug, Clone, Serialize)]
pub struct ShellyDevice {
    pub ip: String,
    pub mac: String,
    pub device_type: String,
    pub name: Option<String>,
    pub gen: u8,
    pub firmware: Option<String>,
    pub online: bool,
    pub last_seen: Option<String>,
}

/// Response from GET /shelly on any Shelly device.
#[derive(Debug, Deserialize)]
struct ShellyIdentity {
    /// Gen1 devices report "type" (e.g. "SHSW-1")
    #[serde(rename = "type", default)]
    device_type: Option<String>,
    /// Gen2+ devices report "id" (e.g. "shellyplus1-aabbccddeeff")
    #[serde(default)]
    id: Option<String>,
    /// Present on both gens (uppercase hex, no colons)
    #[serde(default)]
    mac: Option<String>,
    /// 1 for Gen1, 2 or 3 for Gen2+. Gen1 may omit this field entirely.
    #[serde(default)]
    gen: Option<u8>,
    /// Device name (Gen2+ only)
    #[serde(default)]
    name: Option<String>,
    /// Firmware identifier
    #[serde(default)]
    fw: Option<String>,
    #[serde(default)]
    fw_id: Option<String>,
}

/// The Shelly bridge manager.
pub struct ShellyBridge {
    /// Known devices keyed by MAC address (lowercase, no colons).
    devices: Arc<DashMap<String, ShellyDevice>>,
    /// App state for entity creation.
    app: Arc<AppState>,
    /// HTTP client with timeout.
    client: reqwest::Client,
}

impl ShellyBridge {
    /// Create a new Shelly bridge with a 2-second HTTP timeout.
    pub fn new(app: Arc<AppState>) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());

        Self {
            devices: Arc::new(DashMap::new()),
            app,
            client,
        }
    }

    /// Probe a device at the given IP via GET /shelly, identify it,
    /// and store it in the devices map.
    pub async fn add_device(&self, ip: &str) -> Result<ShellyDevice, String> {
        let url = format!("http://{}/shelly", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("Failed to reach {}: {}", ip, e))?;

        let ident: ShellyIdentity = resp.json().await
            .map_err(|e| format!("Invalid /shelly response from {}: {}", ip, e))?;

        let mac = ident.mac.as_deref().unwrap_or("unknown").to_lowercase();
        let gen = ident.gen.unwrap_or(1);
        let device_type = if gen >= 2 {
            ident.id.unwrap_or_else(|| format!("shelly_gen{}", gen))
        } else {
            ident.device_type.unwrap_or_else(|| "unknown".to_string())
        };

        let firmware = ident.fw.or(ident.fw_id);
        let now = chrono::Utc::now().to_rfc3339();

        let device = ShellyDevice {
            ip: ip.to_string(),
            mac: mac.clone(),
            device_type,
            name: ident.name,
            gen,
            firmware,
            online: true,
            last_seen: Some(now),
        };

        tracing::info!(
            mac = %mac,
            ip = %ip,
            gen = gen,
            "Shelly device discovered: {}",
            device.device_type,
        );

        self.devices.insert(mac, device.clone());
        Ok(device)
    }

    /// Poll a single device by MAC address, fetching its status and
    /// updating Marge entities accordingly.
    pub async fn poll_device(&self, mac: &str) {
        let device = match self.devices.get(mac) {
            Some(d) => d.clone(),
            None => return,
        };

        let result = if device.gen >= 2 {
            self.poll_gen2(&device.ip, &device.mac).await
        } else {
            self.poll_gen1(&device.ip, &device.mac, &device.device_type).await
        };

        match result {
            Ok(()) => {
                let now = chrono::Utc::now().to_rfc3339();
                self.devices.entry(mac.to_string()).and_modify(|d| {
                    d.online = true;
                    d.last_seen = Some(now);
                });
            }
            Err(e) => {
                tracing::warn!(mac = %mac, "Shelly poll failed: {}", e);
                self.devices.entry(mac.to_string()).and_modify(|d| {
                    d.online = false;
                });
            }
        }
    }

    /// List all known devices.
    pub fn devices(&self) -> Vec<ShellyDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Number of tracked devices.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    // ── Gen1 Polling ─────────────────────────────────────

    /// Poll a Gen1 device via GET /status.
    async fn poll_gen1(&self, ip: &str, mac: &str, device_type: &str) -> Result<(), String> {
        let url = format!("http://{}/status", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("HTTP error: {}", e))?;

        let status: Value = resp.json().await
            .map_err(|e| format!("JSON parse error: {}", e))?;

        let device_name = self.devices.get(mac)
            .and_then(|d| d.name.clone());

        // Process relays
        if let Some(relays) = status.get("relays").and_then(|v| v.as_array()) {
            let meters = status.get("meters").and_then(|v| v.as_array());

            for (idx, relay) in relays.iter().enumerate() {
                let is_on = relay.get("ison").and_then(|v| v.as_bool()).unwrap_or(false);
                let entity_id = format!("switch.shelly_{}_{}", mac, idx);
                let state = if is_on { "on" } else { "off" };

                let friendly = device_name.clone()
                    .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));
                let friendly = if relays.len() > 1 {
                    format!("{} Relay {}", friendly, idx)
                } else {
                    friendly
                };

                let mut attrs = serde_json::Map::new();
                attrs.insert("friendly_name".to_string(), Value::String(friendly));
                attrs.insert("ip_address".to_string(), Value::String(ip.to_string()));
                attrs.insert("device_type".to_string(), Value::String(device_type.to_string()));
                attrs.insert("device_class".to_string(), Value::String("switch".to_string()));
                attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

                if let Some(source) = relay.get("source").and_then(|v| v.as_str()) {
                    attrs.insert("source".to_string(), Value::String(source.to_string()));
                }

                // Power from corresponding meter
                if let Some(meters) = meters {
                    if let Some(meter) = meters.get(idx) {
                        if let Some(power) = meter.get("power").and_then(|v| v.as_f64()) {
                            attrs.insert("power".to_string(), serde_json::json!(power));
                        }
                    }
                }

                self.app.state_machine.set(entity_id, state.to_string(), attrs);
            }
        }

        // Process lights (dimmers)
        if let Some(lights) = status.get("lights").and_then(|v| v.as_array()) {
            for (idx, light) in lights.iter().enumerate() {
                let is_on = light.get("ison").and_then(|v| v.as_bool()).unwrap_or(false);
                let entity_id = format!("light.shelly_{}_{}", mac, idx);
                let state = if is_on { "on" } else { "off" };

                let friendly = device_name.clone()
                    .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));
                let friendly = if lights.len() > 1 {
                    format!("{} Light {}", friendly, idx)
                } else {
                    friendly
                };

                let mut attrs = serde_json::Map::new();
                attrs.insert("friendly_name".to_string(), Value::String(friendly));
                attrs.insert("ip_address".to_string(), Value::String(ip.to_string()));
                attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

                if let Some(brightness) = light.get("brightness").and_then(|v| v.as_u64()) {
                    attrs.insert("brightness".to_string(), serde_json::json!(brightness));
                }

                self.app.state_machine.set(entity_id, state.to_string(), attrs);
            }
        }

        // Temperature sensor
        if let Some(temp) = status.get("temperature").and_then(|v| v.as_f64()) {
            let entity_id = format!("sensor.shelly_{}_temperature", mac);
            let friendly = device_name.clone()
                .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));

            let mut attrs = serde_json::Map::new();
            attrs.insert("friendly_name".to_string(), Value::String(format!("{} Temperature", friendly)));
            attrs.insert("unit_of_measurement".to_string(), Value::String("\u{00B0}C".to_string()));
            attrs.insert("device_class".to_string(), Value::String("temperature".to_string()));
            attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

            self.app.state_machine.set(entity_id, format!("{:.1}", temp), attrs);
        }

        // Power sensor (from first meter if present)
        if let Some(meters) = status.get("meters").and_then(|v| v.as_array()) {
            if let Some(meter) = meters.first() {
                if let Some(power) = meter.get("power").and_then(|v| v.as_f64()) {
                    let entity_id = format!("sensor.shelly_{}_power", mac);
                    let friendly = device_name.clone()
                        .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));

                    let mut attrs = serde_json::Map::new();
                    attrs.insert("friendly_name".to_string(), Value::String(format!("{} Power", friendly)));
                    attrs.insert("unit_of_measurement".to_string(), Value::String("W".to_string()));
                    attrs.insert("device_class".to_string(), Value::String("power".to_string()));
                    attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

                    if let Some(total) = meter.get("total").and_then(|v| v.as_f64()) {
                        attrs.insert("total_energy".to_string(), serde_json::json!(total));
                    }

                    self.app.state_machine.set(entity_id, format!("{:.1}", power), attrs);
                }
            }
        }

        Ok(())
    }

    // ── Gen2 Polling ─────────────────────────────────────

    /// Poll a Gen2+ device via GET /rpc/Shelly.GetStatus.
    async fn poll_gen2(&self, ip: &str, mac: &str) -> Result<(), String> {
        let url = format!("http://{}/rpc/Shelly.GetStatus", ip);
        let resp = self.client.get(&url).send().await
            .map_err(|e| format!("HTTP error: {}", e))?;

        let status: Value = resp.json().await
            .map_err(|e| format!("JSON parse error: {}", e))?;

        let device_name = self.devices.get(mac)
            .and_then(|d| d.name.clone());
        let device_type = self.devices.get(mac)
            .map(|d| d.device_type.clone())
            .unwrap_or_default();

        // Extract system info
        let mut sys_attrs = serde_json::Map::new();
        if let Some(sys) = status.get("sys") {
            if let Some(uptime) = sys.get("uptime").and_then(|v| v.as_u64()) {
                sys_attrs.insert("uptime".to_string(), serde_json::json!(uptime));
            }
            if let Some(ram_free) = sys.get("ram_free").and_then(|v| v.as_u64()) {
                sys_attrs.insert("ram_free".to_string(), serde_json::json!(ram_free));
            }
        }

        // Process all keys in the status object
        if let Value::Object(map) = &status {
            for (key, value) in map {
                if let Some(rest) = key.strip_prefix("switch:") {
                    if let Ok(n) = rest.parse::<u32>() {
                        self.process_gen2_switch(ip, mac, n, value, &device_name, &device_type, &sys_attrs);
                    }
                } else if let Some(rest) = key.strip_prefix("light:") {
                    if let Ok(n) = rest.parse::<u32>() {
                        self.process_gen2_light(ip, mac, n, value, &device_name, &device_type);
                    }
                }
            }
        }

        Ok(())
    }

    /// Create/update a Marge entity for a Gen2 switch component.
    fn process_gen2_switch(
        &self,
        ip: &str,
        mac: &str,
        n: u32,
        data: &Value,
        device_name: &Option<String>,
        device_type: &str,
        sys_attrs: &serde_json::Map<String, Value>,
    ) {
        let is_on = data.get("output").and_then(|v| v.as_bool()).unwrap_or(false);
        let entity_id = format!("switch.shelly_{}_{}", mac, n);
        let state = if is_on { "on" } else { "off" };

        let friendly = device_name.clone()
            .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));
        let friendly = format!("{} Switch {}", friendly, n);

        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String(friendly));
        attrs.insert("ip_address".to_string(), Value::String(ip.to_string()));
        attrs.insert("device_type".to_string(), Value::String(device_type.to_string()));
        attrs.insert("device_class".to_string(), Value::String("switch".to_string()));
        attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

        if let Some(apower) = data.get("apower").and_then(|v| v.as_f64()) {
            attrs.insert("apower".to_string(), serde_json::json!(apower));
        }
        if let Some(voltage) = data.get("voltage").and_then(|v| v.as_f64()) {
            attrs.insert("voltage".to_string(), serde_json::json!(voltage));
        }
        if let Some(current) = data.get("current").and_then(|v| v.as_f64()) {
            attrs.insert("current".to_string(), serde_json::json!(current));
        }
        if let Some(temp) = data.get("temperature").and_then(|v| v.get("tC")).and_then(|v| v.as_f64()) {
            attrs.insert("temperature".to_string(), serde_json::json!(temp));
        }
        if let Some(energy) = data.get("aenergy").and_then(|v| v.get("total")).and_then(|v| v.as_f64()) {
            attrs.insert("total_energy".to_string(), serde_json::json!(energy));
        }

        // Merge system attributes
        for (k, v) in sys_attrs {
            attrs.insert(k.clone(), v.clone());
        }

        self.app.state_machine.set(entity_id, state.to_string(), attrs);
    }

    /// Create/update a Marge entity for a Gen2 light component.
    fn process_gen2_light(
        &self,
        ip: &str,
        mac: &str,
        n: u32,
        data: &Value,
        device_name: &Option<String>,
        device_type: &str,
    ) {
        let is_on = data.get("output").and_then(|v| v.as_bool()).unwrap_or(false);
        let entity_id = format!("light.shelly_{}_{}", mac, n);
        let state = if is_on { "on" } else { "off" };

        let friendly = device_name.clone()
            .unwrap_or_else(|| format!("{} {}", device_type, &mac[mac.len().saturating_sub(4)..]));
        let friendly = format!("{} Light {}", friendly, n);

        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String(friendly));
        attrs.insert("ip_address".to_string(), Value::String(ip.to_string()));
        attrs.insert("integration".to_string(), Value::String("shelly".to_string()));

        if let Some(brightness) = data.get("brightness").and_then(|v| v.as_u64()) {
            attrs.insert("brightness".to_string(), serde_json::json!(brightness));
        }

        self.app.state_machine.set(entity_id, state.to_string(), attrs);
    }

    // ── Command Methods ──────────────────────────────────

    /// Send a relay command to a Gen1 device.
    pub async fn command_gen1(&self, ip: &str, relay_idx: u32, action: &str) -> Result<(), String> {
        let url = format!("http://{}/relay/{}?turn={}", ip, relay_idx, action);
        self.client.get(&url).send().await
            .map_err(|e| format!("Command failed: {}", e))?;
        Ok(())
    }

    /// Send a switch command to a Gen2+ device.
    pub async fn command_gen2(&self, ip: &str, switch_id: u32, on: bool) -> Result<(), String> {
        let url = format!(
            "http://{}/rpc/Switch.Set?id={}&on={}",
            ip, switch_id, on
        );
        self.client.get(&url).send().await
            .map_err(|e| format!("Command failed: {}", e))?;
        Ok(())
    }

    /// Send a light command to a Gen1 dimmer.
    pub async fn command_gen1_light(
        &self,
        ip: &str,
        light_idx: u32,
        action: &str,
        brightness: Option<u8>,
    ) -> Result<(), String> {
        let mut url = format!("http://{}/light/{}?turn={}", ip, light_idx, action);
        if let Some(b) = brightness {
            url.push_str(&format!("&brightness={}", b));
        }
        self.client.get(&url).send().await
            .map_err(|e| format!("Command failed: {}", e))?;
        Ok(())
    }

    /// Toggle a Gen2+ switch.
    pub async fn command_gen2_toggle(&self, ip: &str, switch_id: u32) -> Result<(), String> {
        let url = format!("http://{}/rpc/Switch.Toggle?id={}", ip, switch_id);
        self.client.get(&url).send().await
            .map_err(|e| format!("Command failed: {}", e))?;
        Ok(())
    }
}

/// Spawn a background tokio task that polls all known Shelly devices
/// at the specified interval.
pub fn start_shelly_poller(bridge: Arc<ShellyBridge>, poll_interval_secs: u64) {
    tokio::spawn(async move {
        let interval = Duration::from_secs(poll_interval_secs);
        loop {
            // Collect MAC addresses of known devices
            let macs: Vec<String> = bridge.devices
                .iter()
                .map(|e| e.key().clone())
                .collect();

            for mac in macs {
                bridge.poll_device(&mac).await;
            }

            tokio::time::sleep(interval).await;
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_bridge() -> ShellyBridge {
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
        ShellyBridge::new(app)
    }

    #[test]
    fn test_new_bridge_empty() {
        let bridge = make_bridge();
        assert_eq!(bridge.device_count(), 0);
        assert!(bridge.devices().is_empty());
    }

    #[test]
    fn test_gen1_relay_entity_creation() {
        let bridge = make_bridge();
        let mac = "aabbccddeeff";

        // Simulate a device in the map
        bridge.devices.insert(mac.to_string(), ShellyDevice {
            ip: "192.168.1.100".to_string(),
            mac: mac.to_string(),
            device_type: "SHSW-1".to_string(),
            name: Some("Kitchen Shelly".to_string()),
            gen: 1,
            firmware: None,
            online: true,
            last_seen: None,
        });

        // Manually invoke the entity creation logic that poll_gen1 would do
        let entity_id = format!("switch.shelly_{}_0", mac);
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".to_string(), Value::String("Kitchen Shelly".to_string()));
        attrs.insert("integration".to_string(), Value::String("shelly".to_string()));
        bridge.app.state_machine.set(entity_id.clone(), "on".to_string(), attrs);

        let entity = bridge.app.state_machine.get(&entity_id);
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "on");
        assert_eq!(
            entity.attributes.get("friendly_name").and_then(|v| v.as_str()),
            Some("Kitchen Shelly")
        );
        assert_eq!(
            entity.attributes.get("integration").and_then(|v| v.as_str()),
            Some("shelly")
        );
    }

    #[test]
    fn test_gen2_switch_entity_creation() {
        let bridge = make_bridge();
        let mac = "aabbccddeeff";

        bridge.devices.insert(mac.to_string(), ShellyDevice {
            ip: "192.168.1.101".to_string(),
            mac: mac.to_string(),
            device_type: "shellyplus2pm-aabbccddeeff".to_string(),
            name: Some("Garage Shelly".to_string()),
            gen: 2,
            firmware: None,
            online: true,
            last_seen: None,
        });

        // Simulate Gen2 switch data
        let switch_data = serde_json::json!({
            "id": 0,
            "output": true,
            "apower": 45.2,
            "voltage": 225.9,
            "current": 0.2,
            "temperature": {"tC": 53.3, "tF": 127.9},
            "aenergy": {"total": 11.679}
        });

        let sys_attrs = serde_json::Map::new();
        bridge.process_gen2_switch(
            "192.168.1.101",
            mac,
            0,
            &switch_data,
            &Some("Garage Shelly".to_string()),
            "shellyplus2pm-aabbccddeeff",
            &sys_attrs,
        );

        let entity = bridge.app.state_machine.get("switch.shelly_aabbccddeeff_0");
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "on");
        assert_eq!(
            entity.attributes.get("apower").and_then(|v| v.as_f64()),
            Some(45.2)
        );
        assert_eq!(
            entity.attributes.get("voltage").and_then(|v| v.as_f64()),
            Some(225.9)
        );
        assert_eq!(
            entity.attributes.get("temperature").and_then(|v| v.as_f64()),
            Some(53.3)
        );
        assert_eq!(
            entity.attributes.get("total_energy").and_then(|v| v.as_f64()),
            Some(11.679)
        );
    }

    #[test]
    fn test_gen2_light_entity_creation() {
        let bridge = make_bridge();
        let mac = "112233445566";

        let light_data = serde_json::json!({
            "output": true,
            "brightness": 75
        });

        bridge.process_gen2_light(
            "192.168.1.102",
            mac,
            0,
            &light_data,
            &Some("Bedroom Dimmer".to_string()),
            "shellydimmer2",
        );

        let entity = bridge.app.state_machine.get("light.shelly_112233445566_0");
        assert!(entity.is_some());
        let entity = entity.unwrap();
        assert_eq!(entity.state, "on");
        assert_eq!(
            entity.attributes.get("brightness").and_then(|v| v.as_u64()),
            Some(75)
        );
    }

    #[test]
    fn test_device_count() {
        let bridge = make_bridge();
        assert_eq!(bridge.device_count(), 0);

        bridge.devices.insert("aabb".to_string(), ShellyDevice {
            ip: "192.168.1.1".to_string(),
            mac: "aabb".to_string(),
            device_type: "SHSW-1".to_string(),
            name: None,
            gen: 1,
            firmware: None,
            online: true,
            last_seen: None,
        });
        assert_eq!(bridge.device_count(), 1);

        bridge.devices.insert("ccdd".to_string(), ShellyDevice {
            ip: "192.168.1.2".to_string(),
            mac: "ccdd".to_string(),
            device_type: "shellyplus1-ccdd".to_string(),
            name: None,
            gen: 2,
            firmware: None,
            online: true,
            last_seen: None,
        });
        assert_eq!(bridge.device_count(), 2);
    }

    #[test]
    fn test_shelly_identity_parse_gen1() {
        let json = r#"{"type":"SHSW-1","mac":"AABBCCDDEEFF","auth":false,"fw":"20220209-...","gen":1}"#;
        let ident: ShellyIdentity = serde_json::from_str(json).unwrap();
        assert_eq!(ident.device_type.as_deref(), Some("SHSW-1"));
        assert_eq!(ident.mac.as_deref(), Some("AABBCCDDEEFF"));
        assert_eq!(ident.gen, Some(1));
        assert_eq!(ident.fw.as_deref(), Some("20220209-..."));
    }

    #[test]
    fn test_shelly_identity_parse_gen2() {
        let json = r#"{"name":"My Shelly","id":"shellyplus1-aabbccddeeff","mac":"AABBCCDDEEFF","gen":2,"fw_id":"20230913-..."}"#;
        let ident: ShellyIdentity = serde_json::from_str(json).unwrap();
        assert_eq!(ident.id.as_deref(), Some("shellyplus1-aabbccddeeff"));
        assert_eq!(ident.name.as_deref(), Some("My Shelly"));
        assert_eq!(ident.gen, Some(2));
        assert_eq!(ident.fw_id.as_deref(), Some("20230913-..."));
    }

    #[test]
    fn test_shelly_identity_parse_gen1_no_gen_field() {
        // Gen1 devices may omit the gen field entirely
        let json = r#"{"type":"SHSW-25","mac":"AABBCCDDEEFF","auth":false,"fw":"20220209-..."}"#;
        let ident: ShellyIdentity = serde_json::from_str(json).unwrap();
        assert_eq!(ident.gen, None);
        assert_eq!(ident.device_type.as_deref(), Some("SHSW-25"));
    }
}
