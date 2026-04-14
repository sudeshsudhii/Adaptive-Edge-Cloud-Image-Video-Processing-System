# observability/metrics_collector.py
"""Prometheus-style in-process metrics collector."""

from __future__ import annotations

import json
import time
import threading
from typing import Dict, List

import psutil

from observability.logger import get_logger

logger = get_logger("metrics")


class MetricsCollector:
    """Thread-safe counters, gauges, and histograms with system snapshot."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

    # ── Counters ──────────────────────────────────────────
    def inc_counter(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    # ── Gauges ────────────────────────────────────────────
    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    # ── Histograms ────────────────────────────────────────
    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms.setdefault(name, []).append(value)

    # ── System snapshot ───────────────────────────────────
    @staticmethod
    def get_system_metrics() -> dict:
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": mem.percent,
            "ram_available_gb": round(mem.available / (1024 ** 3), 2),
        }

    # ── Export ────────────────────────────────────────────
    def export(self) -> dict:
        with self._lock:
            hist_summary = {}
            for k, v in self._histograms.items():
                hist_summary[k] = {
                    "count": len(v),
                    "sum": round(sum(v), 4),
                    "avg": round(sum(v) / len(v), 4) if v else 0,
                }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": hist_summary,
                "system": self.get_system_metrics(),
            }

    # ── Private ───────────────────────────────────────────
    @staticmethod
    def _make_key(name: str, labels: dict) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Module-level singleton
metrics = MetricsCollector()
