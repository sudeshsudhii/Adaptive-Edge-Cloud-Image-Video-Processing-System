# storage/__init__.py
"""Storage layer: local filesystem and cloud object storage."""

from storage.local_store import LocalStore
from storage.cloud_store import CloudStore

__all__ = ["LocalStore", "CloudStore"]
