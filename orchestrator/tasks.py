"""Celery task definitions and local execution helper."""

from __future__ import annotations

import traceback

from celery import Celery

from backend.config import settings
from backend.models import ExecutionMode, ProcessingResult, TaskPayload, TaskStatus
from observability.logger import get_logger

logger = get_logger("celery_tasks")

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


# ── Singleton caches for task engines (created once, reused) ──
_singleton_state_mgr = None
_singleton_decision = None
_singleton_processing = None
_singleton_benchmark = None


def _get_state_mgr(cls):
    global _singleton_state_mgr
    if _singleton_state_mgr is None:
        _singleton_state_mgr = cls()
    return _singleton_state_mgr


def _get_decision_engine(cls):
    global _singleton_decision
    if _singleton_decision is None:
        _singleton_decision = cls()
    return _singleton_decision


def _get_processing_engine(cls):
    global _singleton_processing
    if _singleton_processing is None:
        _singleton_processing = cls()
    return _singleton_processing


def _get_benchmark_engine(cls):
    global _singleton_benchmark
    if _singleton_benchmark is None:
        _singleton_benchmark = cls()
    return _singleton_benchmark


def run_processing_task(payload_dict: dict, retry_count: int = 0) -> dict:
    """Run one processing attempt, with optional cloud-to-local fallback."""
    from benchmark.engine import BenchmarkEngine
    from decision.engine import DecisionEngine
    from orchestrator.state_manager import TaskStateManager
    from processing.engine import ProcessingEngine

    # Use cached singletons to avoid re-init overhead per task
    state_mgr = _get_state_mgr(TaskStateManager)
    decision_engine = _get_decision_engine(DecisionEngine)
    processing_engine = _get_processing_engine(ProcessingEngine)
    benchmark_engine = _get_benchmark_engine(BenchmarkEngine)

    payload = TaskPayload.model_validate(payload_dict)
    task_id = payload.task_id
    mode = None

    try:
        state_mgr.transition(task_id, TaskStatus.RUNNING)

        decision = decision_engine.decide(
            system=payload.system_profile,
            network=payload.network_profile,
            input_schema=payload.input_schema,
        )
        mode = payload.requested_mode or decision.mode
        state_mgr.update_progress(task_id, 10.0, "decision_complete")

        logger.info(f"[{task_id}] Decision: {mode.value} - {decision.reasoning}")

        result: ProcessingResult = processing_engine.execute(
            mode=mode,
            payload=payload,
            progress_callback=lambda pct, stage: state_mgr.update_progress(
                task_id, pct, stage
            ),
        )

        if result.error:
            raise RuntimeError(result.error)

        benchmark = benchmark_engine.collect(
            task_id=task_id,
            mode=mode,
            processing_result=result,
            system_profile=payload.system_profile,
        )

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

        if mode in (ExecutionMode.CLOUD, ExecutionMode.SPLIT) and retry_count >= 2:
            logger.warning(f"[{task_id}] Cloud failed 3x, falling back to LOCAL")
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
            except Exception as fallback_exc:
                logger.error(
                    f"[{task_id}] LOCAL fallback also failed: {fallback_exc}"
                )

        try:
            state_mgr.transition(
                task_id,
                TaskStatus.FAILED,
                error=str(exc),
                retry_count=retry_count,
            )
        except Exception:
            pass

        raise


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
    """Queue-backed processing task."""
    try:
        return run_processing_task(payload_dict, retry_count=self.request.retries)
    except Exception as exc:
        raise self.retry(exc=exc)
