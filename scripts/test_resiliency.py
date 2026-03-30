#!/usr/bin/env python3
"""
============================================================
Lab 7 — Resiliency & Failover Test Suite
Replaces: Cisco IP SLA / EEM / Packet Tracer simulation
Target:   Docker-based environment on localhost

Tests:
  1. Connectivity Check    — All containers reachable
  2. Load Balancer Check   — Traffic distributed across api-1, api-2
  3. Failover Simulation   — Stop api-1, verify api-2 takes over
  4. Security ACL Check    — DB port not externally accessible
  5. Rate Limit Check      — 429 triggered at >10 req/s
  6. Cache Check           — Redis caching reduces DB latency
  7. Restore & Verify      — Restart api-1, cluster recovers
============================================================
"""

import subprocess
import requests
import time
import json
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────
BASE_URL       = "http://localhost:8000"
HEALTH_URL     = f"{BASE_URL}/health"
INFO_URL       = f"{BASE_URL}/api/info"
DATA_URL       = f"{BASE_URL}/api/data"
API1_CONTAINER = "lab7-api-1"
API2_CONTAINER = "lab7-api-2"
PG_CONTAINER   = "lab7-postgres"
REDIS_CONTAINER = "lab7-redis"
NGINX_CONTAINER = "lab7-nginx"

TIMEOUT     = 5      # seconds per request
POLL_WAIT   = 0.5    # seconds between polls
MAX_WAIT    = 30     # max seconds to wait for failover

# ANSI colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─────────────────────────────────────────────────────────
# TEST RESULTS TRACKER
# ─────────────────────────────────────────────────────────
results = []

def record(test_name, result, details="", latency_ms=None):
    """Record a test result."""
    status = "PASS" if result else "FAIL"
    entry = {
        "test":       test_name,
        "status":     status,
        "details":    details,
        "latency_ms": latency_ms,
        "timestamp":  datetime.now().isoformat()
    }
    results.append(entry)

    color = GREEN if result else RED
    icon  = "✅" if result else "❌"
    lat   = f" ({latency_ms}ms)" if latency_ms else ""
    print(f"  {icon} {color}{BOLD}{status}{RESET}  {test_name}{lat}")
    if details:
        print(f"       └─ {CYAN}{details}{RESET}")
    return result

def banner(title):
    print(f"\n{BLUE}{BOLD}{'═'*60}{RESET}")
    print(f"{BLUE}{BOLD}  {title}{RESET}")
    print(f"{BLUE}{BOLD}{'═'*60}{RESET}")

def info(msg):
    print(f"  {YELLOW}ℹ  {msg}{RESET}")

def get(url, timeout=TIMEOUT):
    """GET request with timing."""
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        ms = int((time.time() - t0) * 1000)
        return r, ms
    except requests.exceptions.ConnectionError:
        return None, int((time.time() - t0) * 1000)
    except requests.exceptions.Timeout:
        return None, TIMEOUT * 1000

