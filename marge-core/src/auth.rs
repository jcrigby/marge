//! Authentication (Phase 4 §4.3)
//!
//! Supports two modes:
//! - Static token: Set `MARGE_AUTH_TOKEN` env var for a single long-lived token
//! - Open: When no token is configured, all endpoints are accessible (development mode)
//!
//! The auth module validates tokens for both REST API (Bearer header)
//! and WebSocket (auth message). Health endpoint is always open.

/// Auth configuration, initialized once at startup.
pub struct AuthConfig {
    /// Static token from MARGE_AUTH_TOKEN. If None, auth is disabled.
    token: Option<String>,
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
        Self { token }
    }

    /// Whether authentication is required.
    pub fn is_enabled(&self) -> bool {
        self.token.is_some()
    }

    /// Validate a token. Returns true if valid or if auth is disabled.
    pub fn validate(&self, token: &str) -> bool {
        match &self.token {
            Some(expected) => {
                // Constant-time comparison to prevent timing attacks
                if expected.len() != token.len() {
                    return false;
                }
                expected
                    .bytes()
                    .zip(token.bytes())
                    .fold(0u8, |acc, (a, b)| acc | (a ^ b))
                    == 0
            }
            None => true,
        }
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
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_disabled_auth_accepts_everything() {
        let auth = AuthConfig { token: None };
        assert!(!auth.is_enabled());
        assert!(auth.validate("anything"));
        assert!(auth.validate_header(None));
        assert!(auth.validate_header(Some("Bearer whatever")));
    }

    #[test]
    fn test_enabled_auth_validates_token() {
        let auth = AuthConfig {
            token: Some("secret123".to_string()),
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
        };
        assert!(auth.validate_header(Some("Bearer mytoken")));
        assert!(!auth.validate_header(Some("Bearer wrong")));
        assert!(!auth.validate_header(None));
        // Also accept raw token (without Bearer prefix)
        assert!(auth.validate_header(Some("mytoken")));
    }
}
