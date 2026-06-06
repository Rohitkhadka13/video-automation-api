# =============================================================================
# app/infrastructure/ai/piper_client.py
# Piper TTS client — runs piper as a subprocess, reads WAV output.
# Piper is a local, fast, high-quality neural TTS engine from Rhasspy.
# Models are ONNX files downloaded separately and mounted at PIPER_MODELS_DIR.
# =============================================================================
from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import PiperError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Characters per second estimate — used to set a reasonable process timeout
_CHARS_PER_SECOND_ESTIMATE = 15
_MIN_TIMEOUT_SECONDS = 30
_MAX_TIMEOUT_SECONDS = 300


class PiperClient:
    """
    Async wrapper around the Piper TTS command-line binary.

    Piper reads text from stdin and writes a WAV file to a path specified
    with --output_file. We use asyncio.create_subprocess_exec for
    non-blocking subprocess management.

    Voice models must be downloaded separately and placed in PIPER_MODELS_DIR.
    Model files come in pairs: <model>.onnx and <model>.onnx.json.
    """

    def __init__(self) -> None:
        self._executable = settings.PIPER_EXECUTABLE
        self._models_dir = Path(settings.PIPER_MODELS_DIR)
        self._default_model = settings.PIPER_DEFAULT_MODEL
        self._sample_rate = settings.PIPER_SAMPLE_RATE

        self._verify_executable()
        logger.info(
            "piper.client.initialised",
            executable=self._executable,
            models_dir=str(self._models_dir),
            default_model=self._default_model,
        )

    @property
    def default_model(self) -> str:
        return self._default_model

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def synthesise(
        self,
        *,
        text: str,
        voice_model: str | None = None,
        output_path: str | Path | None = None,
    ) -> str:
        """
        Synthesise text to speech and save as a WAV file.

        Args:
            text:         Script text to synthesise.
            voice_model:  Piper model name (e.g. "en_US-lessac-medium").
                          Falls back to PIPER_DEFAULT_MODEL.
            output_path:  Destination path for the WAV file.
                          If None, a temp file is created (caller must delete).

        Returns:
            Absolute path to the output WAV file.

        Raises:
            PiperError: If piper exits with non-zero or times out.
        """
        model = voice_model or self._default_model
        model_path = self._resolve_model_path(model)

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                dir=tempfile.gettempdir(),
            )
            tmp.close()
            out_path = tmp.name
        else:
            out_path = str(output_path)

        # Dynamic timeout — proportional to text length
        char_count = len(text)
        timeout = max(
            _MIN_TIMEOUT_SECONDS,
            min(_MAX_TIMEOUT_SECONDS, char_count // _CHARS_PER_SECOND_ESTIMATE + 30),
        )

        logger.info(
            "piper.synthesise.start",
            model=model,
            text_length=char_count,
            timeout=timeout,
        )

        cmd = [
            self._executable,
            "--model", str(model_path),
            "--output_file", out_path,
            "--sentence_silence", "0.3",    # 300ms pause between sentences
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=text.encode("utf-8")),
                timeout=float(timeout),
            )

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace")[:1000]
                raise PiperError(
                    f"Piper exited with code {proc.returncode}: {err_msg}"
                )

            output = Path(out_path)
            if not output.exists() or output.stat().st_size == 0:
                raise PiperError(
                    f"Piper produced no output file at {out_path}"
                )

            logger.info(
                "piper.synthesise.complete",
                model=model,
                output_path=out_path,
                output_size_kb=output.stat().st_size // 1024,
            )
            return out_path

        except asyncio.TimeoutError as exc:
            # Kill the piper subprocess if it hung
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
            raise PiperError(
                f"Piper timed out after {timeout}s for {char_count} chars"
            ) from exc

        except PiperError:
            raise

        except Exception as exc:
            raise PiperError(f"Piper synthesis failed: {exc}") from exc

    async def list_available_models(self) -> list[dict]:
        """
        Return a list of available voice models from the models directory.

        Returns:
            List of dicts: [{name, path, language, quality}]
        """
        models = []
        if not self._models_dir.exists():
            return models

        for onnx_file in self._models_dir.glob("*.onnx"):
            config_file = onnx_file.with_suffix(".onnx.json")
            model_info: dict = {
                "name": onnx_file.stem,
                "path": str(onnx_file),
                "has_config": config_file.exists(),
            }
            if config_file.exists():
                try:
                    import json
                    config = json.loads(config_file.read_text())
                    model_info["language"] = config.get("language", {}).get("code", "unknown")
                    model_info["quality"] = config.get("audio", {}).get("quality", "unknown")
                    model_info["speaker_count"] = len(config.get("speaker_id_map", {})) or 1
                except Exception:
                    pass
            models.append(model_info)

        return sorted(models, key=lambda m: m["name"])

    async def health_check(self) -> bool:
        """Return True if the piper binary is accessible and executable."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._executable, "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return proc.returncode in (0, 1)  # piper --help may return 1
        except Exception as exc:
            logger.warning("piper.health_check.failed", error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _verify_executable(self) -> None:
        """Warn if the piper binary is not found (non-fatal at init time)."""
        if not shutil.which(self._executable) and not Path(self._executable).exists():
            logger.warning(
                "piper.executable.not_found",
                executable=self._executable,
                hint="Piper TTS will fail at runtime. "
                     "Ensure it is installed in the Docker image.",
            )

    def _resolve_model_path(self, model_name: str) -> Path:
        """
        Resolve a model name to its .onnx file path.

        Looks in PIPER_MODELS_DIR for <model_name>.onnx.
        Falls back gracefully with a clear error message.

        Raises:
            PiperError: If the model file is not found.
        """
        # Try exact name first
        exact = self._models_dir / f"{model_name}.onnx"
        if exact.exists():
            return exact

        # Try without quality suffix (e.g. "en_US-lessac" → "en_US-lessac-medium")
        for onnx in self._models_dir.glob(f"{model_name}*.onnx"):
            return onnx

        raise PiperError(
            f"Piper model '{model_name}' not found in {self._models_dir}. "
            f"Download it from https://huggingface.co/rhasspy/piper-voices "
            f"and place both .onnx and .onnx.json files in {self._models_dir}."
        )