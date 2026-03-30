# Lab 7 — Network & Microservices Docker Lab

> **Replaces:** Cisco Packet Tracer / Physical Router topology  
> **Platform:** Docker-based simulation on VSCode + Docker Desktop

---

## 🗺️ Network Topology

```
INTERNET / HOST
      │
      ▼  ports 80, 8000
┌─────────────────────────────────────────┐  172.20.0.0/24
│          EDGE GATEWAY (Nginx)           │  ← frontend-dmz
│     edge-gateway  [172.20.0.10]        │
│  • Reverse Proxy + Load Balancer        │
│  • Rate Limiting (10 req/s, burst=20)  │
│  • ACL / Path-based Firewall rules      │
└────────────────┬────────────────────────┘
                 │ (proxy arm into backend-secure)
                 │  172.21.0.10
═════════════════╪═══════════════════════════ FIREWALL
                 │
┌────────────────┴────────────────────────┐  172.21.0.0/24
│              backend-secure             │  ← PRIVATE ZONE
│                                         │  (internal=true)
│  ┌──────────────┐  ┌──────────────────┐ │
│  │   api-node-1 │  │   api-node-2     │ │
│  │ [172.21.0.21]│  │ [172.21.0.22]   │ │  APP TIER
│  │  Node.js API │  │  Node.js API    │ │
│  └──────┬───────┘  └────────┬─────────┘ │
│         └─────────┬─────────┘           │
│                   │                     │
│  ┌────────────────┴──┐  ┌────────────┐ │
│  │  PostgreSQL 16     │  │  Redis 7   │ │  DATA TIER
│  │   db-primary       │  │  cache     │ │
│  │  [172.21.0.31]    │  │[172.21.0.32]│ │
│  │  Port 5432 PRIVATE│  │Port 6379   │ │
│  └───────────────────┘  │  PRIVATE   │ │
│                         └────────────┘ │
│                                        │
│  ┌────────────────────────────────────┐│
│  │       LOGGING STACK                ││
│  │  Loki[.41] Promtail[.42]          ││
│  │  Grafana[.43] → port 3000 exposed  ││
│  └────────────────────────────────────┘│
└────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
network/
├── docker-compose.yml          # Main topology definition
├── .env                        # Environment variables (secrets)
│
├── nginx/                      # Edge Gateway
│   ├── Dockerfile
│   ├── nginx.conf              # Rate limiting, logging, upstream
│   ├── logs/                   # Nginx access/error logs
│   └── conf.d/
│       ├── default.conf        # ACL, proxy rules, security headers
│       ├── loki-config.yml     # Log aggregation config
│       ├── promtail-config.yml # Log shipper (Docker → Loki)
│       └── grafana-datasource.yml
│
├── api/                        # App Tier (runs as api-1 AND api-2)
│   ├── Dockerfile
│   ├── package.json
│   └── server.js               # Express.js + PostgreSQL + Redis
│
├── db/                         # Data Tier
│   ├── init/
│   │   └── 01_init.sql         # Schema, seed data, roles
│   └── logs/
│
└── scripts/                    # Lab Tools
    ├── test_resiliency.py       # Full resiliency test suite ⭐
    ├── monitor.py               # Real-time dashboard
    └── start-lab.bat            # Windows one-click launcher
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows) — running
- Python 3.x (for test scripts): `pip install requests`

### Option A — One-click (Windows)
```
scripts\start-lab.bat
```

### Option B — Manual
```powershell
# Build & start
docker compose up -d --build

# Wait ~30s for DB init, then check
docker compose ps
curl http://localhost:8000/health
```

---

## 🧪 Lab Tests

### Run Full Resiliency Suite
```powershell
cd d:\ปั2\network
python scripts\test_resiliency.py
```

### Individual Tests (pass test number)
```powershell
python scripts\test_resiliency.py 1   # Connectivity only
python scripts\test_resiliency.py 3   # Failover only
```

### Live Monitor Dashboard
```powershell
python scripts\monitor.py
```

---

## 🔐 Security Architecture

| Security Control          | Implementation                              |
|---------------------------|---------------------------------------------|
| Network Segmentation      | 2 Docker networks (DMZ + backend-secure)    |
| DB Port ACL               | PostgreSQL/Redis NOT published to host      |
| Path-based Firewall       | Nginx blocks /db/*, /postgres, /redis       |
| Rate Limiting             | 10 req/s per IP, burst=20, HTTP 429         |
| Admin ACL                 | /admin only from 172.20.0.0/24 subnets      |
| HTTP Security Headers     | Helmet.js + X-Frame-Options, nosniff, etc.  |
| Non-root Containers       | API service runs as `appuser`               |
| DB Auth                   | SCRAM-SHA-256, read-only role for reporting |

---

## 🌐 Endpoints

| URL                          | Description                            |
|------------------------------|----------------------------------------|
| `http://localhost:8000/`     | API Gateway (rate limited)             |
| `http://localhost:8000/health` | Cluster health check               |
| `http://localhost:8000/api/info` | Node metadata (for LB testing)   |
| `http://localhost:8000/api/data` | Data from DB (Redis cached)      |
| `http://localhost:3000`      | Grafana (admin / GrafanaLab7!)         |
| `http://localhost:3100`      | Loki log API                           |

---

## 📊 Test Plan (Lab 6/7 Format)

| Test ID | Test Case                    | Expected Result                     | Command                     |
|---------|------------------------------|-------------------------------------|------------------------------|
| TC-01   | All containers running       | 5/5 containers Running              | `docker compose ps`          |
| TC-02   | HTTP Gateway reachable       | HTTP 200 on port 8000               | `curl localhost:8000/health` |
| TC-03   | Load balancing active        | Traffic to api-1 AND api-2          | `test_resiliency.py`         |
| TC-04   | DB port blocked              | Port 5432 unreachable from host     | `test_resiliency.py`         |
| TC-05   | Failover: api-1 stops        | api-2 continues serving             | `docker stop lab7-api-1`     |
| TC-06   | Zero downtime failover       | < 20% request failure during stop   | `test_resiliency.py`         |
| TC-07   | Rate limit enforced          | HTTP 429 on burst traffic           | `test_resiliency.py`         |
| TC-08   | Redis caching works          | Second request from cache < DB ms   | `test_resiliency.py`         |
| TC-09   | Cluster recovery             | api-1 rejoins after restart         | `docker start lab7-api-1`    |
| TC-10   | Centralized logging          | Logs visible in Grafana Loki        | `http://localhost:3000`      |

---

## 🛑 Stop & Cleanup

```powershell
# Stop (preserve data volumes)
docker compose down

# Full cleanup (removes volumes too)
docker compose down -v --remove-orphans
```
