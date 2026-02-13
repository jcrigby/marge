use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use rumqttd::{Broker, Config, ConnectionSettings, Notification, RouterConfig, ServerSettings};
use tokio::task::JoinHandle;

use crate::api::AppState;
use crate::discovery::DiscoveryEngine;

/// Start the embedded MQTT broker and an internal subscriber that
/// bridges MQTT messages into the state machine.
///
/// Topic convention (from ha-assumptions-deep-dive.md):
///   home/{domain}/{object_id}/state -> entity_id = {domain}.{object_id}
///
/// Also handles HA MQTT Discovery topics (Phase 2 §1.2):
///   homeassistant/+/+/config and homeassistant/+/+/+/config
///
/// Returns handles for the broker and subscriber tasks.
pub fn start_mqtt(
    app: Arc<AppState>,
    port: u16,
    discovery: Arc<DiscoveryEngine>,
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
            // Subscribe to original home/# topic and discovery topics
            if let Err(e) = link_tx.subscribe("home/#") {
                tracing::error!("MQTT subscribe home/# failed: {}", e);
                return;
            }
            if let Err(e) = link_tx.subscribe("homeassistant/#") {
                tracing::error!("MQTT subscribe homeassistant/# failed: {}", e);
                return;
            }
            tracing::info!("MQTT subscriber listening on home/# and homeassistant/#");

            loop {
                match link_rx.recv() {
                    Ok(Some(notification)) => {
                        if let Some((topic, payload)) = extract_publish(&notification) {
                            // Check if this is a discovery topic
                            if DiscoveryEngine::is_discovery_topic(&topic) {
                                if let Some(new_topics) = discovery.process_discovery(&topic, &payload) {
                                    // Subscribe to newly discovered state topics
                                    for t in new_topics {
                                        if let Err(e) = link_tx.subscribe(&t) {
                                            tracing::warn!("Failed to subscribe to {}: {}", t, e);
                                        }
                                    }
                                }
                                continue;
                            }

                            // Check if this is a state update for a discovered entity
                            if discovery.is_subscribed_topic(&topic) {
                                discovery.process_state_update(&topic, &payload);
                                continue;
                            }

                            // Original home/{domain}/{object_id}/state handling
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
