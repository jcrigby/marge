FROM rust:1.83-slim-bookworm AS builder
WORKDIR /build

# Copy manifest first for layer caching
COPY Cargo.toml Cargo.lock* ./

# Create dummy src for dependency caching
RUN mkdir src && echo 'fn main() {}' > src/main.rs
RUN cargo build --release 2>/dev/null || true

# Copy real source and build
COPY src/ src/
RUN touch src/main.rs && cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/marge /usr/local/bin/marge

ENV MARGE_HTTP_PORT=8124 \
    MARGE_AUTOMATIONS_PATH=/etc/marge/automations.yaml \
    MARGE_SCENES_PATH=/etc/marge/scenes.yaml \
    RUST_LOG=info,marge=debug

EXPOSE 8124
CMD ["marge"]
