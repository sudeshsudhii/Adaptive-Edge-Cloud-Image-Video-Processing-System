"""
Full verification test: all 5 issues + latency benchmarks.

Tests:
  1. Redis timeout bottleneck — no >2s status polls
  2. Network profiling delay — cached repeated calls
  3. Thread state inconsistency — shared state across threads
  4. GPU overhead — fast repeated processing (no re-init)
  5. Slow API response — all endpoints under 2s latency target
"""
import io
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx
import numpy as np
import cv2

BASE = "http://127.0.0.1:8000"
LATENCY_TARGET = 2.0  # seconds


def create_test_image():
    img = np.zeros((640, 480, 3), dtype=np.uint8)
    cv2.circle(img, (320, 240), 100, (0, 255, 0), 3)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def timed(label, fn, target=LATENCY_TARGET):
    start = time.time()
    result = fn()
    elapsed = time.time() - start
    ok = elapsed < target
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label}: {elapsed:.3f}s {'(target <'+str(target)+'s)' if not ok else ''}")
    return ok, elapsed, result


def upload():
    img = create_test_image()
    files = {"file": ("test.png", io.BytesIO(img), "image/png")}
    r = httpx.post(f"{BASE}/upload", files=files, timeout=15)
    assert r.status_code == 200
    return r.json()


def process_task(upload_data, mode):
    payload = {
        "file_type": upload_data["file_type"],
        "resolution": upload_data["resolution"],
        "frames": upload_data["frames"],
        "size_mb": upload_data["size_mb"],
    }
    r = httpx.post(
        f"{BASE}/process",
        json=payload,
        params={"file_path": upload_data["file_path"], "mode": mode},
        timeout=30,
    )
    assert r.status_code == 202
    return r.json()["task_id"]


def poll_until_done(task_id, timeout=30):
    start = time.time()
    max_poll_latency = 0
    while time.time() - start < timeout:
        t0 = time.time()
        r = httpx.get(f"{BASE}/status/{task_id}", timeout=10)
        poll_time = time.time() - t0
        max_poll_latency = max(max_poll_latency, poll_time)
        if r.status_code == 200:
            state = r.json()
            if state["status"] in ("COMPLETED", "FAILED"):
                return state, max_poll_latency
        time.sleep(0.5)
    return None, max_poll_latency


def main():
    results = {}

    # ═══ Issue 1: Redis timeout bottleneck ═══
    print("\n" + "="*60)
    print("ISSUE 1: Redis Timeout Bottleneck")
    print("  Target: /status polls < 0.5s each (not 4s)")
    ok1, t1, _ = timed("Health check", lambda: httpx.get(f"{BASE}/health", timeout=10))
    results["Redis: health"] = ok1

    # ═══ Issue 5: Slow API response — /system/profile ═══
    print("\n" + "="*60)
    print("ISSUE 5: Slow API Response (System Profile)")
    ok_sp, t_sp, _ = timed("System profile (1st)", lambda: httpx.get(f"{BASE}/system/profile", timeout=10))
    results["API: profile_1st"] = ok_sp
    ok_sp2, t_sp2, _ = timed("System profile (2nd, cached)", lambda: httpx.get(f"{BASE}/system/profile", timeout=10), target=0.5)
    results["API: profile_cached"] = ok_sp2

    # ═══ Issue 2: Network profiling delay ═══
    print("\n" + "="*60)
    print("ISSUE 2: Network Profiling Delay (TTL cache)")
    ok_n1, t_n1, _ = timed("Network profile (1st)", lambda: httpx.get(f"{BASE}/system/network", timeout=15))
    ok_n2, t_n2, _ = timed("Network profile (2nd, cached)", lambda: httpx.get(f"{BASE}/system/network", timeout=10), target=0.5)
    results["Network: 1st"] = ok_n1
    results["Network: cached"] = ok_n2

    # ═══ Issue 3/4/5: Upload + 3x process (thread state + GPU overhead + API latency) ═══
    print("\n" + "="*60)
    print("ISSUE 3: Thread State Consistency + ISSUE 4: GPU Overhead + ISSUE 5: API Latency")

    ok_up, _, up_data = timed("Upload", upload)
    results["Upload"] = ok_up

    # Process 3 tasks rapidly to test singleton caching, GPU cache, thread state
    for i, mode in enumerate(["LOCAL", "CLOUD", "SPLIT"], 1):
        print(f"\n  --- Task {i}: {mode} ---")
        ok_proc, t_proc, task_id = timed(
            f"POST /process ({mode})",
            lambda m=mode: process_task(up_data, m),
        )
        results[f"Process_{mode}"] = ok_proc

        state, max_poll = poll_until_done(task_id)
        ok_poll = max_poll < 0.5  # each poll < 500ms
        icon_poll = "✅" if ok_poll else "❌"
        print(f"  {icon_poll} Max /status poll latency: {max_poll:.3f}s (target <0.5s)")
        results[f"Poll_{mode}"] = ok_poll

        if state and state["status"] == "COMPLETED":
            result = state.get("result", {})
            print(f"  ✅ {mode} completed in {result.get('processing_time_s', '?')}s")
            results[f"Complete_{mode}"] = True
        else:
            status = state.get("status", "UNKNOWN") if state else "TIMEOUT"
            print(f"  ❌ {mode} status: {status}")
            results[f"Complete_{mode}"] = False

    # ═══ Rapid-fire: 2nd and 3rd tasks should be faster (singletons cached) ═══
    print("\n" + "="*60)
    print("ISSUE 4: GPU Overhead (2nd task should be instant init)")
    ok_rapid, t_rapid, task_id2 = timed(
        "POST /process (LOCAL repeat)",
        lambda: process_task(up_data, "LOCAL"),
        target=1.0,  # 2nd process should be <1s with caching
    )
    results["GPU_cached_2nd"] = ok_rapid

    state2, _ = poll_until_done(task_id2)
    results["Repeat_LOCAL"] = (state2 is not None and state2["status"] == "COMPLETED")

    # ═══ Summary ═══
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)

    issue_map = {
        "Redis timeout bottleneck":    ["Redis: health", "Poll_LOCAL", "Poll_CLOUD", "Poll_SPLIT"],
        "Network profiling delay":     ["Network: 1st", "Network: cached"],
        "Thread state inconsistency":  ["Complete_LOCAL", "Complete_CLOUD", "Complete_SPLIT"],
        "GPU overhead":                ["GPU_cached_2nd", "Repeat_LOCAL"],
        "Slow API response":           ["API: profile_1st", "API: profile_cached", "Upload",
                                        "Process_LOCAL", "Process_CLOUD", "Process_SPLIT"],
    }

    all_pass = True
    for issue, keys in issue_map.items():
        ok = all(results.get(k, False) for k in keys)
        icon = "✅" if ok else "❌"
        print(f"  {icon} {issue}")
        for k in keys:
            sub = "✓" if results.get(k, False) else "✗"
            print(f"      {sub} {k}")
        if not ok:
            all_pass = False

    print(f"\n  {'✅ ALL ISSUES RESOLVED' if all_pass else '❌ SOME ISSUES REMAIN'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
