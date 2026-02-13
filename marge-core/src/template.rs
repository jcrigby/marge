//! Template engine powered by minijinja (Phase 2 §1.3)
//!
//! Provides Jinja2-compatible template rendering for:
//! - MQTT Discovery value_templates
//! - Automation template conditions and actions (Phase 3)
//!
//! Context variables:
//!   value      — raw MQTT payload string
//!   value_json — parsed JSON from the payload
//!
//! Custom filters: round, int, float, default, iif, is_defined

use minijinja::{Environment, Value};
use std::sync::OnceLock;

/// Shared template environment (filters registered once).
static ENV: OnceLock<Environment<'static>> = OnceLock::new();

fn env() -> &'static Environment<'static> {
    ENV.get_or_init(|| {
        let mut env = Environment::new();

        // Custom filters matching HA's Jinja2 builtins
        env.add_filter("int", filter_int);
        env.add_filter("float", filter_float);
        env.add_filter("round", filter_round);
        env.add_filter("default", filter_default);
        env.add_filter("iif", filter_iif);
        env.add_filter("is_defined", filter_is_defined);
        env.add_filter("lower", filter_lower);
        env.add_filter("upper", filter_upper);
        env.add_filter("trim", filter_trim);
        env.add_filter("replace", filter_replace);
        env.add_filter("regex_match", filter_regex_match);
        env.add_filter("from_json", filter_from_json);
        env.add_filter("to_json", filter_to_json);
        env.add_filter("log", filter_log);
        env.add_filter("abs", filter_abs);
        env.add_filter("max", filter_max);
        env.add_filter("min", filter_min);

        // Global functions matching HA templates
        env.add_function("float", fn_float);
        env.add_function("int", fn_int);
        env.add_function("bool", fn_bool);

        env
    })
}

/// Render a template string with the given context variables.
pub fn render(template: &str, ctx: &TemplateContext) -> Result<String, String> {
    let env = env();
    let tmpl = env
        .template_from_str(template)
        .map_err(|e| format!("template parse error: {}", e))?;

    // Build context with value and value_json
    let context = match (&ctx.value, &ctx.value_json) {
        (Some(v), Some(vj)) => minijinja::context! { value => v, value_json => vj },
        (Some(v), None) => minijinja::context! { value => v },
        (None, Some(vj)) => minijinja::context! { value_json => vj },
        (None, None) => minijinja::context! {},
    };

    tmpl.render(context)
        .map_err(|e| format!("template render error: {}", e))
}

/// Render a template with a full state context (for automation templates).
pub fn render_with_states<F>(template: &str, _state_getter: F) -> Result<String, String>
where
    F: Fn(&str) -> Option<String>,
{
    let env = env();
    let tmpl = env
        .template_from_str(template)
        .map_err(|e| format!("template parse error: {}", e))?;

    // For now, provide an empty context. Full state access comes in Phase 3
    // when we add `states('entity_id')` as a global function.
    let context = minijinja::context! {};
    tmpl.render(context)
        .map_err(|e| format!("template render error: {}", e))
}

/// Context variables for template rendering.
#[derive(Default)]
pub struct TemplateContext {
    /// Raw MQTT payload string
    pub value: Option<String>,
    /// Parsed JSON from MQTT payload
    pub value_json: Option<Value>,
}

impl TemplateContext {
    /// Build context from an MQTT payload.
    pub fn from_payload(payload: &str) -> Self {
        let value_json = serde_json::from_str::<serde_json::Value>(payload)
            .ok()
            .map(|v| serde_json_to_minijinja(&v));

        Self {
            value: Some(payload.to_string()),
            value_json,
        }
    }
}

