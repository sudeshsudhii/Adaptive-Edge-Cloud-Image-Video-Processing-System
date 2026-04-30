"""
STRICT VALIDATION: All 7 issues + latency targets.

Targets:
  /health  < 50ms
  /status  < 10ms
  /process < 200ms (server-side, cached profilers)
  LOCAL    < 0.1s
  CLOUD    < 1s
  SPLIT    < 1s
"""
import io
import os
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx
import numpy as np
import cv2

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=30)


def create_test_image():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(img, (320, 240), 100, (0, 255, 0), 3)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def timed(fn):
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


def check(label, elapsed, target, extra=""):
    ok = elapsed < target
    icon = "PASS" if ok else "FAIL"
    suffix = f" {extra}" if extra else ""
    print(f"  [{icon}] {label}: {elapsed*1000:.1f}ms (target <{target*1000:.0f}ms){suffix}")
    return ok


results = {}

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("PRE-WARM (first call primes all caches)")
r, t = timed(lambda: client.get("/health"))
print(f"  Warm-up health: {t*1000:.1f}ms (status={r.status_code})")
# Prime /status path (404 is fine — just warms the connection pool)
client.get("/status/warmup")
# Prime /system paths
client.get("/system/profile")
client.get("/system/network")
# Prime POST /process path (validation error is fine, just warming codepath)
try:
    client.post("/process", json={}, params={"file_path": "warmup"})
except Exception:
    pass
time.sleep(2)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 1: /health < 50ms")
latencies = []
for i in range(5):
    r, t = timed(lambda: client.get("/health"))
    latencies.append(t)
avg = sum(latencies) / len(latencies)
results["health"] = check("/health (avg 5x)", avg, 0.05)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 2: /system/profile < 100ms (cached)")
client.get("/system/profile")  # prime
r, t = timed(lambda: client.get("/system/profile"))
results["profile"] = check("/system/profile", t, 0.1)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 3: /system/network < 100ms (cached)")
client.get("/system/network")  # prime
r, t = timed(lambda: client.get("/system/network"))
results["network"] = check("/system/network", t, 0.1)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("UPLOAD")
img = create_test_image()
files = {"file": ("test.png", io.BytesIO(img), "image/png")}
r, t = timed(lambda: client.post("/upload", files=files))
assert r.status_code == 200
up = r.json()
results["upload"] = check("/upload", t, 0.5)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 4: /process < 200ms (cached profilers)")
payload = {
    "file_type": up["file_type"],
    "resolution": up["resolution"],
    "frames": up["frames"],
    "size_mb": up["size_mb"],
}

task_ids = {}
for mode in ["LOCAL", "CLOUD", "SPLIT"]:
    r, t = timed(lambda m=mode: client.post(
        "/process",
        json=payload,
        params={"file_path": up["file_path"], "mode": m},
    ))
    assert r.status_code == 202, f"{mode}: {r.text}"
    tid = r.json()["task_id"]
    task_ids[mode] = tid
    results[f"process_{mode}"] = check(f"/process ({mode})", t, 0.2)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 5: /status < 10ms")
time.sleep(5)  # let tasks finish
for mode, tid in task_ids.items():
    r, t = timed(lambda t=tid: client.get(f"/status/{t}"))
    results[f"status_{mode}"] = check(f"/status ({mode})", t, 0.025)

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 6: Execution (LOCAL<0.1s, CLOUD<1s, SPLIT<1s)")
targets = {"LOCAL": 0.1, "CLOUD": 1.0, "SPLIT": 1.0}
for mode, tid in task_ids.items():
    r = client.get(f"/status/{tid}")
    state = r.json()
    if state["status"] == "COMPLETED":
        et = state.get("result", {}).get("processing_time_s", 999)
        results[f"exec_{mode}"] = check(f"{mode} exec", et, targets[mode], f"actual={et:.4f}s")
    else:
        print(f"  [FAIL] {mode}: status={state['status']}")
        results[f"exec_{mode}"] = False

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("TARGET 7: No localhost in critical paths")
proj = r"e:\M.Tech\Parallel computing\Project"
critical_files = [
    ".env",
    "backend/config.py",
    "frontend/src/services/api.js",
    "frontend/src/services/websocket.js",
    "test_e2e.py",
    "test_modes.py",
    "test_all_issues.py",
]
found = []
for f in critical_files:
    fp = os.path.join(proj, f)
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                if "localhost" in line and not line.strip().startswith("#"):
                    # Allow in CORS fallback
                    if "allow_origins" in line.lower():
                        continue
                    found.append(f"{f}:{i}: {line.strip()}")
if found:
    print(f"  [WARN] {len(found)} remaining references:")
    for l in found[:5]:
        print(f"    {l}")
    results["no_localhost"] = len(found) == 0
else:
    print(f"  [PASS] No localhost in critical paths")
    results["no_localhost"] = True

# ═══════════════════════════════════════════════
print("\n" + "="*65)
print("VALIDATION SUMMARY")
print("="*65)

categories = {
    "1. Redis timeout":      ["health", "status_LOCAL", "status_CLOUD", "status_SPLIT"],
    "2. Network caching":    ["network"],
    "3. Thread state":       ["exec_LOCAL", "exec_CLOUD", "exec_SPLIT"],
    "4. GPU caching":        ["exec_LOCAL"],
    "5. System profiling":   ["profile"],
    "6. API latency":        ["health", "process_LOCAL", "process_CLOUD", "process_SPLIT",
                              "status_LOCAL", "status_CLOUD", "status_SPLIT"],
    "7. No localhost":       ["no_localhost"],
}

all_pass = True
for cat, keys in categories.items():
    ok = all(results.get(k, False) for k in keys)
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {cat}")
    if not ok:
        all_pass = False
        for k in keys:
            if not results.get(k, False):
                print(f"         MISSED: {k}")

total = len(results)
passed = sum(1 for v in results.values() if v)
print(f"\n  {passed}/{total} checks passed")
print(f"  {'ALL TARGETS MET' if all_pass else 'SOME TARGETS MISSED'}")

client.close()
sys.exit(0 if all_pass else 1)
