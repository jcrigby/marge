//! Built-in weather integration using Met.no Locationforecast API
//!
//! No API key required. Rate-limited to 1 request per 30 minutes.
//! Met.no Terms of Service: https://api.met.no/doc/TermsOfService
//! Requires a User-Agent header identifying the application.

use std::sync::Arc;

use serde::Deserialize;

use crate::api::AppState;

/// Configuration for the weather integration.
pub struct WeatherConfig {
    /// Latitude of the location to fetch weather for.
    pub lat: f64,
    /// Longitude of the location to fetch weather for.
    pub lon: f64,
    /// Polling interval in seconds (default: 1800 = 30 minutes).
    pub poll_interval_secs: u64,
}

impl Default for WeatherConfig {
    fn default() -> Self {
        Self {
            lat: 30.2672,   // Austin, TX
            lon: -97.7431,
            poll_interval_secs: 1800,
        }
    }
}

// ── Met.no JSON response structures ────────────────────────────

#[derive(Debug, Deserialize)]
struct MetNoResponse {
    properties: MetNoProperties,
}

#[derive(Debug, Deserialize)]
struct MetNoProperties {
    timeseries: Vec<MetNoTimeseries>,
}

#[derive(Debug, Deserialize)]
struct MetNoTimeseries {
    data: MetNoData,
}

#[derive(Debug, Deserialize)]
struct MetNoData {
    instant: MetNoInstant,
    next_1_hours: Option<MetNoNextHours>,
    next_6_hours: Option<MetNoNextHours>,
}

#[derive(Debug, Deserialize)]
struct MetNoInstant {
    details: MetNoDetails,
}

#[derive(Debug, Deserialize)]
struct MetNoDetails {
    air_temperature: f64,
    relative_humidity: f64,
    wind_speed: f64,
    wind_from_direction: f64,
    air_pressure_at_sea_level: f64,
}

#[derive(Debug, Deserialize)]
struct MetNoNextHours {
    summary: MetNoSummary,
}

#[derive(Debug, Deserialize)]
struct MetNoSummary {
    symbol_code: String,
}

// ── Poller ──────────────────────────────────────────────────────

/// Spawn a background task that periodically fetches weather data from Met.no
/// and updates weather entities in the state machine.
pub fn start_weather_poller(app_state: Arc<AppState>, config: WeatherConfig) {
    tokio::spawn(async move {
        let client = reqwest::Client::builder()
            .user_agent("Marge/0.1 github.com/sangerburgwich/marge")
            .build()
            .expect("failed to build reqwest client");

        let url = format!(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={}&lon={}",
            config.lat, config.lon
        );

        let mut first_fetch = true;

        loop {
            match fetch_weather(&client, &url).await {
                Ok(resp) => {
                    if first_fetch {
                        tracing::info!(
                            "Weather integration active for ({}, {})",
                            config.lat,
                            config.lon
                        );
                        first_fetch = false;
                    }
                    update_entities(&app_state, &resp);
                }
                Err(e) => {
                    tracing::warn!("Weather fetch failed: {} — will retry in {}s", e, config.poll_interval_secs);
                }
            }

            tokio::time::sleep(std::time::Duration::from_secs(config.poll_interval_secs)).await;
        }
    });
}

async fn fetch_weather(client: &reqwest::Client, url: &str) -> anyhow::Result<MetNoResponse> {
    let resp = client.get(url).send().await?;
    let status = resp.status();
    if !status.is_success() {
        anyhow::bail!("Met.no returned HTTP {}", status);
    }
    let body = resp.json::<MetNoResponse>().await?;
    Ok(body)
}

fn update_entities(app_state: &AppState, resp: &MetNoResponse) {
    let Some(first) = resp.properties.timeseries.first() else {
        tracing::warn!("Weather response contained no timeseries data");
        return;
    };

    let details = &first.data.instant.details;

    // Determine condition from next_1_hours, falling back to next_6_hours
    let condition = first
        .data
        .next_1_hours
        .as_ref()
        .or(first.data.next_6_hours.as_ref())
        .map(|h| h.summary.symbol_code.clone())
        .unwrap_or_else(|| "unknown".to_string());

    // weather.home — primary weather entity
    {
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".into(), serde_json::json!("Home"));
        attrs.insert("temperature".into(), serde_json::json!(details.air_temperature));
        attrs.insert("humidity".into(), serde_json::json!(details.relative_humidity));
        attrs.insert("wind_speed".into(), serde_json::json!(details.wind_speed));
        attrs.insert("wind_bearing".into(), serde_json::json!(details.wind_from_direction));
        attrs.insert("pressure".into(), serde_json::json!(details.air_pressure_at_sea_level));
        app_state.state_machine.set(
            "weather.home".to_string(),
            condition,
            attrs,
        );
    }

    // sensor.weather_temperature
    {
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".into(), serde_json::json!("Weather Temperature"));
        attrs.insert("unit_of_measurement".into(), serde_json::json!("\u{00b0}C"));
        app_state.state_machine.set(
            "sensor.weather_temperature".to_string(),
            format!("{}", details.air_temperature),
            attrs,
        );
    }

    // sensor.weather_humidity
    {
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".into(), serde_json::json!("Weather Humidity"));
        attrs.insert("unit_of_measurement".into(), serde_json::json!("%"));
        app_state.state_machine.set(
            "sensor.weather_humidity".to_string(),
            format!("{}", details.relative_humidity),
            attrs,
        );
    }

    // sensor.weather_wind_speed
    {
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".into(), serde_json::json!("Weather Wind Speed"));
        attrs.insert("unit_of_measurement".into(), serde_json::json!("m/s"));
        app_state.state_machine.set(
            "sensor.weather_wind_speed".to_string(),
            format!("{}", details.wind_speed),
            attrs,
        );
    }

    // sensor.weather_pressure
    {
        let mut attrs = serde_json::Map::new();
        attrs.insert("friendly_name".into(), serde_json::json!("Weather Pressure"));
        attrs.insert("unit_of_measurement".into(), serde_json::json!("hPa"));
        app_state.state_machine.set(
            "sensor.weather_pressure".to_string(),
            format!("{}", details.air_pressure_at_sea_level),
            attrs,
        );
    }
}