/// Convert serde_json::Value to minijinja::Value
fn serde_json_to_minijinja(v: &serde_json::Value) -> Value {
    match v {
        serde_json::Value::Null => Value::from(()),
        serde_json::Value::Bool(b) => Value::from(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Value::from(i)
            } else if let Some(f) = n.as_f64() {
                Value::from(f)
            } else {
                Value::from(n.to_string())
            }
        }
        serde_json::Value::String(s) => Value::from(s.as_str()),
        serde_json::Value::Array(arr) => {
            Value::from(arr.iter().map(serde_json_to_minijinja).collect::<Vec<_>>())
        }
        serde_json::Value::Object(map) => {
            Value::from(
                map.iter()
                    .map(|(k, v)| (k.as_str(), serde_json_to_minijinja(v)))
                    .collect::<std::collections::BTreeMap<&str, Value>>(),
            )
        }
    }
}

// ── Custom Filters ──────────────────────────────────────

fn filter_int(value: Value) -> Value {
    if let Some(s) = value.as_str() {
        Value::from(s.parse::<i64>().unwrap_or(0))
    } else if let Some(f) = as_f64(&value) {
        Value::from(f as i64)
    } else {
        Value::from(0i64)
    }
}

fn filter_float(value: Value) -> Value {
    if let Some(s) = value.as_str() {
        Value::from(s.parse::<f64>().unwrap_or(0.0))
    } else if let Some(f) = as_f64(&value) {
        Value::from(f)
    } else {
        Value::from(0.0f64)
    }
}

fn filter_round(value: Value, precision: Option<Value>) -> Value {
    let p = precision
        .and_then(|v| as_f64(&v))
        .unwrap_or(0.0) as i32;
    if let Some(f) = as_f64(&value) {
        let factor = 10f64.powi(p);
        Value::from((f * factor).round() / factor)
    } else {
        value
    }
}

fn filter_default(value: Value, default: Option<Value>) -> Value {
    if value.is_undefined() || value.is_none() {
        default.unwrap_or_else(|| Value::from(""))
    } else {
        value
    }
}

fn filter_iif(value: Value, if_true: Value, if_false: Option<Value>) -> Value {
    let falsy = value.is_undefined()
        || value.is_none()
        || value == Value::from(false)
        || value == Value::from(0i64)
        || (value.as_str() == Some(""));
    if !falsy {
        if_true
    } else {
        if_false.unwrap_or_else(|| Value::from(""))
    }
}

fn filter_is_defined(value: Value) -> Value {
    Value::from(!value.is_undefined())
}

fn filter_lower(value: Value) -> Value {
    Value::from(value.to_string().to_lowercase())
}

fn filter_upper(value: Value) -> Value {
    Value::from(value.to_string().to_uppercase())
}

fn filter_trim(value: Value) -> Value {
    Value::from(value.to_string().trim().to_string())
}

fn filter_replace(value: Value, old: Value, new: Value) -> Value {
    let s = value.to_string();
    let old_s = old.to_string();
    let new_s = new.to_string();
    Value::from(s.replace(&old_s, &new_s))
}

fn filter_regex_match(value: Value, _pattern: Value) -> Value {
    // Minimal stub — full regex support can be added later
    Value::from(!value.to_string().is_empty())
}

fn filter_from_json(value: Value) -> Value {
    if let Some(s) = value.as_str() {
        match serde_json::from_str::<serde_json::Value>(s) {
            Ok(v) => serde_json_to_minijinja(&v),
            Err(_) => value,
        }
    } else {
        value
    }
}

fn filter_to_json(value: Value) -> Value {
    Value::from(value.to_string())
}

fn filter_log(value: Value, base: Option<Value>) -> Value {
    if let Some(f) = as_f64(&value) {
        let result = match base.and_then(|b| as_f64(&b)) {
            Some(b) => f.log(b),
            None => f.ln(),
        };
        Value::from(result)
    } else {
        value
    }
}

fn filter_abs(value: Value) -> Value {
    if let Some(f) = as_f64(&value) {
        Value::from(f.abs())
    } else {
        value
    }
}

fn filter_max(value: Value, other: Value) -> Value {
    match (as_f64(&value), as_f64(&other)) {
        (Some(a), Some(b)) => Value::from(a.max(b)),
        _ => value,
    }
}

