#!/usr/bin/env python3
"""
============================================================
Lab 7 — Continuous Health Monitor
Watches all containers in real-time, alerts on failures
Press Ctrl+C to stop.
============================================================
"""

import subprocess
import requests
import time
import os
import sys
from datetime import datetime
from collections import deque

BASE_URL    = "http://localhost:8000"
REFRESH     = 2          # seconds between checks
HISTORY     = 10         # requests to keep for uptime calc
CONTAINERS  = ["lab7-nginx", "lab7-api-1", "lab7-api-2", "lab7-postgres", "lab7-redis"]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CLEAR  = "\033[2J\033[H"

history = {c: deque(maxlen=HISTORY) for c in CONTAINERS}
http_history = deque(maxlen=HISTORY)

def clear():
    print(CLEAR, end="")

def docker_status(name):
    try:
        r = subprocess.run(
            f'docker inspect -f "{{{{.State.Status}}}}" {name}',
            shell=True, capture_output=True, text=True, timeout=5
        )
        status = r.stdout.strip().strip('"')
        return status == "running", status
    except:
        return False, "error"

def http_check():
    t0 = time.time()
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=3)
        ms = int((time.time() - t0) * 1000)
        return resp.status_code == 200, resp.status_code, ms
    except:
        return False, 0, int((time.time() - t0) * 1000)

def node_check():
    """Check which node responded."""
    try:
        resp = requests.get(f"{BASE_URL}/api/info", timeout=3)
        if resp.status_code == 200:
            return resp.json().get("node_id", "?")
    except:
        pass
    return None

def uptime_pct(hist):
    if not hist:
        return 0
    return (sum(hist) / len(hist)) * 100

def bar(pct, width=20):
    filled = int((pct / 100) * width)
    color = GREEN if pct > 90 else (YELLOW if pct > 70 else RED)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RESET} {pct:5.1f}%"

def run():
    check_num = 0
    node_counts = {}
    alert_log = deque(maxlen=20)

    while True:
        check_num += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Collect status
        container_status = {}
        for c in CONTAINERS:
            ok, status = docker_status(c)
            container_status[c] = (ok, status)
            history[c].append(1 if ok else 0)
            if not ok:
                alert_log.append(f"{now}  ⚠️  {c} is {status}")

        # HTTP health check
        http_ok, http_code, http_ms = http_check()
        http_history.append(1 if http_ok else 0)
        if not http_ok:
            alert_log.append(f"{now}  ❌  HTTP gateway DOWN (code={http_code})")

        # Node rotation
        node = node_check()
        if node:
            node_counts[node] = node_counts.get(node, 0) + 1

        # ── RENDER DASHBOARD ──
        clear()
        print(f"{BOLD}{BLUE}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{BLUE}║   Lab 7 — Live Health Monitor  #{check_num:>5}               ║{RESET}")
        print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"  {CYAN}Time: {now}   Refresh: {REFRESH}s{RESET}\n")

        # Container status table
        print(f"  {BOLD}─── Container Status ──────────────────────────────────{RESET}")
        print(f"  {'Container':<22} {'Status':<12} {'Uptime':>20}")
        print(f"  {'─'*22} {'─'*12} {'─'*20}")
        for c in CONTAINERS:
            ok, status = container_status[c]
            color  = GREEN if ok else RED
            icon   = "●" if ok else "○"
            pct    = uptime_pct(history[c])
            bar_s  = bar(pct, width=10)
            short  = c.replace("lab7-", "")
            print(f"  {color}{icon}{RESET} {short:<20} {color}{status:<12}{RESET} {bar_s}")

        # HTTP Gateway status
        print(f"\n  {BOLD}─── HTTP Gateway (Port 8000) ──────────────────────────{RESET}")
        gw_color = GREEN if http_ok else RED
        gw_icon  = "●" if http_ok else "○"
        gw_pct   = uptime_pct(http_history)
        print(f"  {gw_color}{gw_icon}{RESET}  Gateway Health      HTTP {http_code}   {http_ms}ms   {bar(gw_pct, 10)}")

        # Load balancer distribution
        if node_counts:
            print(f"\n  {BOLD}─── Load Balancer Distribution ────────────────────────{RESET}")
            total_reqs = sum(node_counts.values())
            for n, cnt in sorted(node_counts.items()):
                pct = (cnt / total_reqs) * 100
                print(f"  {'  ' + n:<22} {cnt:>5} req  {bar(pct, 10)}")
            print(f"  {'  Total':<22} {total_reqs:>5} req")

        # Current node serving
        if node:
            print(f"\n  {CYAN}  Last request served by: {BOLD}{node}{RESET}")

        # Recent alerts
        if alert_log:
            print(f"\n  {BOLD}{YELLOW}─── Recent Alerts ─────────────────────────────────────{RESET}")
            for alert in list(alert_log)[-5:]:
                print(f"  {YELLOW}{alert}{RESET}")

        print(f"\n  {BLUE}Press Ctrl+C to stop{RESET}")

        time.sleep(REFRESH)

if __name__ == "__main__":
    print(f"{BOLD}{CYAN}Starting Lab 7 Health Monitor...{RESET}")
    time.sleep(0.5)
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Monitor stopped.{RESET}")
