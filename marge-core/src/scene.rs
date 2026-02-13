use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;

use crate::api::AppState;

#[derive(Debug, Clone, Deserialize)]
pub struct Scene {
    pub id: String,
    pub name: String,
    pub entities: HashMap<String, SceneEntity>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SceneEntity {
    pub state: String,
    #[serde(flatten)]
    pub attributes: HashMap<String, serde_json::Value>,
}

pub fn load_scenes(path: &Path) -> anyhow::Result<Vec<Scene>> {
    let contents = std::fs::read_to_string(path)?;
    let scenes: Vec<Scene> = serde_yaml::from_str(&contents)?;
    Ok(scenes)
}

pub struct SceneEngine {
    scenes: Vec<Scene>,
    app: Arc<AppState>,
}

impl SceneEngine {
    pub fn new(scenes: Vec<Scene>, app: Arc<AppState>) -> Self {
        tracing::info!("Loaded {} scenes", scenes.len());
        for scene in &scenes {
            tracing::info!("  [{}] {}", scene.id, scene.name);
        }
        Self { scenes, app }
    }

    /// Apply a scene by entity_id (e.g., "scene.evening").
    pub fn turn_on(&self, scene_entity_id: &str) -> bool {
        let id = scene_entity_id.strip_prefix("scene.").unwrap_or(scene_entity_id);

        for scene in &self.scenes {
            if scene.id == id {
                tracing::info!("Activating scene [{}]", scene.id);
                for (entity_id, entity) in &scene.entities {
                    let mut attrs = self.app.state_machine.get(entity_id)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    // Merge scene attributes into current attributes
                    for (k, v) in &entity.attributes {
                        attrs.insert(k.clone(), v.clone());
                    }
                    self.app.state_machine.set(
                        entity_id.clone(),
                        entity.state.clone(),
                        attrs,
                    );
                }
                return true;
            }
        }
        tracing::warn!("Scene not found: {}", scene_entity_id);
        false
    }

    /// Get scene IDs and names (for entity registration).
    pub fn scene_ids(&self) -> Vec<(String, String)> {
        self.scenes.iter().map(|s| (s.id.clone(), s.name.clone())).collect()
    }

    /// Get scene info for API responses.
    pub fn get_scenes_info(&self) -> Vec<serde_json::Value> {
        self.scenes.iter().map(|s| {
            let entity_ids: Vec<&str> = s.entities.keys().map(|k| k.as_str()).collect();
            serde_json::json!({
                "id": s.id,
                "name": s.name,
                "entity_count": s.entities.len(),
                "entities": entity_ids,
            })
        }).collect()
    }
}
