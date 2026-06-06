# =============================================================================
# app/infrastructure/ai/whisper_client.py
# faster-whisper transcription client.
# faster-whisper uses CTranslate2 under the hood — 4x faster than openai-whisper
# with the same accuracy, at ~1/4 the VRAM on GPU or int8 on CPU.
# =============================================================================
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import WhisperError
from app.core.logging import get_logger

logger = get_logger(__name__)


class WhisperClient:
    """
    Wrapper around faster-whisper's WhisperModel.

    The model is loaded once on first use and kept in memory for the
    lifetime of the worker process (lazy-loaded singleton pattern via
    the VideoProcessingTask.whisper property).

    All transcription is run in a thread pool executor to avoid blocking
    the asyncio event loop — faster-whisper is CPU-bound synchronous code.
    """

    def __init__(self) -> None:
        self._model_name = settings.WHISPER_MODEL
        self._device = settings.WHISPER_DEVICE
        self._compute_type = settings.WHISPER_COMPUTE_TYPE
        self._beam_size = settings.WHISPER_BEAM_SIZE
        self._vad_filter = settings.WHISPER_VAD_FILTER
        self._model: Any = None   # WhisperModel — loaded on first use

        logger.info(
            "whisper.client.initialised",
            model=self._model_name,
            device=self._device,
            compute_type=self._compute_type,
        )

    def _load_model(self) -> Any:
        """Load the WhisperModel synchronously (called once per worker)."""
        try:
            from faster_whisper import WhisperModel  # type: ignore[import]
        except ImportError as exc:
            raise WhisperError(
                "faster-whisper is not installed. "
                "Install it in the worker image: pip install faster-whisper"
            ) from exc

        logger.info("whisper.model.loading", model=self._model_name)
        model = WhisperModel(
            self._model_name,
            device=self._device,
            compute_type=self._compute_type,
            # Download to the shared models volume, not /tmp
            download_root=str(Path(settings.MEDIA_ROOT).parent / "models" / "whisper"),
        )
        logger.info("whisper.model.loaded", model=self._model_name)
        return model

    @property
    def model(self) -> Any:
        """Return the loaded WhisperModel, loading it on first access."""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        task: str = "transcribe",   # "transcribe" or "translate"
        word_timestamps: bool = False,
    ) -> dict:
        """
        Transcribe an audio/video file.

        Runs in a thread pool executor to avoid blocking the event loop.

        Args:
            audio_path:       Local path to the audio or video file.
            language:         ISO language code (e.g. "en", "es") or None for auto-detect.
            task:             "transcribe" or "translate" (translate → English).
            word_timestamps:  If True, include per-word timestamps in segments.

        Returns:
            dict with keys:
                text:     Full concatenated transcript.
                language: Detected or specified language code.
                segments: List of segment dicts with start/end/text.
                duration: Audio duration in seconds.

        Raises:
            WhisperError: If transcription fails.
        """
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._transcribe_sync(
                str(audio_path),
                language=language,
                task=task,
                word_timestamps=word_timestamps,
            ),
        )
        return result

    def _transcribe_sync(
        self,
        audio_path: str,
        *,
        language: str | None,
        task: str,
        word_timestamps: bool,
    ) -> dict:
        """Synchronous transcription — called from thread pool."""
        try:
            logger.info(
                "whisper.transcribe.start",
                path=audio_path,
                language=language or "auto",
            )

            segments_iter, info = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                beam_size=self._beam_size,
                vad_filter=self._vad_filter,
                vad_parameters={
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 400,
                },
                word_timestamps=word_timestamps,
            )

            segments: list[dict] = []
            full_text_parts: list[str] = []

            for seg in segments_iter:
                segment_dict: dict = {
                    "id": seg.id,
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                    "avg_logprob": round(seg.avg_logprob, 4),
                    "no_speech_prob": round(seg.no_speech_prob, 4),
                }
                if word_timestamps and seg.words:
                    segment_dict["words"] = [
                        {
                            "word": w.word,
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "probability": round(w.probability, 4),
                        }
                        for w in seg.words
                    ]
                segments.append(segment_dict)
                full_text_parts.append(seg.text.strip())

            full_text = " ".join(full_text_parts)

            logger.info(
                "whisper.transcribe.complete",
                language=info.language,
                duration=round(info.duration, 2),
                segment_count=len(segments),
                text_length=len(full_text),
            )

            return {
                "text": full_text,
                "language": info.language,
                "language_probability": round(info.language_probability, 4),
                "duration": round(info.duration, 3),
                "segments": segments,
            }

        except Exception as exc:
            logger.error(
                "whisper.transcribe.failed",
                path=audio_path,
                error=str(exc),
            )
            raise WhisperError(f"Transcription failed: {exc}") from exc

    async def detect_language(self, audio_path: str | Path) -> tuple[str, float]:
        """
        Detect the spoken language from the first 30 seconds of audio.

        Returns:
            Tuple of (language_code, probability), e.g. ("en", 0.98).
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._detect_language_sync(str(audio_path)),
        )

    def _detect_language_sync(self, audio_path: str) -> tuple[str, float]:
        try:
            _, info = self.model.transcribe(audio_path, language=None, max_new_tokens=1)
            return info.language, info.language_probability
        except Exception as exc:
            raise WhisperError(f"Language detection failed: {exc}") from exc