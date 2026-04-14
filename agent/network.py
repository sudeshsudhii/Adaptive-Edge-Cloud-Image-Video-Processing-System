# agent/network.py
"""Network condition profiler — latency and bandwidth measurement."""

from __future__ import annotations

import socket
import time
from typing import Optional

from backend.models import NetworkProfile
from observability.logger import get_logger

logger = get_logger("network")

# Default endpoints for network measurement
_PING_HOST = "8.8.8.8"
_PING_PORT = 53
_PING_TIMEOUT = 2.0


class NetworkProfiler:
    """Measures network latency and estimates bandwidth."""

    def __init__(
        self,
        ping_host: str = _PING_HOST,
        ping_port: int = _PING_PORT,
        timeout: float = _PING_TIMEOUT,
    ) -> None:
        self.ping_host = ping_host
        self.ping_port = ping_port
        self.timeout = timeout

    def measure_latency(self, samples: int = 3) -> float:
        """
        Measure TCP-connect latency to ping_host:ping_port.
        Returns average latency in milliseconds.
        """
        times: list[float] = []
        for _ in range(samples):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                start = time.perf_counter()
                sock.connect((self.ping_host, self.ping_port))
                elapsed = (time.perf_counter() - start) * 1000  # ms
                sock.close()
                times.append(elapsed)
            except (socket.timeout, OSError):
                times.append(self.timeout * 1000)  # treat timeout as max
        avg = sum(times) / len(times) if times else self.timeout * 1000
        return round(avg, 2)

    def estimate_bandwidth(self) -> float:
        """
        Estimate download bandwidth in Mbps.
        Uses a lightweight heuristic based on latency (no large download).
        For accurate measurement, swap with an actual download test.
        """
        latency_ms = self.measure_latency(samples=1)
        # Heuristic: infer bandwidth class from latency
        if latency_ms < 10:
            bw = 100.0      # LAN / high-speed
        elif latency_ms < 30:
            bw = 50.0       # fast broadband
        elif latency_ms < 80:
            bw = 20.0       # broadband
        elif latency_ms < 200:
            bw = 5.0        # slow
        else:
            bw = 1.0        # very slow / cellular
        return bw

    def snapshot(self) -> NetworkProfile:
        latency = self.measure_latency()
        bandwidth = self.estimate_bandwidth()
        logger.info(f"Network: latency={latency}ms, bandwidth≈{bandwidth}Mbps")
        return NetworkProfile(latency_ms=latency, bandwidth_mbps=bandwidth)
