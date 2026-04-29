# 🚀 Agnos DevOps Assignment

A production-ready DevOps setup featuring an API service and background Worker service, fully containerized and orchestrated with Kubernetes.

---

## 📐 Architecture Overview

The system is designed for **high availability**, **scalability**, and **resilience**.

| Service | Description |
|---|---|
| **API Service** | RESTful API built with Python (FastAPI) — handles requests, exposes `/health`, outputs structured JSON logs |
| **Worker Service** | Background process running in a continuous loop with built-in failure detection and auto-exit on consecutive errors |

Both services are containerized using **multi-stage Docker builds** to minimize image size and attack surface. Kubernetes manages resource limits, health probes, and automated scaling.

```
┌─────────────────────────────────────────────┐
│              Kubernetes Cluster              │
│                                             │
│   ┌─────────────┐     ┌─────────────────┐   │
│   │ API Service │     │ Worker Service  │   │
│   │  (FastAPI)  │     │  (Background)   │   │
│   │  Port 8000  │     │   Port 8001     │   │
│   └──────┬──────┘     └────────┬────────┘   │
│          │                     │            │
│   ┌──────▼─────────────────────▼────────┐   │
│   │         Prometheus + Alerting        │   │
│   └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Setup & Installation

### Prerequisites

- Docker & Docker Compose
- A running Kubernetes cluster (Minikube, Kind, or Docker Desktop K8s)
- `kubectl` CLI installed and configured
- Helm (for Prometheus installation)

---

### Local Development (Docker Compose)

Run all services locally without Kubernetes:

```bash
docker compose up --build -d
```

Verify services are running:

```bash
# Check API health
curl http://localhost:8000/health

# Check Worker logs
docker compose logs worker -f
```

---

### Kubernetes Deployment

**1. Apply manifests per environment:**

```bash
# DEV
kubectl apply -f k8s/dev/

# UAT
kubectl apply -f k8s/uat/

# PROD
kubectl apply -f k8s/prod/
```

**2. Verify pods are running:**

```bash
kubectl get pods -n dev
kubectl get pods -n uat
kubectl get pods -n prod
```

**3. Install Prometheus for monitoring:**

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/prometheus \
  --namespace monitor --create-namespace \
  --set alertmanager.enabled=true \
  --set prometheus-pushgateway.enabled=false \
  --set server.persistentVolume.enabled=false \
  --set alertmanager.persistentVolume.enabled=false
```

---

## 🔄 CI/CD Pipeline

The project uses **GitHub Actions** for continuous integration and delivery.

```
push to main
     │
     ▼
 Lint (Flake8)
     │
     ▼
 Build Images
     │
     ▼
 Security Scan (Trivy)
     │
     ▼
 Push to GHCR
     │
     ▼
 Deploy (mocked / real)
```

| Stage | Tool | Description |
|---|---|---|
| **Lint** | Flake8 | Syntax and code quality checks |
| **Build** | Docker Buildx | Multi-stage image builds |
| **Security Scan** | Trivy | Container vulnerability scanning (CRITICAL/HIGH) |
| **Publish** | GHCR | Push verified images to GitHub Container Registry |
| **Deploy** | kubectl | Rolling updates to Kubernetes cluster |

**Trigger rules:**
- `push to main` → auto deploy to **dev**
- `workflow_dispatch` → manual deploy to **uat** or **prod** (prod requires reviewer approval)

---

## 📊 Observability & Monitoring

### Structured JSON Logging

All services output logs in structured JSON format:

```json
{
  "timestamp": "2026-04-29T08:00:00Z",
  "level": "INFO",
  "service": "api-service",
  "env": "production",
  "event": "timestamp_updated"
}
```

### Metrics

| Service | Endpoint | Metrics |
|---|---|---|
| **API** | `:8000/metrics` | Request latency, error rate |
| **Worker** | `:8001/metrics` | `worker_jobs_completed_total`, `worker_last_success_unixtime` |

### Alerting Rules

| Alert | Condition |
|---|---|
| High Error Rate | API error rate > threshold |
| Stalled Worker | Worker hasn't updated heartbeat |
| API Unavailable | Pod not responding to liveness probe |

---

## 🛡️ Failure Scenarios

### a. API crashes during peak hours

**Strategy:** Kubernetes `livenessProbe` monitors `/health` continuously. On crash, the pod restarts immediately. HPA scales pods automatically based on CPU/Memory utilization to handle peak load.

### b. Worker fails and infinitely retries

**Strategy:** The worker limits consecutive failures via `WORKER_MAX_FAILURES`. On breach, the script exits forcefully. A heartbeat file (`/tmp/healthy`) is updated on each successful run. If the worker stalls, the `livenessProbe` detects the stale file, terminates the pod, and Kubernetes spins up a fresh instance.

### c. Bad deployment is released

**Strategy:** Kubernetes uses a **Rolling Update** strategy with strict `readinessProbes`. Traffic only routes to new pods once confirmed healthy. If a bad deployment occurs, the rollout halts automatically. Rollback is instant:

```bash
kubectl rollout undo deployment/api -n <namespace>
kubectl rollout undo deployment/worker -n <namespace>
```

### d. Kubernetes node goes down

**Strategy:** When the Control Plane detects a node is `NotReady`, the Scheduler automatically evicts affected pods and reschedules them onto healthy nodes to maintain the desired replica count.

---

## 📁 Project Structure

```
.
├── api/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── worker/
│   ├── Dockerfile
│   └── worker.py
├── k8s/
│   ├── dev/
│   │   ├── configmap.yaml
│   │   ├── api_deployment.yaml
│   │   ├── api_service.yaml
│   │   ├── api_hpa.yaml
│   │   └── worker_deployment.yaml
│   ├── uat/
│   └── prod/
├── envs/
│   ├── .env.dev
│   ├── .env.uat
│   └── .env.prod
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── .trivyignore
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Environment Variables

| Variable | DEV | UAT | PROD |
|---|---|---|---|
| `ENV` | development | uat | production |
| `LOG_LEVEL` | debug | info | warning |
| `WORKER_INTERVAL` | 30s | 60s | 300s |
| `WORKER_MAX_FAILURES` | 5 | 5 | 5 |
