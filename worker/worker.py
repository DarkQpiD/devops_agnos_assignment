import logging
import json
import os
import time
from datetime import datetime, timezone

# ─── Load Environment Variables ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    
    # 1. เช็คก่อนว่ารันอยู่ในโหมดไหน (ถ้าไม่ได้เซ็ตค่ามา ให้มองว่าเป็น development)
    current_env = os.getenv("ENV", "development").lower()
    
    # 2. โหลดไฟล์ .env พื้นฐานก่อน (ถ้ามี)
    # load_dotenv(".env")
    
    # 3. โหลดไฟล์ .env ตามสภาพแวดล้อม (ทับค่าเดิมถ้ามีตัวแปรซ้ำกัน)
    env_filename = f".env.{current_env}"
    load_dotenv(env_filename, override=True)
    
    print(f"[*] Loaded environment from: {env_filename}")
except ImportError:
    # ถ้าไม่ได้ลง python-dotenv (เช่น รันบน K8s ที่ inject env มาให้แล้ว) ก็ให้ผ่านไป
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
        
        # ถ้าโยน Dict เข้ามาใน logger ให้เอามา Merge รวมกันเลย
        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logger():
    logger = logging.getLogger("worker")
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # ป้องกัน Handler ซ้ำซ้อนเวลามีการเรียก setup_logger หลายครั้ง
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
    # โยนเป็น Dict เข้าไปเลย ไม่ต้อง json.dumps แล้ว
    logger.info({
        "event": "timestamp_updated",
        "date": now.date().isoformat(),
        "timestamp_val": now.isoformat(),
        "worker_message": get_env_message(),
    })

# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    # ใช้ or เผื่อกรณีเซ็ต Env ไว้เป็นค่าว่าง ("") จะได้ไม่ Error
    interval = int(os.getenv("WORKER_INTERVAL", "") or 30)
    max_failures = int(os.getenv("WORKER_MAX_FAILURES", "") or 5)
    env = os.getenv("ENV", "development")
    
    logger.info({
        "event": "worker_started",
        "env_active": env,
        "interval_seconds": interval,
        "worker_message": get_env_message(),
    })
    
    consecutive_failures = 0
    
    while True:
        print(">>> LOOP RUNNING <<<", flush=True)
        try:
            logger.info({
                "event": "worker_heartbeat",
                "message": "Worker loop is running"
            })

            update_timestamp()
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            logger.error({
                "event": "job_failed",
                "error": str(e),
                "consecutive_failures": consecutive_failures,
            })
            
            # ถ้า fail ติดกันเกิน max → crash ให้ k8s restart
            if consecutive_failures >= max_failures:
                logger.error({
                    "event": "worker_crash",
                    "reason": f"exceeded max consecutive failures ({max_failures})",
                })
                raise SystemExit(1)
                
        time.sleep(interval)

if __name__ == "__main__":
    import sys
    print(">>> worker.py STARTED <<<", flush=True)
    sys.stdout.flush()

    main()