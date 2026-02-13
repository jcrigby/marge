## ── Stage 1: Build dashboard ────────────────────
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY marge-ui/package.json marge-ui/package-lock.json* ./
RUN npm ci --no-audit
COPY marge-ui/ ./
RUN npm run build

## ── Stage 2: Build Rust binary ──────────────────
FROM rust:1.93-slim-bookworm AS builder
WORKDIR /build

# Copy manifest first for layer caching
COPY marge-core/Cargo.toml marge-core/Cargo.lock* ./

# Create dummy src for dependency caching
RUN mkdir src && echo 'fn main() {}' > src/main.rs
RUN cargo build --release 2>/dev/null || true

# Copy real source and build
COPY marge-core/src/ src/
RUN touch src/main.rs && cargo build --release

## ── Stage 3: Runtime image ──────────────────────
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/marge /usr/local/bin/marge
COPY --from=ui-builder /ui/dist /usr/share/marge/ui

ENV MARGE_HTTP_PORT=8124 \
    MARGE_MQTT_PORT=1884 \
    MARGE_AUTOMATIONS_PATH=/etc/marge/automations.yaml \
    MARGE_SCENES_PATH=/etc/marge/scenes.yaml \
    MARGE_DASHBOARD_PATH=/usr/share/marge/ui \
    RUST_LOG=info,marge=debug

EXPOSE 8124 1884
CMD ["marge"]
