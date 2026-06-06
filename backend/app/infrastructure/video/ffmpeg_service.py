# =============================================================================
# app/infrastructure/video/ffmpeg_service.py
# FFmpeg service — async wrappers for video/audio processing operations.
# All subprocess calls are non-blocking via asyncio.create_subprocess_exec.
# =============================================================================
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import FFmpegError
from app.core.logging import get_logger

logger = get_logger(__name__)

_FFMPEG = settings.FFMPEG_EXECUTABLE
_FFPROBE = settings.FFPROBE_EXECUTABLE


class FFmpegService:
    """
    Provides async wrappers for common FFmpeg operations used in the pipeline:
      - probe:         Read video/audio metadata (duration, resolution, fps).
      - merge_audio:   Replace a video's audio track with a new audio file.
      - extract_audio: Pull the audio stream from a video to a WAV file.
      - generate_thumbnail: Extract a single frame as a JPEG image.
      - transcode:     Re-encode a video with configurable quality settings.
    """

    # ------------------------------------------------------------------
    # Probe — metadata extraction via ffprobe
    # ------------------------------------------------------------------

    async def probe(self, input_path: str | Path) -> dict:
        """
        Extract media metadata using ffprobe.

        Returns:
            dict with keys: duration, width, height, fps, codec_name,
                            audio_codec, bit_rate, size_bytes.

        Raises:
            FFmpegError: If ffprobe fails or the file is unreadable.
        """
        cmd = [
            _FFPROBE,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        ]

        stdout, _ = await self._run(cmd, timeout=30)

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise FFmpegError(
                command=" ".join(cmd),
                returncode=0,
                stderr=f"ffprobe JSON parse error: {exc}",
            ) from exc

        result: dict = {}
        fmt = data.get("format", {})
        result["duration"] = float(fmt.get("duration", 0) or 0)
        result["size_bytes"] = int(fmt.get("size", 0) or 0)
        result["bit_rate"] = int(fmt.get("bit_rate", 0) or 0)
        result["format_name"] = fmt.get("format_name", "")

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                result["width"] = int(stream.get("width", 0) or 0)
                result["height"] = int(stream.get("height", 0) or 0)
                result["codec_name"] = stream.get("codec_name", "")
                # Parse frame rate — stored as "30000/1001" or "30/1"
                r_frame_rate = stream.get("r_frame_rate", "0/1")
                try:
                    num, den = r_frame_rate.split("/")
                    result["fps"] = round(int(num) / max(int(den), 1), 3)
                except (ValueError, ZeroDivisionError):
                    result["fps"] = 0.0
            elif stream.get("codec_type") == "audio":
                result["audio_codec"] = stream.get("codec_name", "")
                result["audio_sample_rate"] = int(stream.get("sample_rate", 0) or 0)
                result["audio_channels"] = int(stream.get("channels", 0) or 0)

        return result

    # ------------------------------------------------------------------
    # Merge audio — replace video audio track
    # ------------------------------------------------------------------

    async def merge_audio(
        self,
        *,
        video_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path | None = None,
    ) -> tuple[str, dict]:
        """
        Replace a video's audio track with a new audio file.

        The output video is re-encoded with H.264 + AAC.
        If the audio is shorter than the video, it is looped.
        If longer, it is trimmed to the video duration.

        Args:
            video_path:  Source video file.
            audio_path:  Replacement audio file (WAV, MP3, AAC, etc.)
            output_path: Destination path. Defaults to a temp file.

        Returns:
            Tuple of (output_path_str, probe_metadata_dict).

        Raises:
            FFmpegError: If FFmpeg fails.
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.close()
            output_path = tmp.name

        video_probe = await self.probe(video_path)
        duration = video_probe.get("duration", 0)

        cmd = [
            _FFMPEG, "-y",
            "-i", str(video_path),          # input 0: video
            "-i", str(audio_path),          # input 1: new audio
            "-c:v", settings.FFMPEG_VIDEO_CODEC,
            "-preset", settings.FFMPEG_PRESET,
            "-crf", str(settings.FFMPEG_DEFAULT_CRF),
            "-c:a", settings.FFMPEG_AUDIO_CODEC,
            "-b:a", "192k",
            "-map", "0:v:0",               # take video from input 0
            "-map", "1:a:0",               # take audio from input 1
            "-shortest",                   # trim to shortest stream
            "-movflags", "+faststart",     # moov atom at front for web streaming
            "-threads", str(settings.FFMPEG_THREADS),
            str(output_path),
        ]

        if duration > 0:
            cmd = [_FFMPEG, "-y", "-i", str(video_path), "-i", str(audio_path),
                   "-c:v", settings.FFMPEG_VIDEO_CODEC,
                   "-preset", settings.FFMPEG_PRESET,
                   "-crf", str(settings.FFMPEG_DEFAULT_CRF),
                   "-c:a", settings.FFMPEG_AUDIO_CODEC, "-b:a", "192k",
                   "-map", "0:v:0", "-map", "1:a:0",
                   "-t", str(duration),
                   "-movflags", "+faststart",
                   "-threads", str(settings.FFMPEG_THREADS),
                   str(output_path)]

        timeout = max(120, int(duration * 3) if duration else 600)
        await self._run(cmd, timeout=timeout)

        out_probe = await self.probe(output_path)
        logger.info(
            "ffmpeg.merge_audio.complete",
            duration=out_probe.get("duration"),
            resolution=f"{out_probe.get('width')}x{out_probe.get('height')}",
        )
        return str(output_path), out_probe

    # ------------------------------------------------------------------
    # Extract audio
    # ------------------------------------------------------------------

    async def extract_audio(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        sample_rate: int = 16000,   # Whisper expects 16kHz
        channels: int = 1,          # mono
    ) -> str:
        """
        Extract and convert the audio stream from a video to WAV.

        Args:
            input_path:  Source video or audio file.
            output_path: Destination WAV path. Defaults to temp file.
            sample_rate: Output sample rate in Hz (default 16000 for Whisper).
            channels:    Number of audio channels (default 1 = mono).

        Returns:
            Path to the output WAV file.
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            output_path = tmp.name

        probe = await self.probe(input_path)
        duration = probe.get("duration", 0)

        cmd = [
            _FFMPEG, "-y",
            "-i", str(input_path),
            "-vn",                          # no video output
            "-acodec", "pcm_s16le",         # signed 16-bit PCM WAV
            "-ar", str(sample_rate),
            "-ac", str(channels),
            str(output_path),
        ]

        timeout = max(60, int(duration * 2) if duration else 300)
        await self._run(cmd, timeout=timeout)
        return str(output_path)

    # ------------------------------------------------------------------
    # Thumbnail generation
    # ------------------------------------------------------------------

    async def generate_thumbnail(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        at_second: int | None = None,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """
        Extract a single frame from a video as a JPEG thumbnail.

        Args:
            input_path:  Source video file.
            output_path: Destination JPEG path. Defaults to temp file.
            at_second:   Timestamp to extract from (default: FFMPEG_THUMBNAIL_SECOND).
            width/height: Output dimensions (preserves aspect ratio with scale).

        Returns:
            Path to the output JPEG file.
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.close()
            output_path = tmp.name

        seek = at_second if at_second is not None else settings.FFMPEG_THUMBNAIL_SECOND

        cmd = [
            _FFMPEG, "-y",
            "-ss", str(seek),
            "-i", str(input_path),
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-q:v", "2",                    # JPEG quality (2=best, 31=worst)
            str(output_path),
        ]

        await self._run(cmd, timeout=30)
        return str(output_path)

    # ------------------------------------------------------------------
    # Transcode
    # ------------------------------------------------------------------

    async def transcode(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        crf: int | None = None,
        preset: str | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> tuple[str, dict]:
        """
        Transcode a video with configurable codec and quality settings.

        Returns:
            Tuple of (output_path, probe_dict).
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.close()
            output_path = tmp.name

        probe = await self.probe(input_path)
        duration = probe.get("duration", 0)

        vf_filter = "null"
        if max_width or max_height:
            w = max_width or -2
            h = max_height or -2
            vf_filter = f"scale='min({w},iw)':'min({h},ih)':force_original_aspect_ratio=decrease"

        cmd = [
            _FFMPEG, "-y",
            "-i", str(input_path),
            "-c:v", video_codec or settings.FFMPEG_VIDEO_CODEC,
            "-preset", preset or settings.FFMPEG_PRESET,
            "-crf", str(crf if crf is not None else settings.FFMPEG_DEFAULT_CRF),
            "-c:a", audio_codec or settings.FFMPEG_AUDIO_CODEC,
            "-b:a", "192k",
            "-vf", vf_filter,
            "-movflags", "+faststart",
            "-threads", str(settings.FFMPEG_THREADS),
            str(output_path),
        ]

        timeout = max(120, int(duration * 4) if duration else 600)
        await self._run(cmd, timeout=timeout)

        out_probe = await self.probe(output_path)
        return str(output_path), out_probe

    # ------------------------------------------------------------------
    # Private helper — run subprocess
    # ------------------------------------------------------------------

    async def _run(
        self,
        cmd: list[str],
        *,
        timeout: int = 300,
    ) -> tuple[str, str]:
        """
        Run an FFmpeg/ffprobe command asynchronously.

        Returns:
            Tuple of (stdout, stderr) as strings.

        Raises:
            FFmpegError: If the process exits with a non-zero return code.
        """
        cmd_str = " ".join(cmd)
        logger.debug("ffmpeg.run", cmd=cmd_str[:200])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout)
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise FFmpegError(
                    command=cmd_str,
                    returncode=-1,
                    stderr=f"Process timed out after {timeout}s",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                raise FFmpegError(
                    command=cmd_str,
                    returncode=proc.returncode,
                    stderr=stderr,
                )

            return stdout, stderr

        except FFmpegError:
            raise
        except Exception as exc:
            raise FFmpegError(
                command=cmd_str,
                returncode=-1,
                stderr=str(exc),
            ) from exc