# backend/models.py
"""
Pydantic schema registry — single source of truth for ALL inter-module contracts.

External (API-facing):
    InputSchema, SystemProfile, NetworkProfile, BenchmarkOutput

Internal (inter-module):
    TaskPayload, ProcessingResult, CloudResponse, TaskState, DecisionResult

Auth:
    LoginRequest, TokenResponse
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════

class ExecutionMode(str, Enum):
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    SPLIT = "SPLIT"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


# ═══════════════════════════════════════════════════════════
#  EXTERNAL SCHEMAS (user-facing)
# ═══════════════════════════════════════════════════════════

class InputSchema(BaseModel):
    """Describes the uploaded file's characteristics."""
    file_type: FileType
    resolution: List[int] = Field(..., min_length=2, max_length=2,
                                  description="[width, height]")
    frames: int = Field(1, ge=1)
    size_mb: float = Field(..., gt=0)


class SystemProfile(BaseModel):
    """Snapshot of the local machine's capabilities."""
    cpu_cores: int
    cpu_freq: float             # GHz
    gpu_available: bool
    gpu_cores: int = 0
    gpu_vram_mb: int = 0        # for memory-safe batching
    ram_gb: float
    battery: int                # 0-100 or -1 (desktop)
    cpu_load: float             # 0.0 – 1.0


class NetworkProfile(BaseModel):
    """Current network conditions."""
    latency_ms: float
    bandwidth_mbps: float


class BenchmarkOutput(BaseModel):
    """Post-execution performance metrics."""
    mode: ExecutionMode
    latency: float              # seconds
    throughput: float           # items/sec
    cpu_usage: float            # 0.0 – 1.0
    gpu_usage: float            # 0.0 – 1.0
    cost_usd: float
    energy_j: float
    speedup: float              # local_est / actual


# ═══════════════════════════════════════════════════════════
#  INTERNAL CONTRACTS (inter-module)
# ═══════════════════════════════════════════════════════════

class TaskPayload(BaseModel):
    """Travels: Backend → Orchestrator → Processing."""
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    input_schema: InputSchema
    file_path: str
    system_profile: SystemProfile
    network_profile: NetworkProfile
    requested_mode: Optional[ExecutionMode] = None
    priority: int = Field(default=5, ge=1, le=10)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ProcessingResult(BaseModel):
    """Travels: Processing → Orchestrator → Backend."""
    task_id: str
    mode_used: ExecutionMode
    output_path: str
    processing_time_s: float
    stages_completed: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class CloudResponse(BaseModel):
    """Travels: Cloud Manager → Processing Engine."""
    provider: str               # "aws" | "simulated"
    instance_id: Optional[str] = None
    processing_time_s: float
    cost_usd: float
    output_path: Optional[str] = None


class TaskState(BaseModel):
    """Persisted in Redis — full lifecycle record."""
    task_id: str
    status: TaskStatus
    mode: Optional[ExecutionMode] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_pct: float = 0.0
    current_stage: Optional[str] = None
    result: Optional[ProcessingResult] = None
    benchmark: Optional[BenchmarkOutput] = None
    error: Optional[str] = None
    retry_count: int = 0


class DecisionResult(BaseModel):
    """Returned by Decision Engine."""
    mode: ExecutionMode
    system_score: float
    network_score: float
    complexity_score: float
    energy_estimate_j: float
    reasoning: str
    confidence: float           # 0.0 – 1.0


# ═══════════════════════════════════════════════════════════
#  AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# ═══════════════════════════════════════════════════════════
#  API RESPONSE WRAPPERS
# ═══════════════════════════════════════════════════════════

class ProcessingResponse(BaseModel):
    """Returned immediately after submission (202 Accepted)."""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    message: str = "Task submitted successfully"


class ErrorResponse(BaseModel):
    detail: str
