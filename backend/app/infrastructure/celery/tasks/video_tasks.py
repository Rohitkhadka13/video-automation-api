# =============================================================================
# app/infrastructure/celery/tasks/video_tasks.py
# Full video processing pipeline task.
# Orchestrates: transcription → script generation → TTS → FFmpeg merge.
# =============================================================================
from __future__ import annotations

import asyncio
import traceback
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger

from app.infrastructure.celery.celery_app import celery_app

logger = get_task_logger(__name__)


class VideoProcessingTask(Task):
    """
    Custom Task base class that holds lazy-initialised service singletons.
    Services are created once per worker process, not per task invocation.
    This avoids re-loading Whisper models for every task.
    """

    abstract = True
    _whisper = None
    _ollama = None
    _piper = None
    _ffmpeg = None

    @property
    def whisper(self):  # noqa: ANN201
        if self._whisper is None:
            from app.infrastructure.ai.whisper_client import WhisperClient
            self._whisper = WhisperClient()
        return self._whisper

    @property
    def ollama(self):  # noqa: ANN201
        if self._ollama is None:
            from app.infrastructure.ai.ollama_client import OllamaClient
            self._ollama = OllamaClient()
        return self._ollama

    @property
    def piper(self):  # noqa: ANN201
        if self._piper is None:
            from app.infrastructure.ai.piper_client import PiperClient
            self._piper = PiperClient()
        return self._piper

    @property
    def ffmpeg(self):  # noqa: ANN201
        if self._ffmpeg is None:
            from app.infrastructure.video.ffmpeg_service import FFmpegService
            self._ffmpeg = FFmpegService()
        return self._ffmpeg


@celery_app.task(
    bind=True,
    base=VideoProcessingTask,
    name="app.infrastructure.celery.tasks.video_tasks.process_video",
    queue="video",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=3600,   # 1 hour soft limit → raises SoftTimeLimitExceeded
    time_limit=3660,        # 1 hour + 60s hard kill
)
def process_video(self: VideoProcessingTask, video_id: str, task_id: str) -> dict:
    """
    Full AI video processing pipeline.

    Steps:
        1. Mark task as started in DB.
        2. Download source file from storage.
        3. Whisper: transcribe audio.
        4. Ollama: generate enhanced script from transcription.
        5. Piper: synthesise new audio from script.
        6. FFmpeg: merge original video with new audio + create thumbnail.
        7. Upload output to storage.
        8. Mark video as COMPLETED.

    Uses asyncio.run() because all infrastructure clients are async.
    Celery workers run in a synchronous context by default.
    """
    return asyncio.run(_process_video_async(self, video_id, task_id))


