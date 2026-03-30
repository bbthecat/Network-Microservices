@echo off
:: ============================================================
:: Lab 7 — Quick Start Script (Windows)
:: Builds and starts all containers
:: ============================================================

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Lab 7 — Network ^& Microservices Lab 7          ║
echo  ║   Docker Environment Launcher                    ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Check Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo  [1/4] Building Docker images...
docker compose build --no-cache
if %errorlevel% neq 0 (
    echo  [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo  [2/4] Starting all containers...
docker compose up -d
if %errorlevel% neq 0 (
    echo  [ERROR] Startup failed!
    pause
    exit /b 1
)

echo.
echo  [3/4] Waiting for services to become healthy (30s)...
timeout /t 30 /nobreak > nul

echo.
echo  [4/4] Status check...
docker compose ps

echo.
echo  ════════════════════════════════════════════════════
echo  Lab 7 is RUNNING! Access points:
echo.
echo    Gateway (API):   http://localhost:8000
echo    Health Check:    http://localhost:8000/health
echo    API Info:        http://localhost:8000/api/info
echo    API Data:        http://localhost:8000/api/data
echo    Grafana Logs:    http://localhost:3000  (admin/GrafanaLab7!)
echo.
echo  Run the resiliency test:
echo    python scripts\test_resiliency.py
echo.
echo  Run the live monitor:
echo    python scripts\monitor.py
echo.
echo  Stop everything:
echo    docker compose down
echo  ════════════════════════════════════════════════════
echo.
pause
