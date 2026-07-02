FROM rust:1.82-slim AS builder

WORKDIR /app

# Cache dependency layer: compile a stub before copying real source
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Build the real binary
COPY src/ src/
RUN touch src/main.rs && cargo build --release

# ── Runtime image ──────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 appuser

COPY --from=builder /app/target/release/rust-engine /usr/local/bin/rust-engine

USER appuser

EXPOSE 8080

ENV RUST_LOG=info

CMD ["rust-engine"]
