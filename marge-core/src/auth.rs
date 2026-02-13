//! Authentication (Phase 4 §4.3)
//!
//! Supports three auth modes:
//! - Static token: Set `MARGE_AUTH_TOKEN` env var for a single admin token
//! - Long-lived tokens: Managed via API, persisted in SQLite
//! - Open: When no token is configured, all endpoints are accessible (development mode)
//!
//! The auth module validates tokens for both REST API (Bearer header)
//! and WebSocket (auth message). Health endpoint is always open.

use dashmap::DashMap;

/// Info about a long-lived access token.
#[derive(Debug, Clone, serde::Serialize)]
pub struct TokenInfo {
    pub id: String,
    pub name: String,
    pub created_at: String,
    /// Only included when the token is first created
    #[serde(skip_serializing_if = "Option::is_none")]
    pub token: Option<String>,
}

/// Auth configuration, initialized once at startup.
pub struct AuthConfig {
    /// Static token from MARGE_AUTH_TOKEN. If None, auth is disabled.
    token: Option<String>,
    /// Long-lived access tokens: token_value -> TokenInfo
    long_lived: DashMap<String, TokenInfo>,
}

impl AuthConfig {
    /// Load auth configuration from environment.
    /// Returns an AuthConfig. If MARGE_AUTH_TOKEN is not set, auth is disabled.
    pub fn from_env() -> Self {
        let token = std::env::var("MARGE_AUTH_TOKEN").ok();
        if token.is_some() {
            tracing::info!("Auth enabled (static token)");
        } else {
            tracing::info!("Auth disabled (no MARGE_AUTH_TOKEN set)");
        }
        Self {
            token,
            long_lived: DashMap::new(),
        }
    }

    /// Whether authentication is required (based on static token only).
    /// Long-lived tokens are accepted as valid credentials but don't
    /// force auth on by themselves — that's controlled by MARGE_AUTH_TOKEN.
    pub fn is_enabled(&self) -> bool {
        self.token.is_some()
    }

    /// Validate a token. Returns true if valid or if auth is disabled.
    pub fn validate(&self, token: &str) -> bool {
        // Check static token first
        if let Some(expected) = &self.token {
            if constant_time_eq(expected, token) {
                return true;
            }
        }

        // Check long-lived tokens
        if self.long_lived.contains_key(token) {
            return true;
        }

        // If no static token configured, allow everything
        self.token.is_none()
    }

    /// Extract and validate a Bearer token from an Authorization header value.
    pub fn validate_header(&self, auth_header: Option<&str>) -> bool {
        if !self.is_enabled() {
            return true;
        }
        match auth_header {
            Some(header) => {
                let token = header.strip_prefix("Bearer ").unwrap_or(header);
                self.validate(token)
            }
            None => false,
        }
    }

    /// Add a long-lived token (loaded from DB or newly created).
    pub fn add_token(&self, token_value: String, info: TokenInfo) {
        self.long_lived.insert(token_value, info);
    }

    /// Remove a long-lived token by its ID (not the token value).
    /// Returns true if found and removed.
    pub fn remove_token_by_id(&self, id: &str) -> bool {
        let key = self.long_lived.iter()
            .find(|entry| entry.value().id == id)
            .map(|entry| entry.key().clone());
        if let Some(key) = key {
            self.long_lived.remove(&key);
            true
        } else {
            false
        }
    }

    /// List all long-lived tokens (without the actual token values).
    pub fn list_tokens(&self) -> Vec<TokenInfo> {
        self.long_lived.iter().map(|entry| {
            let mut info = entry.value().clone();
            info.token = None; // Never expose the token value in listings
            info
        }).collect()
    }

    /// Number of long-lived tokens.
    pub fn token_count(&self) -> usize {
        self.long_lived.len()
    }
}

/// Constant-time string comparison to prevent timing attacks.
fn constant_time_eq(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    a.bytes()
        .zip(b.bytes())
        .fold(0u8, |acc, (x, y)| acc | (x ^ y))
        == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_disabled_auth_accepts_everything() {
        let auth = AuthConfig { token: None, long_lived: DashMap::new() };
        assert!(!auth.is_enabled());
        assert!(auth.validate("anything"));
        assert!(auth.validate_header(None));
        assert!(auth.validate_header(Some("Bearer whatever")));
    }

    #[test]
    fn test_enabled_auth_validates_token() {
        let auth = AuthConfig {
            token: Some("secret123".to_string()),
            long_lived: DashMap::new(),
        };
        assert!(auth.is_enabled());
        assert!(auth.validate("secret123"));
        assert!(!auth.validate("wrong"));
        assert!(!auth.validate("secret12")); // different length
    }

    #[test]
    fn test_bearer_header_parsing() {
        let auth = AuthConfig {
            token: Some("mytoken".to_string()),
            long_lived: DashMap::new(),
        };
        assert!(auth.validate_header(Some("Bearer mytoken")));
        assert!(!auth.validate_header(Some("Bearer wrong")));
        assert!(!auth.validate_header(None));
        // Also accept raw token (without Bearer prefix)
        assert!(auth.validate_header(Some("mytoken")));
    }

    #[test]
    fn test_long_lived_tokens() {
        let auth = AuthConfig { token: None, long_lived: DashMap::new() };
        assert!(!auth.is_enabled());

        // Add a long-lived token — doesn't enable auth globally
        auth.add_token("llat_abc123".to_string(), TokenInfo {
            id: "tok1".to_string(),
            name: "Test Token".to_string(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            token: None,
        });
        assert!(!auth.is_enabled()); // no static token, so auth stays off
        assert!(auth.validate("llat_abc123")); // but token is still valid
        assert!(auth.validate("anything")); // auth off = everything valid

        // With static token set, long-lived tokens work as credentials
        let auth2 = AuthConfig {
            token: Some("admin".to_string()),
            long_lived: DashMap::new(),
        };
        auth2.add_token("llat_xyz".to_string(), TokenInfo {
            id: "tok2".to_string(),
            name: "API Token".to_string(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            token: None,
        });
        assert!(auth2.is_enabled());
        assert!(auth2.validate("admin")); // static token works
        assert!(auth2.validate("llat_xyz")); // long-lived token works
        assert!(!auth2.validate("wrong")); // invalid token rejected

        // List tokens
        let tokens = auth.list_tokens();
        assert_eq!(tokens.len(), 1);
        assert_eq!(tokens[0].name, "Test Token");
        assert!(tokens[0].token.is_none()); // token value not exposed

        // Remove by ID
        assert!(auth.remove_token_by_id("tok1"));
        assert!(!auth.remove_token_by_id("tok1")); // already removed
    }
}
