# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN mkdir -p /install && \
    pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Final ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy worker source
COPY worker.py .

# Security: run as non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Default env vars (overridden per environment)
ENV PYTHONUNBUFFERED=1 \
    ENV ENV=production \
    LOG_LEVEL=warning \
    WORKER_INTERVAL=300 \
    WORKER_MAX_FAILURES=5

CMD ["python", "worker.py"]