async def _process_video_async(
    task: VideoProcessingTask, video_id: str, task_id: str
) -> dict:
    """Async implementation of the video processing pipeline."""
    from app.core.exceptions import ProcessingError
    from app.db.session import get_db_context
    from app.infrastructure.repositories.sqlalchemy_video_repository import (
        SQLAlchemyVideoRepository,
    )
    from app.infrastructure.repositories.sqlalchemy_task_repository import (
        SQLAlchemyTaskRepository,
    )
    from app.infrastructure.storage.file_storage import FileStorage
    from backend.app.model.models_video import VideoStatus

    vid_uuid = UUID(video_id)
    task_uuid = UUID(task_id)

    async with get_db_context() as db:
        video_repo = SQLAlchemyVideoRepository(db)
        task_repo = SQLAlchemyTaskRepository(db)
        storage = FileStorage()

        async def update_progress(pct: float, msg: str) -> None:
            await task_repo.update_status(
                task_uuid, "started", progress=pct, progress_message=msg
            )
            await task_repo.append_log(task_uuid, msg)
            logger.info(f"[{video_id}] {msg} ({pct*100:.0f}%)")

        try:
            # ----------------------------------------------------------------
            # Step 1: Mark started
            # ----------------------------------------------------------------
            await task_repo.mark_started(task_uuid)
            await video_repo.update_status(vid_uuid, VideoStatus.PROCESSING)
            await update_progress(0.05, "Pipeline started")

            video = await video_repo.get_by_id(vid_uuid)
            if video is None:
                raise ProcessingError(f"Video {video_id} not found")

            if not video.storage_key:
                raise ProcessingError("Video has no uploaded source file")

            # ----------------------------------------------------------------
            # Step 2: Download source file
            # ----------------------------------------------------------------
            await update_progress(0.10, "Downloading source file")
            local_source = await storage.download_to_temp(video.storage_key)

            # ----------------------------------------------------------------
            # Step 3: Transcription
            # ----------------------------------------------------------------
            await update_progress(0.20, "Transcribing audio with Whisper")
            transcription = await task.whisper.transcribe(
                local_source,
                language=video.language if video.language != "auto" else None,
            )
            await video_repo.update_processing_metadata(
                vid_uuid, {"transcription": transcription}
            )
            await update_progress(0.40, f"Transcription complete — {len(transcription.get('text',''))} chars")

            # ----------------------------------------------------------------
            # Step 4: Script generation with Ollama
            # ----------------------------------------------------------------
            await update_progress(0.45, "Generating enhanced script with Ollama")
            script_prompt = video.script_prompt or transcription.get("text", "")
            generated_script = await task.ollama.generate_script(
                prompt=script_prompt,
                transcription=transcription.get("text", ""),
            )
            await video_repo.update_processing_metadata(
                vid_uuid, {"script": {"text": generated_script}}
            )
            await update_progress(0.60, "Script generation complete")

            # ----------------------------------------------------------------
            # Step 5: TTS synthesis
            # ----------------------------------------------------------------
            await update_progress(0.65, "Synthesising voiceover with Piper TTS")
            audio_path = await task.piper.synthesise(
                text=generated_script,
                voice_model=video.voice_model,
            )
            await update_progress(0.75, "Voiceover synthesis complete")

            # ----------------------------------------------------------------
            # Step 6: FFmpeg — replace audio + generate thumbnail
            # ----------------------------------------------------------------
            await update_progress(0.80, "Merging video with new audio via FFmpeg")
            output_path, probe_data = await task.ffmpeg.merge_audio(
                video_path=local_source,
                audio_path=audio_path,
            )
            thumbnail_path = await task.ffmpeg.generate_thumbnail(output_path)
            await update_progress(0.90, "FFmpeg processing complete")

            # ----------------------------------------------------------------
            # Step 7: Upload outputs to storage
            # ----------------------------------------------------------------
            await update_progress(0.93, "Uploading processed video")
            output_key = await storage.upload_from_path(
                output_path,
                prefix=f"processed/{video_id}",
            )
            thumbnail_key = await storage.upload_from_path(
                thumbnail_path,
                prefix=f"thumbnails/{video_id}",
            )

            # ----------------------------------------------------------------
            # Step 8: Finalise
            # ----------------------------------------------------------------
            await video_repo.update_output(
                vid_uuid,
                output_storage_key=output_key,
                thumbnail_storage_key=thumbnail_key,
                duration_seconds=probe_data.get("duration"),
                width=probe_data.get("width"),
                height=probe_data.get("height"),
                fps=probe_data.get("fps"),
            )
            await video_repo.update_status(vid_uuid, VideoStatus.COMPLETED)

            result = {
                "output_key": output_key,
                "thumbnail_key": thumbnail_key,
                "duration": probe_data.get("duration"),
                "resolution": f"{probe_data.get('width')}x{probe_data.get('height')}",
            }
            await task_repo.mark_success(task_uuid, result_data=result)
            await update_progress(1.0, "Processing complete ✓")

            logger.info(f"process_video.completed video_id={video_id}")
            return result

        except Exception as exc:
            tb = traceback.format_exc()
            error_type = type(exc).__name__
            error_msg = str(exc)

            logger.error(
                f"process_video.failed video_id={video_id} "
                f"error_type={error_type} error={error_msg}"
            )

            await video_repo.update_status(
                vid_uuid, VideoStatus.FAILED, error_message=error_msg
            )
            await task_repo.mark_failure(
                task_uuid,
                error_type=error_type,
                error_message=error_msg,
                traceback=tb if not task.request.retries else None,
            )

            # Retry with exponential backoff
            raise task.retry(
                exc=exc,
                countdown=60 * (2 ** task.request.retries),
            ) from exc


@celery_app.task(
    bind=True,
    name="app.infrastructure.celery.tasks.video_tasks.generate_thumbnail",
    queue="video",
    max_retries=2,
)
def generate_thumbnail(self: VideoProcessingTask, video_id: str, task_id: str) -> dict:
    """Standalone thumbnail generation task (re-run without full pipeline)."""
    return asyncio.run(_generate_thumbnail_async(self, video_id, task_id))


async def _generate_thumbnail_async(
    task: VideoProcessingTask, video_id: str, task_id: str
) -> dict:
    from app.db.session import get_db_context
    from app.infrastructure.repositories.sqlalchemy_video_repository import SQLAlchemyVideoRepository
    from app.infrastructure.storage.file_storage import FileStorage

    async with get_db_context() as db:
        video_repo = SQLAlchemyVideoRepository(db)
        storage = FileStorage()
        vid_uuid = UUID(video_id)

        video = await video_repo.get_by_id(vid_uuid)
        if video is None or not video.output_storage_key:
            raise ValueError(f"Video {video_id} has no output to thumbnail")

        local_path = await storage.download_to_temp(video.output_storage_key)
        thumb_path = await task.ffmpeg.generate_thumbnail(local_path)
        thumb_key = await storage.upload_from_path(
            thumb_path, prefix=f"thumbnails/{video_id}"
        )
        await video_repo.update(
            vid_uuid, {"thumbnail_storage_key": thumb_key}
        )
        return {"thumbnail_key": thumb_key}