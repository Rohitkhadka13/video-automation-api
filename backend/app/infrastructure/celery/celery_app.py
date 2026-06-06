# =============================================================================
# app/infrastructure/celery/celery_app.py
# Celery application factory with Redis broker/backend.
# All task modules are auto-discovered via the `include` list.
# =============================================================================
from __future__ import annotations

from celery import Celery
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    worker_ready,
)
from kombu import Exchange, Queue

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_celery_app() -> Celery:
    """
    Build and configure the Celery application.

    Queue routing:
        default       — general tasks (email, cleanup, etc.)
        video         — full video processing pipeline (slow, CPU-bound)
        transcription — Whisper transcription (memory-bound, needs GPU or beefy CPU)
        tts           — Piper TTS synthesis (fast, subprocess)
    """
    app = Celery("ai_video_saas")

    # -------------------------------------------------------------------------
    # Broker & backend
    # -------------------------------------------------------------------------
    app.conf.broker_url = settings.CELERY_BROKER_URL
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND

    # -------------------------------------------------------------------------
    # Serialisation
    # -------------------------------------------------------------------------
    app.conf.task_serializer = settings.CELERY_TASK_SERIALIZER
    app.conf.result_serializer = settings.CELERY_RESULT_SERIALIZER
    app.conf.accept_content = settings.CELERY_ACCEPT_CONTENT

    # -------------------------------------------------------------------------
    # Task reliability
    # -------------------------------------------------------------------------
    app.conf.task_acks_late = settings.CELERY_TASK_ACKS_LATE
    app.conf.task_reject_on_worker_lost = settings.CELERY_TASK_REJECT_ON_WORKER_LOST
    app.conf.task_track_started = settings.CELERY_TASK_TRACK_STARTED
    app.conf.task_send_sent_event = settings.CELERY_TASK_SEND_SENT_EVENT
    app.conf.worker_prefetch_multiplier = settings.CELERY_WORKER_PREFETCH_MULTIPLIER

    # -------------------------------------------------------------------------
    # Retry defaults (overridable per-task)
    # -------------------------------------------------------------------------
    app.conf.task_max_retries = settings.CELERY_TASK_MAX_RETRIES

    # -------------------------------------------------------------------------
    # Result expiry — keep results for 24 hours (enough for polling)
    # -------------------------------------------------------------------------
    app.conf.result_expires = 86400  # 24 hours in seconds

    # -------------------------------------------------------------------------
    # Queue definitions with explicit exchange/routing-key bindings
    # -------------------------------------------------------------------------
    default_exchange = Exchange("default", type="direct")
    video_exchange = Exchange("video", type="direct")
    transcription_exchange = Exchange("transcription", type="direct")
    tts_exchange = Exchange("tts", type="direct")

    app.conf.task_queues = (
        Queue("default",       default_exchange,       routing_key="default"),
        Queue("video",         video_exchange,         routing_key="video"),
        Queue("transcription", transcription_exchange, routing_key="transcription"),
        Queue("tts",           tts_exchange,           routing_key="tts"),
    )
    app.conf.task_default_queue = settings.CELERY_TASK_DEFAULT_QUEUE
    app.conf.task_default_exchange = "default"
    app.conf.task_default_routing_key = "default"

    # -------------------------------------------------------------------------
    # Explicit task routing — task name → queue
    # -------------------------------------------------------------------------
    app.conf.task_routes = {
        "app.infrastructure.celery.tasks.video_tasks.*":         {"queue": "video"},
        "app.infrastructure.celery.tasks.transcription_tasks.*": {"queue": "transcription"},
        "app.infrastructure.celery.tasks.tts_tasks.*":           {"queue": "tts"},
    }

    # -------------------------------------------------------------------------
    # Auto-discover tasks
    # -------------------------------------------------------------------------
    app.autodiscover_tasks(
        [
            "app.infrastructure.celery.tasks.video_tasks",
            "app.infrastructure.celery.tasks.transcription_tasks",
            "app.infrastructure.celery.tasks.tts_tasks",
        ],
        force=True,
    )

    # -------------------------------------------------------------------------
    # Test mode — execute tasks synchronously without a broker
    # -------------------------------------------------------------------------
    app.conf.task_always_eager = settings.CELERY_TASK_ALWAYS_EAGER
    app.conf.task_eager_propagates = True  # re-raise exceptions in eager mode

    # -------------------------------------------------------------------------
    # Worker concurrency settings
    # -------------------------------------------------------------------------
    app.conf.worker_max_tasks_per_child = 100   # recycle workers to prevent memory leaks
    app.conf.worker_max_memory_per_child = 512000  # 512MB per worker process

    return app


# Module-level singleton
celery_app: Celery = create_celery_app()


# =============================================================================
# Signal handlers — bridge Celery events → structured logging
# =============================================================================

@worker_ready.connect
def on_worker_ready(sender: object, **kwargs: object) -> None:
    logger.info("celery.worker.ready", hostname=str(getattr(sender, "hostname", "unknown")))


@task_prerun.connect
def on_task_prerun(
    task_id: str,
    task: object,
    args: tuple,
    kwargs: dict,
    **extra: object,
) -> None:
    logger.info(
        "celery.task.started",
        task_id=task_id,
        task_name=getattr(task, "name", "unknown"),
    )


@task_postrun.connect
def on_task_postrun(
    task_id: str,
    task: object,
    args: tuple,
    kwargs: dict,
    retval: object,
    state: str,
    **extra: object,
) -> None:
    logger.info(
        "celery.task.finished",
        task_id=task_id,
        task_name=getattr(task, "name", "unknown"),
        state=state,
    )


@task_failure.connect
def on_task_failure(
    task_id: str,
    exception: Exception,
    traceback: object,
    einfo: object,
    **kwargs: object,
) -> None:
    logger.error(
        "celery.task.failed",
        task_id=task_id,
        error=str(exception),
        exc_type=type(exception).__name__,
    )


@task_retry.connect
def on_task_retry(
    request: object,
    reason: object,
    einfo: object,
    **kwargs: object,
) -> None:
    logger.warning(
        "celery.task.retry",
        task_id=getattr(request, "id", "unknown"),
        reason=str(reason),
    )