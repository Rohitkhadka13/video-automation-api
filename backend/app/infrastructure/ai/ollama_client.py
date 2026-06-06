# =============================================================================
# app/infrastructure/ai/ollama_client.py
# Async Ollama client for Llama 3 script generation.
# Uses the official ollama-python library with httpx under the hood.
# =============================================================================
from __future__ import annotations

import asyncio
from typing import AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import OllamaError
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SCRIPT_SYSTEM_PROMPT = settings.OLLAMA_SYSTEM_PROMPT

_SCRIPT_USER_TEMPLATE = """
You are given a video transcription. Your task is to rewrite it as a polished,
engaging video script. Keep the same information but improve clarity, flow, and
audience engagement. Return ONLY the script text, no headings or meta-commentary.

Original transcription:
{transcription}

Additional instructions from the creator:
{prompt}

Rewritten script:
"""

_SUMMARISE_TEMPLATE = """
Summarise the following video transcription in 2-3 sentences for use as a
video description. Be concise and capture the key message.

Transcription:
{transcription}

Summary:
"""


class OllamaClient:
    """
    Async client for Ollama local inference.

    All methods are async coroutines — call with `await` or from an async context.
    The client reuses a single httpx.AsyncClient across requests for connection pooling.
    """

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url
        self._model = settings.OLLAMA_MODEL
        self._timeout = settings.OLLAMA_TIMEOUT
        self._max_tokens = settings.OLLAMA_MAX_TOKENS
        self._temperature = settings.OLLAMA_TEMPERATURE
        self._keep_alive = settings.OLLAMA_KEEP_ALIVE

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(self._timeout),
                write=30.0,
                pool=5.0,
            ),
        )
        logger.info(
            "ollama.client.initialised",
            base_url=self._base_url,
            model=self._model,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate_script(
        self,
        *,
        prompt: str,
        transcription: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate an enhanced video script from a transcription.

        Args:
            prompt:        Additional creator instructions or original script prompt.
            transcription: Raw Whisper transcription text.
            system_prompt: Override the default system prompt.

        Returns:
            Generated script text.

        Raises:
            OllamaError: If the API returns an error or times out after retries.
        """
        user_message = _SCRIPT_USER_TEMPLATE.format(
            transcription=transcription[:8000],   # guard against token overflow
            prompt=prompt or "Improve the script for clarity and engagement.",
        )

        response_text = await self._chat(
            messages=[
                {"role": "system", "content": system_prompt or _SCRIPT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
        )
        logger.info(
            "ollama.generate_script.complete",
            input_chars=len(transcription),
            output_chars=len(response_text),
        )
        return response_text.strip()

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def summarise(self, transcription: str) -> str:
        """
        Generate a short video description from a transcription.

        Returns:
            2-3 sentence summary string.
        """
        user_message = _SUMMARISE_TEMPLATE.format(
            transcription=transcription[:6000]
        )
        response = await self._generate(prompt=user_message)
        return response.strip()

    async def stream_generate_script(
        self,
        *,
        prompt: str,
        transcription: str,
    ) -> AsyncIterator[str]:
        """
        Stream script generation token-by-token.

        Yields:
            Individual token strings as they arrive from the model.
        """
        user_message = _SCRIPT_USER_TEMPLATE.format(
            transcription=transcription[:8000],
            prompt=prompt or "Improve the script for clarity and engagement.",
        )
        async for token in self._stream_chat(
            messages=[
                {"role": "system", "content": _SCRIPT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
        ):
            yield token

    async def health_check(self) -> bool:
        """
        Return True if Ollama is reachable and the configured model is available.
        Used by the /health endpoint.
        """
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            if response.status_code != 200:
                return False
            tags = response.json()
            model_names = [m.get("name", "") for m in tags.get("models", [])]
            return any(self._model in name for name in model_names)
        except Exception as exc:
            logger.warning("ollama.health_check.failed", error=str(exc))
            return False

    async def close(self) -> None:
        """Close the underlying httpx client. Call on app shutdown."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _chat(self, messages: list[dict]) -> str:
        """POST /api/chat (non-streaming) and return the response text."""
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": self._max_tokens,
                        "temperature": self._temperature,
                    },
                    "keep_alive": self._keep_alive,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama API error {exc.response.status_code}: {exc.response.text[:500]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaError(
                f"Ollama request timed out after {self._timeout}s"
            ) from exc
        except Exception as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    async def _generate(self, prompt: str) -> str:
        """POST /api/generate (non-streaming) and return the response text."""
        try:
            response = await self._client.post(
                "/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": self._max_tokens,
                        "temperature": self._temperature,
                    },
                    "keep_alive": self._keep_alive,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama API error {exc.response.status_code}: {exc.response.text[:500]}"
            ) from exc
        except Exception as exc:
            raise OllamaError(f"Ollama generate failed: {exc}") from exc

    async def _stream_chat(
        self, messages: list[dict]
    ) -> AsyncIterator[str]:
        """POST /api/chat with stream=True, yielding token strings."""
        import json
        try:
            async with self._client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "num_predict": self._max_tokens,
                        "temperature": self._temperature,
                    },
                    "keep_alive": self._keep_alive,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if token := chunk.get("message", {}).get("content", ""):
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama stream error {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            raise OllamaError(f"Ollama stream failed: {exc}") from exc