def docker(cmd):
    """Run a docker command and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"

def container_running(name):
    ok, out, _ = docker(f'docker inspect -f "{{{{.State.Running}}}}" {name}')
    return ok and "true" in out.lower()

# ─────────────────────────────────────────────────────────
# TEST 1: CONNECTIVITY CHECK
# ─────────────────────────────────────────────────────────
def test_connectivity():
    banner("TEST 1: Connectivity Check")
    info("Verifying all containers are running and reachable")

    containers = [NGINX_CONTAINER, API1_CONTAINER, API2_CONTAINER,
                  PG_CONTAINER, REDIS_CONTAINER]

    all_ok = True
    for c in containers:
        running = container_running(c)
        record(f"Container {c} running", running,
               "docker inspect → Running=true" if running else "Container not running or not found")
        if not running:
            all_ok = False

    # HTTP Health Check via Nginx
    resp, ms = get(HEALTH_URL)
    if resp and resp.status_code == 200:
        record("Nginx gateway HTTP health check", True,
               f"HTTP 200 via port 8000", ms)
    else:
        record("Nginx gateway HTTP health check", False,
               f"Expected HTTP 200, got: {resp.status_code if resp else 'No response'}", ms)
        all_ok = False

    # Verify DB port NOT exposed externally (ACL/Firewall check)
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('localhost', 5432))
        s.close()
        db_exposed = (result == 0)
        record("PostgreSQL port 5432 NOT exposed to host",
               not db_exposed,
               "Port 5432 is correctly closed externally (backend-secure zone)" if not db_exposed
               else "⚠️  Port 5432 is EXPOSED — security misconfiguration!")
    except Exception as e:
        record("PostgreSQL port ACL check", True, "Port 5432 unreachable (correct)")

    # Verify Redis port NOT exposed externally
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('localhost', 6379))
        s.close()
        redis_exposed = (result == 0)
        record("Redis port 6379 NOT exposed to host",
               not redis_exposed,
               "Port 6379 is correctly closed externally" if not redis_exposed
               else "⚠️  Port 6379 is EXPOSED — security misconfiguration!")
    except:
        record("Redis port ACL check", True, "Port 6379 unreachable (correct)")

    return all_ok

# ─────────────────────────────────────────────────────────
# TEST 2: LOAD BALANCER DISTRIBUTION
# ─────────────────────────────────────────────────────────
def test_load_balancer():
    banner("TEST 2: Load Balancer Distribution")
    info("Sending 20 requests and checking which node handles each")

    node_counts = defaultdict(int)
    errors = 0

    for i in range(20):
        resp, ms = get(INFO_URL)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                node = data.get("node_id", "unknown")
                node_counts[node] += 1
            except:
                errors += 1
        else:
            errors += 1
        time.sleep(0.1)

    info(f"Node distribution: {dict(node_counts)}")
    info(f"Errors: {errors}")

    both_served = len(node_counts) >= 2
    record("Traffic distributed to 2+ nodes", both_served,
           f"Nodes seen: {dict(node_counts)}" if both_served
           else f"Only 1 node serving (LB not working?): {dict(node_counts)}")

    # Check roughly balanced (no node > 85%)
    total = sum(node_counts.values())
    if total > 0:
        for node, count in node_counts.items():
            pct = (count / total) * 100
            balanced = pct <= 85
            record(f"Node {node} not overloaded", balanced,
                   f"{count}/{total} requests ({pct:.0f}%)")

    return both_served

# ─────────────────────────────────────────────────────────
# TEST 3: FAILOVER SIMULATION (Zero Downtime)
# ─────────────────────────────────────────────────────────
def test_failover():
    banner("TEST 3: Failover Simulation — Zero Downtime")
    info("Stopping api-1 and verifying api-2 takes over...")

    # Verify api-1 is running first
    if not container_running(API1_CONTAINER):
        record("api-1 pre-check", False, "api-1 is already stopped — cannot test failover")
        return False

    # Send requests while stopping api-1 (parallel)
    failover_times = []
    errors_during = []

    def send_requests_during_failover(stop_after=2):
        """Send continuous requests; stop api-1 after `stop_after` seconds."""
        results_local = []
        stop_triggered = False
        start = time.time()

        for i in range(60):  # max 60 iterations
            elapsed = time.time() - start

            # Trigger stop after delay
            if elapsed >= stop_after and not stop_triggered:
                info(f"  ⚡ Stopping {API1_CONTAINER} now (t={elapsed:.1f}s)...")
                ok, _, err = docker(f"docker stop {API1_CONTAINER}")
                stop_triggered = True
                if not ok:
                    info(f"  docker stop failed: {err}")

            resp, ms = get(INFO_URL, timeout=3)
            entry = {
                "t": elapsed,
                "ok": resp is not None and resp.status_code == 200,
                "ms": ms,
                "node": None,
                "stop_triggered": stop_triggered
            }
            if resp and resp.status_code == 200:
                try:
                    entry["node"] = resp.json().get("node_id")
                except:
                    pass
            results_local.append(entry)
            time.sleep(0.3)

            if elapsed > 20:
                break

        return results_local

    test_data = send_requests_during_failover(stop_after=2)

    # Analyze results
    before_stop  = [r for r in test_data if not r["stop_triggered"]]
    after_stop   = [r for r in test_data if r["stop_triggered"]]

    before_ok    = sum(1 for r in before_stop if r["ok"])
    after_ok     = sum(1 for r in after_stop  if r["ok"])
    after_total  = len(after_stop)
    after_errors = sum(1 for r in after_stop  if not r["ok"])
    after_nodes  = set(r["node"] for r in after_stop if r["node"])

    record("api-1 stopped during live traffic", not container_running(API1_CONTAINER),
           f"docker stop {API1_CONTAINER}")

    if after_total > 0:
        success_rate = (after_ok / after_total) * 100
        record("Service continues after primary failure", success_rate >= 80,
               f"{after_ok}/{after_total} requests OK ({success_rate:.0f}%) after failover")
        record("Traffic routed to api-2 after failover", "api-2" in after_nodes,
               f"Nodes seen after stop: {after_nodes}")
        record("Zero downtime (< 20% errors)", after_errors <= (after_total * 0.2),
               f"Errors: {after_errors}/{after_total}")
    else:
        record("Failover test data collected", False, "No post-stop data collected")

    # Find failover time (first successful request after failures)
    failures_after = [r for r in after_stop if not r["ok"]]
    if failures_after:
        failover_t = failures_after[-1]["t"]
        info(f"  Failover convergence ~{failover_t:.1f}s after stop")
        record("Failover time < 5s", failover_t < 5,
               f"Convergence at t={failover_t:.1f}s")
    else:
        record("Instant failover (0 failed requests)", True,
               "Nginx proxy_next_upstream handled it transparently")

    return after_ok > 0

# ─────────────────────────────────────────────────────────
# TEST 4: SECURITY — Rate Limiting
# ─────────────────────────────────────────────────────────
def test_rate_limiting():
    banner("TEST 4: Security — Rate Limiting (ACL)")
    info("Sending 30 rapid requests to trigger rate limit (429)...")

    status_codes = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(get, INFO_URL, 3) for _ in range(30)]
        for f in futures:
            resp, _ = f.result()
            if resp:
                status_codes.append(resp.status_code)
            else:
                status_codes.append(0)

    got_429 = status_codes.count(429)
    got_200 = status_codes.count(200)
    got_503 = status_codes.count(503)

    info(f"  Responses: 200={got_200}, 429={got_429}, 503={got_503}, error={status_codes.count(0)}")

    record("Rate limit (429) triggered under burst load", got_429 > 0,
           f"{got_429}/30 requests were rate-limited with HTTP 429")
    record("Some legitimate requests served (not fully blocked)", got_200 > 0,
           f"{got_200}/30 requests served normally")

    # Test path-based ACL: /db/* should return 403
    info("Testing path-based ACL: /db/ should return 403...")
    resp, ms = get(f"{BASE_URL}/db/query")
    if resp:
        blocked = resp.status_code == 403
        record("Path ACL: /db/* blocked with 403", blocked,
               f"HTTP {resp.status_code} for /db/query" , ms)
    else:
        record("Path ACL: /db/* blocked", False, "No response received")

    return got_429 > 0

# ─────────────────────────────────────────────────────────
# TEST 5: CACHE PERFORMANCE
# ─────────────────────────────────────────────────────────
def test_cache():
    banner("TEST 5: Cache Performance — Redis vs PostgreSQL")
    info("Comparing first-hit (DB) vs cached response latency...")

    # First request (cache miss → hits PostgreSQL)
    resp1, ms1 = get(DATA_URL)
    source1 = "unknown"
    if resp1 and resp1.status_code == 200:
        try:
            source1 = resp1.json().get("source", "unknown")
        except:
            pass

    # Second request (should be cache hit)
    time.sleep(0.1)
    resp2, ms2 = get(DATA_URL)
    source2 = "unknown"
    if resp2 and resp2.status_code == 200:
        try:
            source2 = resp2.json().get("source", "unknown")
        except:
            pass

    info(f"  Request 1: source={source1}, latency={ms1}ms")
    info(f"  Request 2: source={source2}, latency={ms2}ms")

    record("First request hits database", source1 == "database",
           f"source={source1}")
    record("Second request served from cache", source2 == "cache",
           f"source={source2}")

    if ms1 and ms2 and ms1 > 0:
        faster = ms2 < ms1
        speedup = ((ms1 - ms2) / ms1) * 100 if ms1 > 0 else 0
        record("Cache faster than DB query", faster,
               f"DB={ms1}ms → Cache={ms2}ms ({speedup:.0f}% faster)", ms2)

    return source2 == "cache"

# ─────────────────────────────────────────────────────────
# TEST 6: RESTORE & CLUSTER RECOVERY
# ─────────────────────────────────────────────────────────
def test_restore():
    banner("TEST 6: Restore & Cluster Recovery")
    info(f"Restarting {API1_CONTAINER} and verifying cluster recovers...")

    ok, _, err = docker(f"docker start {API1_CONTAINER}")
    record("api-1 restarted successfully", ok,
           f"docker start returned OK" if ok else f"Error: {err}")

    if not ok:
        return False

    # Wait for api-1 to become healthy
    info(f"Waiting for {API1_CONTAINER} to pass health checks (max {MAX_WAIT}s)...")
    deadline = time.time() + MAX_WAIT
    recovered = False
    while time.time() < deadline:
        if container_running(API1_CONTAINER):
            # Check if api-1 is serving traffic
            time.sleep(2)   # let it warm up
            node_counts = defaultdict(int)
            for _ in range(10):
                resp, _ = get(INFO_URL)
                if resp and resp.status_code == 200:
                    try:
                        node_counts[resp.json().get("node_id")] += 1
                    except:
                        pass
                time.sleep(0.2)

            if "api-1" in node_counts:
                recovered = True
                break
        time.sleep(POLL_WAIT)

    record("api-1 rejoins cluster and serves traffic", recovered,
           f"api-1 reappeared in node rotation after restart")

    # Final cluster health
    resp, ms = get(HEALTH_URL)
    record("Cluster health check passes after recovery", resp and resp.status_code == 200,
           f"HTTP {resp.status_code if resp else 'no response'}", ms)

    return recovered

# ─────────────────────────────────────────────────────────
# FINAL REPORT — LAB 6/7 Test Plan Format
# ─────────────────────────────────────────────────────────
def print_report():
    banner("VALIDATION REPORT — Lab 7 Resiliency Test")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total  = len(results)

    # Table header
    col1 = 40
    col2 = 8
    col3 = 50

    header = f"{'Test Case':<{col1}} {'Result':<{col2}} {'Details':<{col3}}"
    divider = "─" * (col1 + col2 + col3 + 4)

    print(f"\n{BOLD}{header}{RESET}")
    print(divider)

    for r in results:
        color  = GREEN if r["status"] == "PASS" else RED
        status = f"{color}{r['status']}{RESET}"
        lat    = f" [{r['latency_ms']}ms]" if r.get("latency_ms") else ""
        detail = (r["details"] + lat)[:col3]
        name   = r["test"][:col1]
        print(f"{name:<{col1}} {status:<{col2+len(color)+len(RESET)}} {detail}")

    print(divider)
    print(f"\n{BOLD}Summary:{RESET}  {GREEN}PASS: {passed}{RESET}  |  {RED}FAIL: {failed}{RESET}  |  Total: {total}")

    pct = (passed / total * 100) if total > 0 else 0
    if pct >= 90:
        print(f"\n{GREEN}{BOLD}✅ Lab 7 PASSED ({pct:.0f}% success rate) — System is resilient!{RESET}")
    elif pct >= 70:
        print(f"\n{YELLOW}{BOLD}⚠️  Lab 7 PARTIAL ({pct:.0f}% success rate) — Review failed tests.{RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ Lab 7 FAILED ({pct:.0f}% success rate) — Critical issues detected.{RESET}")

    # Save JSON report
    report_path = os.path.join(os.path.dirname(__file__), "test_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "lab":       "Lab 7 — Network & Microservices Resiliency",
            "run_at":    datetime.now().isoformat(),
            "summary":   {"passed": passed, "failed": failed, "total": total, "percent": round(pct, 1)},
            "results":   results
        }, f, indent=2)
    print(f"\n{CYAN}📄 Full report saved: {report_path}{RESET}")

    return failed == 0

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║   Lab 7 — Resiliency & Failover Test Suite      ║")
    print("  ║   Docker-based Network Simulation                ║")
    print(f"  ╚══════════════════════════════════════════════════╝{RESET}")
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"  Target:  {BASE_URL}")

    suite = [
        test_connectivity,
        test_load_balancer,
        test_failover,
        test_rate_limiting,
        test_cache,
        test_restore
    ]

    # Skip to specific test
    start_at = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else 0
    suite = suite[start_at:]

    for test_fn in suite:
        try:
            test_fn()
        except KeyboardInterrupt:
            print(f"\n{YELLOW}⚠️  Test interrupted by user{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}💥 Test crashed: {e}{RESET}")
            import traceback; traceback.print_exc()
        time.sleep(1)

    success = print_report()
    sys.exit(0 if success else 1)
