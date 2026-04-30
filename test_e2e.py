"""
End-to-end test script for the Adaptive Edge-Cloud Processing System.
Tests: upload → process → poll status → verify output.
"""

import io
import os
import sys
import time

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx
import numpy as np
import cv2

BASE = "http://127.0.0.1:8000"
TIMEOUT = 60.0


def create_test_image(width=640, height=480):
    """Generate a synthetic test image with gradients and shapes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Gradient background
    for y in range(height):
        img[y, :, 0] = int(255 * y / height)
        img[y, :, 2] = int(255 * (1 - y / height))
    # Draw shapes
    cv2.circle(img, (width // 2, height // 2), 100, (0, 255, 0), 3)
    cv2.rectangle(img, (50, 50), (200, 200), (255, 255, 0), 2)
    cv2.putText(img, "EdgeCloud Test", (150, 400),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_health():
    print("=" * 60)
    print("TEST 1: Health Check")
    r = httpx.get(f"{BASE}/health", timeout=10)
    assert r.status_code == 200, f"Health failed: {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    print(f"  ✅ Health OK: {data}")
    return True


def test_system_profile():
    print("=" * 60)
    print("TEST 2: System Profile")
    r = httpx.get(f"{BASE}/system/profile", timeout=10)
    assert r.status_code == 200, f"Profile failed: {r.status_code}"
    data = r.json()
    print(f"  ✅ Profile: {data['cpu_cores']}C, GPU={data['gpu_available']}, "
          f"RAM={data['ram_gb']}GB, Battery={data['battery']}%")
    return True


def test_network_profile():
    print("=" * 60)
    print("TEST 3: Network Profile")
    r = httpx.get(f"{BASE}/system/network", timeout=15)
    assert r.status_code == 200, f"Network failed: {r.status_code}"
    data = r.json()
    print(f"  ✅ Network: latency={data['latency_ms']}ms, "
          f"bandwidth={data['bandwidth_mbps']}Mbps")
    return True


def test_upload_and_process(mode="LOCAL"):
    print("=" * 60)
    print(f"TEST 4: Upload + Process ({mode})")
    
    # Step 1: Upload
    img_data = create_test_image()
    files = {"file": ("test_image.png", io.BytesIO(img_data), "image/png")}
    r = httpx.post(f"{BASE}/upload", files=files, timeout=15)
    assert r.status_code == 200, f"Upload failed: {r.status_code} — {r.text}"
    upload_data = r.json()
    file_path = upload_data["file_path"]
    print(f"  ✅ Uploaded: {upload_data['filename']} ({upload_data['size_mb']} MB)")

    # Step 2: Process
    payload = {
        "file_type": upload_data["file_type"],
        "resolution": upload_data["resolution"],
        "frames": upload_data["frames"],
        "size_mb": upload_data["size_mb"],
    }
    r = httpx.post(
        f"{BASE}/process",
        json=payload,
        params={"file_path": file_path, "mode": mode},
        timeout=30,
    )
    assert r.status_code == 202, f"Process failed: {r.status_code} — {r.text}"
    proc_data = r.json()
    task_id = proc_data["task_id"]
    print(f"  ✅ Task submitted: {task_id}")

    # Step 3: Poll status until COMPLETED or FAILED
    start = time.time()
    final_status = None
    while time.time() - start < TIMEOUT:
        time.sleep(2)
        r = httpx.get(f"{BASE}/status/{task_id}", timeout=10)
        if r.status_code == 200:
            state = r.json()
            status = state["status"]
            progress = state.get("progress_pct", 0)
            stage = state.get("current_stage", "")
            print(f"  ⏳ Status: {status} | Progress: {progress}% | Stage: {stage}")
            if status in ("COMPLETED", "FAILED"):
                final_status = state
                break
        else:
            print(f"  ⚠️ Status poll returned {r.status_code}")

    if final_status is None:
        print("  ❌ TIMEOUT waiting for task completion")
        return False

    if final_status["status"] == "COMPLETED":
        result = final_status.get("result", {})
        benchmark = final_status.get("benchmark", {})
        print(f"  ✅ COMPLETED in {result.get('processing_time_s', '?')}s")
        print(f"     Mode: {result.get('mode_used', '?')}")
        print(f"     Output: {result.get('output_path', '?')}")
        print(f"     Stages: {result.get('stages_completed', [])}")
        if benchmark:
            print(f"     Benchmark: latency={benchmark.get('latency', '?')}s, "
                  f"speedup={benchmark.get('speedup', '?')}x")
        return True
    else:
        print(f"  ❌ FAILED: {final_status.get('error', 'Unknown error')}")
        return False


def test_metrics():
    print("=" * 60)
    print("TEST 5: Metrics Endpoint")
    r = httpx.get(f"{BASE}/metrics", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  ✅ Counters: {len(data.get('counters', {}))} entries")
    print(f"  ✅ System CPU: {data.get('system', {}).get('cpu_percent', '?')}%")
    return True


def test_benchmarks():
    print("=" * 60)
    print("TEST 6: Benchmark Endpoint")
    r = httpx.get(f"{BASE}/benchmark", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  ✅ Benchmark summary: {data}")
    return True


def main():
    print("\n🚀 Edge-Cloud Processing System — End-to-End Test Suite")
    print("=" * 60)
    
    results = {}
    
    for name, fn in [
        ("Health", test_health),
        ("System Profile", test_system_profile),
        ("Network Profile", test_network_profile),
        ("Upload & Process (LOCAL)", lambda: test_upload_and_process("LOCAL")),
        ("Metrics", test_metrics),
        ("Benchmarks", test_benchmarks),
    ]:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {passed}/{total} tests passed")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
