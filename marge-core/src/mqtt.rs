use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use rumqttd::{Broker, Config, ConnectionSettings, Notification, RouterConfig, ServerSettings};
use tokio::task::JoinHandle;

use crate::api::AppState;
use crate::discovery::DiscoveryEngine;
use crate::integrations::{zigbee2mqtt, zwave, tasmota, esphome};

/// Device bridge managers passed to the MQTT subscriber.
pub struct DeviceBridges {
    pub z2m: Arc<zigbee2mqtt::Zigbee2MqttBridge>,
    pub zwave: Arc<zwave::ZwaveBridge>,
    pub tasmota: Arc<tasmota::TasmotaBridge>,
    pub esphome: Arc<esphome::ESPHomeBridge>,
}

/// Start the embedded MQTT broker and an internal subscriber that
/// bridges MQTT messages into the state machine.
///
/// Topic convention (from ha-assumptions-deep-dive.md):
///   home/{domain}/{object_id}/state -> entity_id = {domain}.{object_id}
///
/// Also handles HA MQTT Discovery topics (Phase 2 §1.2):
///   homeassistant/+/+/config and homeassistant/+/+/+/config
///
/// Device bridge topics (Phase 2 §2.1-2.3):
///   zigbee2mqtt/#, zwave/#, stat/#, tele/#
///
/// Returns handles for the broker and subscriber tasks.
pub fn start_mqtt(
    app: Arc<AppState>,
    port: u16,
    discovery: Arc<DiscoveryEngine>,
    bridges: DeviceBridges,
) -> anyhow::Result<(JoinHandle<()>, JoinHandle<()>)> {
    let addr: SocketAddr = format!("0.0.0.0:{}", port).parse()?;

    let server_settings = ServerSettings {
        name: "v4-marge".to_string(),
        listen: addr,
        tls: None,
        next_connection_delay_ms: 0,
        connections: ConnectionSettings {
            connection_timeout_ms: 5000,
            max_payload_size: 65536,
            max_inflight_count: 100,
            auth: None,
            external_auth: None,
            dynamic_filters: true,
        },
    };

    let mut v4 = HashMap::new();
    v4.insert("v4-1".to_string(), server_settings);

    let config = Config {
        id: 0,
        router: RouterConfig {
            max_connections: 1000,
            max_outgoing_packet_count: 200,
            max_segment_size: 104857600,
            max_segment_count: 10,
            custom_segment: None,
            initialized_filters: None,
            shared_subscriptions_strategy: Default::default(),
        },
        v4: Some(v4),
        v5: None,
        ws: None,
        cluster: None,
        console: None,
        bridge: None,
        prometheus: None,
        metrics: None,
    };

    let mut broker = Broker::new(config);

    // Create an internal link for subscribing (must happen before start)
    let (mut link_tx, mut link_rx) = broker.link("marge-internal")?;

    // broker.start() is blocking — run it in a dedicated thread
    let broker_handle = tokio::spawn(async move {
        tokio::task::spawn_blocking(move || {
            if let Err(e) = broker.start() {
                tracing::error!("MQTT broker error: {}", e);
            }
        })
        .await
        .ok();
    });

    // Spawn the subscriber bridge in a blocking thread
    // (link_rx.recv() is blocking and would starve the tokio runtime)
    let subscriber_handle = tokio::spawn(async move {
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;

        tokio::task::spawn_blocking(move || {
            // Subscribe to all topic namespaces
            for pattern in &[
                "home/#",
                "homeassistant/#",
                "zigbee2mqtt/#",
                "zwave/#",
                "stat/#",
                "tele/#",
                "cmnd/#",
            ] {
                if let Err(e) = link_tx.subscribe(*pattern) {
                    tracing::error!("MQTT subscribe {} failed: {}", pattern, e);
                    return;
                }
            }
            tracing::info!("MQTT subscriber listening on home/#, homeassistant/#, zigbee2mqtt/#, zwave/#, stat/#, tele/#");

            loop {
                match link_rx.recv() {
                    Ok(Some(notification)) => {
                        if let Some((topic, payload)) = extract_publish(&notification) {
                            // ── HA MQTT Discovery ────────────────
                            if DiscoveryEngine::is_discovery_topic(&topic) {
                                if let Some(new_topics) = discovery.process_discovery(&topic, &payload) {
                                    for t in new_topics {
                                        if let Err(e) = link_tx.subscribe(&t) {
                                            tracing::warn!("Failed to subscribe to {}: {}", t, e);
                                        }
                                    }
                                }
                                continue;
                            }

                            // ── Discovered entity state updates ──
                            if discovery.is_subscribed_topic(&topic) {
                                discovery.process_state_update(&topic, &payload);
                                continue;
                            }

                            // ── zigbee2mqtt bridge ───────────────
                            if zigbee2mqtt::Zigbee2MqttBridge::is_z2m_topic(&topic) {
                                bridges.z2m.process_message(&topic, &payload);
                                continue;
                            }

                            // ── Z-Wave bridge ────────────────────
                            if zwave::ZwaveBridge::is_zwave_topic(&topic) {
                                bridges.zwave.process_message(&topic, &payload);
                                continue;
                            }

                            // ── Tasmota bridge ───────────────────
                            if tasmota::TasmotaBridge::is_tasmota_topic(&topic) {
                                bridges.tasmota.process_message(&topic, &payload);
                                continue;
                            }

                            // ── Original home/# bridge ───────────
                            if let Some(entity_id) = topic_to_entity_id(&topic) {
                                let state = String::from_utf8_lossy(&payload).to_string();
                                tracing::debug!("MQTT -> {} = {}", entity_id, state);

                                let attrs = app.state_machine.get(&entity_id)
                                    .map(|s| s.attributes.clone())
                                    .unwrap_or_default();

                                app.state_machine.set(entity_id, state, attrs);
                            }
                        }
                    }
                    Ok(None) => continue,
                    Err(e) => {
                        tracing::error!("MQTT link_rx error: {:?}", e);
                        break;
                    }
                }
            }
        }).await.ok();
    });

    Ok((broker_handle, subscriber_handle))
}

/// Extract topic and payload from a rumqttd notification.
fn extract_publish(notification: &Notification) -> Option<(String, Vec<u8>)> {
    match notification {
        Notification::Forward(forward) => {
            let topic = std::str::from_utf8(&forward.publish.topic)
                .ok()?
                .to_string();
            let payload = forward.publish.payload.to_vec();
            Some((topic, payload))
        }
        _ => None,
    }
}

/// Convert MQTT topic to entity_id.
/// `home/sensor/bedroom_temperature/state` -> `sensor.bedroom_temperature`
fn topic_to_entity_id(topic: &str) -> Option<String> {
    let parts: Vec<&str> = topic.split('/').collect();
    // Expected: home/{domain}/{object_id}/state
    if parts.len() == 4 && parts[0] == "home" && parts[3] == "state" {
        Some(format!("{}.{}", parts[1], parts[2]))
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_topic_to_entity_id() {
        assert_eq!(
            topic_to_entity_id("home/sensor/bedroom_temperature/state"),
            Some("sensor.bedroom_temperature".to_string())
        );
        assert_eq!(
            topic_to_entity_id("home/binary_sensor/smoke_detector/state"),
            Some("binary_sensor.smoke_detector".to_string())
        );
        assert_eq!(topic_to_entity_id("other/topic"), None);
        assert_eq!(topic_to_entity_id("home/sensor/temp/command"), None);
    }
}
