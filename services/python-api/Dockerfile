FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

RUN mkdir -p /app/storage/logs

EXPOSE 5001

ENV LOG_DIRECTORY=/app/storage/logs

# 1 worker avoids duplicate startup seed across processes; 4 threads handle concurrency
CMD ["gunicorn", "app.main:create_app()", \
     "--bind", "0.0.0.0:5001", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
