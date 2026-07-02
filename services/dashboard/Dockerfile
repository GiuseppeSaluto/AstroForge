FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

USER appuser

# Talk to the other services by their Docker Compose service names by default;
# overridden locally when running outside Compose (see CLAUDE.md).
ENV API_BASE_URL=http://python-api:5001
ENV RUST_ENGINE_URL=http://rust-engine:8080

CMD ["python", "-m", "app.main"]
