import logging
import json
import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# ─── Structured JSON Logger ───────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "api-service",
            "env": os.getenv("ENV", "development"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logger():
    logger = logging.getLogger("api")
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger


logger = setup_logger()

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="API Service",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENV") != "production" else None,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    logger.info(json.dumps({
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 2),
    }))
    return response


# ─── Env Messages ─────────────────────────────────────────────────────────────

ENV_MESSAGES = {
    "development": "Running in DEVELOPMENT mode debug logs enabled, hot reload on",
    "uat":         "Running in UAT mode for testing and QA validation only",
    "production":  "Running in PRODUCTION mode stay calm and monitor dashboards",
}

def get_env_message() -> str:
    env = os.getenv("ENV", "development").lower()
    return ENV_MESSAGES.get(env, f"⚙️  Running in '{env}' mode")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    env = os.getenv("ENV", "development")
    logger.info("health check called")
    return JSONResponse(content={
        "status": "ok",
        "service": "api-service",
        "env": env,
        "message": get_env_message(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/")
async def root():
    return {
        "service": "api-service",
        "env": os.getenv("ENV", "development"),
        "message": get_env_message(),
    }


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting API Service on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
