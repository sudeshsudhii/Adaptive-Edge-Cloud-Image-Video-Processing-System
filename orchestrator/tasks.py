# orchestrator/tasks.py
"""
Celery task definitions.

Celery owns the task lifecycle (queue → retry → timeout → state).
Processing / Ray / Cloud are called INSIDE each task — no duplicate scheduling.
"""

from __future__ import annotations

import traceback

from celery import Celery

from backend.config import settings
from backend.models import (
    ExecutionMode,
    ProcessingResult,
    TaskPayload,
    TaskStatus,
)
from observability.logger import get_logger

logger = get_logger("celery_tasks")

# ═══════════════════════════════════════════════════════════
#  CELERY APP
# ═══════════════════════════════════════════════════════════

app = Celery(
    "edgecloud",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3600,
)


# ═══════════════════════════════════════════════════════════
#  MAIN PROCESSING TASK
# ═══════════════════════════════════════════════════════════

@app.task(
    bind=True,
    name="edgecloud.process",
    max_retries=3,
    default_retry_delay=5,
    soft_time_limit=300,
    time_limit=360,
    acks_late=True,
)
def process_task(self, payload_dict: dict) -> dict:
    """
    Master Celery task: decide → process → benchmark → store result.

    Retries up to 3× with exponential backoff.
    On 3rd cloud failure, falls back to LOCAL.
    """
    from orchestrator.state_manager import TaskStateManager
    from decision.engine import DecisionEngine
    from processing.engine import ProcessingEngine
    from benchmark.engine import BenchmarkEngine

    state_mgr = TaskStateManager()
    decision_engine = DecisionEngine()
    processing_engine = ProcessingEngine()
    benchmark_engine = BenchmarkEngine()

    payload = TaskPayload.model_validate(payload_dict)
    task_id = payload.task_id
    mode = None

    try:
        # ── PENDING → RUNNING ──
        state_mgr.transition(task_id, TaskStatus.RUNNING)

        # ── Decision ──
        decision = decision_engine.decide(
            system=payload.system_profile,
            network=payload.network_profile,
            input_schema=payload.input_schema,
        )
        mode = payload.requested_mode or decision.mode
        state_mgr.transition(
            task_id, TaskStatus.FAILED  # will not execute — see below
        ) if False else None  # placeholder for readability

        # Update state with mode
        state_mgr.update_progress(task_id, 10.0, "decision_complete")

        logger.info(
            f"[{task_id}] Decision: {mode.value} — {decision.reasoning}"
        )

        # ── Processing ──
        result: ProcessingResult = processing_engine.execute(
            mode=mode,
            payload=payload,
            progress_callback=lambda pct, stage: state_mgr.update_progress(
                task_id, pct, stage
            ),
        )

        if result.error:
            raise RuntimeError(result.error)

        # ── Benchmark ──
        benchmark = benchmark_engine.collect(
            task_id=task_id,
            mode=mode,
            processing_result=result,
            system_profile=payload.system_profile,
        )

        # ── RUNNING → COMPLETED ──
        state_mgr.transition(
            task_id,
            TaskStatus.COMPLETED,
            mode=mode,
            result=result,
            benchmark=benchmark,
        )
        logger.info(f"[{task_id}] COMPLETED in {result.processing_time_s:.2f}s")
        return result.model_dump()

    except Exception as exc:
        logger.error(f"[{task_id}] FAILED: {exc}\n{traceback.format_exc()}")

        # ── Fallback: after 3 cloud failures, try LOCAL ──
        if (
            mode in (ExecutionMode.CLOUD, ExecutionMode.SPLIT)
            and self.request.retries >= 2
        ):
            logger.warning(f"[{task_id}] Cloud failed 3×, falling back to LOCAL")
            try:
                result = processing_engine.execute(
                    mode=ExecutionMode.LOCAL,
                    payload=payload,
                    progress_callback=lambda pct, stage: state_mgr.update_progress(
                        task_id, pct, stage
                    ),
                )
                if not result.error:
                    benchmark = benchmark_engine.collect(
                        task_id=task_id,
                        mode=ExecutionMode.LOCAL,
                        processing_result=result,
                        system_profile=payload.system_profile,
                    )
                    state_mgr.transition(
                        task_id,
                        TaskStatus.COMPLETED,
                        mode=ExecutionMode.LOCAL,
                        result=result,
                        benchmark=benchmark,
                    )
                    return result.model_dump()
            except Exception as fb_exc:
                logger.error(f"[{task_id}] LOCAL fallback also failed: {fb_exc}")

        # Mark as FAILED
        try:
            state_mgr.transition(
                task_id,
                TaskStatus.FAILED,
                error=str(exc),
                retry_count=self.request.retries,
            )
        except Exception:
            pass

        raise self.retry(exc=exc)
