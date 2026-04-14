# processing/__init__.py
"""Processing engine: local CPU, GPU, distributed (Ray), and split pipeline."""

from processing.engine import ProcessingEngine

__all__ = ["ProcessingEngine"]
