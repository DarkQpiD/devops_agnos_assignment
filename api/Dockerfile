# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install deps only (cache layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Final ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy app source
COPY main.py .

# Security: run as non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Default env vars (overridden per environment)
ENV ENV=production \
    LOG_LEVEL=warning \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "main.py"]