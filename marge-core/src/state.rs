use chrono::{DateTime, Utc};
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::broadcast;

/// HA-compatible state object (SSS §4.1.2)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntityState {
    pub entity_id: String,
    pub state: String,
    #[serde(default)]
    pub attributes: serde_json::Map<String, serde_json::Value>,
    pub last_changed: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
    pub last_reported: DateTime<Utc>,
    pub context: Context,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Context {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_id: Option<String>,
}

impl Context {
    pub fn new() -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            parent_id: None,
            user_id: None,
        }
    }
}

/// Event fired when state changes (SSS §4.1.1 state_changed)
#[derive(Debug, Clone, Serialize)]
pub struct StateChangedEvent {
    pub entity_id: String,
    pub old_state: Option<EntityState>,
    pub new_state: EntityState,
}

/// The core state machine (SSS STATE-001 through STATE-008)
pub struct StateMachine {
    states: Arc<DashMap<String, EntityState>>,
    event_tx: broadcast::Sender<StateChangedEvent>,
}

impl StateMachine {
    pub fn new(channel_capacity: usize) -> Self {
        let (event_tx, _) = broadcast::channel(channel_capacity);
        Self {
            states: Arc::new(DashMap::new()),
            event_tx,
        }
    }

    /// Get all entity states
    pub fn get_all(&self) -> Vec<EntityState> {
        self.states
            .iter()
            .map(|entry| entry.value().clone())
            .collect()
    }

    /// Get a single entity state
    pub fn get(&self, entity_id: &str) -> Option<EntityState> {
        self.states.get(entity_id).map(|entry| entry.value().clone())
    }

    /// Set entity state. Returns the old state if it existed.
    /// Fires state_changed event on the event bus (STATE-003).
    pub fn set(&self, entity_id: String, state: String, attributes: serde_json::Map<String, serde_json::Value>) -> EntityState {
        let now = Utc::now();
        let context = Context::new();

        let old_state = self.states.get(&entity_id).map(|e| e.value().clone());

        // STATE-006: Distinguish last_changed vs last_updated vs last_reported
        let (last_changed, last_updated) = match &old_state {
            Some(prev) => {
                let changed = if prev.state != state {
                    now
                } else {
                    prev.last_changed
                };
                let updated = if prev.state != state || prev.attributes != attributes {
                    now
                } else {
                    prev.last_updated
                };
                (changed, updated)
            }
            None => (now, now),
        };

        let new_state = EntityState {
            entity_id: entity_id.clone(),
            state,
            attributes,
            last_changed,
            last_updated,
            last_reported: now,
            context,
        };

        self.states.insert(entity_id.clone(), new_state.clone());

        // Fire state_changed event (ignore error if no subscribers)
        let _ = self.event_tx.send(StateChangedEvent {
            entity_id,
            old_state,
            new_state: new_state.clone(),
        });

        new_state
    }

    /// Subscribe to state change events
    pub fn subscribe(&self) -> broadcast::Receiver<StateChangedEvent> {
        self.event_tx.subscribe()
    }

    /// Number of entities currently tracked
    pub fn len(&self) -> usize {
        self.states.len()
    }
}
