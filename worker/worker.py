import sys
import logging
import json
import os
import time
from datetime import datetime, timezone

# ✅ นำเข้าไลบรารีสำหรับ Prometheus Metrics
from prometheus_client import start_http_server, Counter, Gauge

# ─── Metrics ──────────────────────────────────────────────────────────────────
# สร้างตัวแปรเก็บสถิติเพื่อส่งให้ Prometheus
JOBS_COMPLETED = Counter('worker_jobs_completed_total', 'Total number of successful jobs')
LAST_SUCCESS_TIMESTAMP = Gauge('worker_last_success_unixtime', 'Last time a job was successful')

# ─── Load Environment Variables ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    current_env = os.getenv("ENV", "development").lower()
    env_filename = f".env.{current_env}"
    load_dotenv(env_filename, override=True)
    print(f"[*] Loaded environment from: {env_filename}")
except ImportError:
    pass

# ─── Structured JSON Logger ───────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "worker-service",
            "env": os.getenv("ENV", "development"),
        }
        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logger():
    logger = logging.getLogger("worker")
    handler = logging.StreamHandler(sys.stdout) 
    handler.setFormatter(JSONFormatter())
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

logger = setup_logger()

# ─── Env Messages ─────────────────────────────────────────────────────────────
ENV_MESSAGES = {
    "development": "Worker running in DEVELOPMENT mode",
    "uat":         "Worker running in UAT mode",
    "production":  "Worker running in PRODUCTION mode",
}

def get_env_message() -> str:
    env = os.getenv("ENV", "development").lower()
    return ENV_MESSAGES.get(env, f"Worker running in '{env}' mode")

# ─── Worker Job ───────────────────────────────────────────────────────────────
def update_timestamp():
    now = datetime.now(timezone.utc)
    logger.info({
        "event": "timestamp_updated",
        "date": now.date().isoformat(),
        "timestamp_val": now.isoformat(),
        "worker_message": get_env_message(),
    })

# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    interval = int(os.getenv("WORKER_INTERVAL", "") or 30)
    max_failures = int(os.getenv("WORKER_MAX_FAILURES", "") or 5)
    env = os.getenv("ENV", "development")
    
    logger.info({
        "event": "worker_started",
        "env_active": env,
        "interval_seconds": interval,
        "worker_message": get_env_message(),
    })
    
    # ✅ เปิด HTTP Server ที่พอร์ต 8001 เพื่อให้ Prometheus เข้ามาดึง Metrics
    start_http_server(8001)
    logger.info({"event": "metrics_server_started", "port": 8001})
    
    consecutive_failures = 0
    
    while True:
        try:
            logger.info({
                "event": "worker_heartbeat",
                "message": "Worker loop is running"
            })

            update_timestamp()
            
            # ✅ เมื่อทำงานสำเร็จ ให้อัปเดต Metrics
            JOBS_COMPLETED.inc()
            LAST_SUCCESS_TIMESTAMP.set_to_current_time()
            
            consecutive_failures = 0
            
            # ✅ สร้าง Heartbeat File ให้ Kubernetes Liveness Probe เข้ามาเช็ค
            with open("/tmp/healthy", "w") as f:
                f.write("ok")
                
        except Exception as e:
            consecutive_failures += 1
            logger.error({
                "event": "job_failed",
                "error": str(e),
                "consecutive_failures": consecutive_failures,
            })
            
            # ✅ ถ้าเกิด Error ลบ Heartbeat File ทิ้ง เพื่อบอก K8s ว่าเรามีปัญหาแล้วนะ
            if os.path.exists("/tmp/healthy"):
                os.remove("/tmp/healthy")
            
            # ถ้า fail ติดกันเกิน max → crash ให้ k8s restart
            if consecutive_failures >= max_failures:
                logger.error({
                    "event": "worker_crash",
                    "reason": f"exceeded max consecutive failures ({max_failures})",
                })
                raise SystemExit(1)
                
        time.sleep(interval)

if __name__ == "__main__":
    print(">>> worker.py STARTED <<<", flush=True)
    sys.stdout.flush()
    main()