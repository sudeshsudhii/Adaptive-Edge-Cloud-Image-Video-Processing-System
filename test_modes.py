"""Extended E2E tests: CLOUD and SPLIT modes."""

import io
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx
import numpy as np
import cv2

BASE = "http://127.0.0.1:8000"
TIMEOUT = 60.0


def create_test_image(width=640, height=480):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        img[y, :, 0] = int(255 * y / height)
        img[y, :, 2] = int(255 * (1 - y / height))
    cv2.circle(img, (width // 2, height // 2), 100, (0, 255, 0), 3)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_mode(mode):
    print(f"\n{'='*60}")
    print(f"TEST: Upload + Process ({mode})")

    img_data = create_test_image()
    files = {"file": ("test_image.png", io.BytesIO(img_data), "image/png")}
    r = httpx.post(f"{BASE}/upload", files=files, timeout=15)
    assert r.status_code == 200
    upload_data = r.json()
    print(f"  ✅ Uploaded: {upload_data['filename']}")

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
    task_id = r.json()["task_id"]
    print(f"  ✅ Task submitted: {task_id}")

    start = time.time()
    while time.time() - start < TIMEOUT:
        time.sleep(1)
        r = httpx.get(f"{BASE}/status/{task_id}", timeout=10)
        if r.status_code == 200:
            state = r.json()
            status = state["status"]
            print(f"  ⏳ Status: {status} | {state.get('progress_pct', 0)}% | {state.get('current_stage', '')}")
            if status == "COMPLETED":
                result = state.get("result", {})
                print(f"  ✅ COMPLETED in {result.get('processing_time_s', '?')}s")
                print(f"     Mode used: {result.get('mode_used', '?')}")
                print(f"     Output: {result.get('output_path', '?')}")
                print(f"     Stages: {result.get('stages_completed', [])}")
                return True
            elif status == "FAILED":
                print(f"  ❌ FAILED: {state.get('error', 'Unknown')}")
                return False

    print("  ❌ TIMEOUT")
    return False


results = {}
for mode in ["CLOUD", "SPLIT"]:
    try:
        results[mode] = test_mode(mode)
    except Exception as e:
        print(f"  ❌ {mode} FAILED: {e}")
        results[mode] = False

print(f"\n{'='*60}")
print("RESULTS:")
for m, ok in results.items():
    print(f"  {'✅' if ok else '❌'} {m}")
sys.exit(0 if all(results.values()) else 1)