fn filter_min(value: Value, other: Value) -> Value {
    match (as_f64(&value), as_f64(&other)) {
        (Some(a), Some(b)) => Value::from(a.min(b)),
        _ => value,
    }
}

// ── Global Functions ────────────────────────────────────

fn fn_float(value: Value, default: Option<Value>) -> Value {
    if let Some(s) = value.as_str() {
        match s.parse::<f64>() {
            Ok(f) => Value::from(f),
            Err(_) => default.unwrap_or(Value::from(0.0f64)),
        }
    } else if let Some(f) = as_f64(&value) {
        Value::from(f)
    } else {
        default.unwrap_or(Value::from(0.0f64))
    }
}

fn fn_int(value: Value, default: Option<Value>) -> Value {
    if let Some(s) = value.as_str() {
        match s.parse::<i64>() {
            Ok(i) => Value::from(i),
            Err(_) => {
                // Try parsing as float then truncating
                match s.parse::<f64>() {
                    Ok(f) => Value::from(f as i64),
                    Err(_) => default.unwrap_or(Value::from(0i64)),
                }
            }
        }
    } else if let Some(f) = as_f64(&value) {
        Value::from(f as i64)
    } else {
        default.unwrap_or(Value::from(0i64))
    }
}

fn fn_bool(value: Value) -> Value {
    let truthy = if let Some(s) = value.as_str() {
        matches!(s.to_lowercase().as_str(), "true" | "yes" | "on" | "enable" | "1")
    } else if let Some(f) = as_f64(&value) {
        f != 0.0
    } else {
        !value.is_undefined() && !value.is_none()
    };
    Value::from(truthy)
}

/// Helper: extract f64 from a minijinja Value
fn as_f64(v: &Value) -> Option<f64> {
    // Try i64 first, then f64 directly
    if let Ok(i) = i64::try_from(v.clone()) {
        Some(i as f64)
    } else if let Ok(f) = f64::try_from(v.clone()) {
        Some(f)
    } else if let Some(s) = v.as_str() {
        s.parse::<f64>().ok()
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_template() {
        let ctx = TemplateContext::from_payload("42.5");
        let result = render("{{ value }}", &ctx).unwrap();
        assert_eq!(result, "42.5");
    }

    #[test]
    fn test_value_json() {
        let ctx = TemplateContext::from_payload(r#"{"temperature": 72.3}"#);
        let result = render("{{ value_json.temperature }}", &ctx).unwrap();
        assert_eq!(result, "72.3");
    }

    #[test]
    fn test_float_filter() {
        let ctx = TemplateContext::from_payload(r#"{"temp": "72.3"}"#);
        let result = render("{{ value_json.temp | float }}", &ctx).unwrap();
        assert_eq!(result, "72.3");
    }

    #[test]
    fn test_round_filter() {
        let ctx = TemplateContext::from_payload(r#"{"temp": 72.345}"#);
        let result = render("{{ value_json.temp | round(1) }}", &ctx).unwrap();
        assert_eq!(result, "72.3");
    }

    #[test]
    fn test_int_filter() {
        let ctx = TemplateContext::from_payload(r#"{"count": "42"}"#);
        let result = render("{{ value_json.count | int }}", &ctx).unwrap();
        assert_eq!(result, "42");
    }

    #[test]
    fn test_default_filter() {
        let ctx = TemplateContext { value: None, value_json: None };
        let result = render("{{ missing | default('N/A') }}", &ctx).unwrap();
        assert_eq!(result, "N/A");
    }

    #[test]
    fn test_nested_json() {
        let ctx = TemplateContext::from_payload(
            r#"{"sensor": {"temperature": 25, "humidity": 60}}"#,
        );
        let result = render("{{ value_json.sensor.temperature }}", &ctx).unwrap();
        assert_eq!(result, "25");
    }
}
