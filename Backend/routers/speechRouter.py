"""
HTTP bridge to NVIDIA Riva (local gRPC). Requires ``nvidia-riva-client`` + a running Riva server.
"""

from __future__ import annotations

import asyncio
import logging

try:
    import grpc
except ImportError:  # pragma: no cover - riva client normally pulls grpc in
    grpc = None

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from utility.riva_speech_bridge import (
    riva_installed,
    riva_missing_message,
    synthesize_http_wav,
    transcribe_wav_pcm,
)

router = APIRouter()
_log = logging.getLogger(__name__)


def _http_and_detail_for_riva_error(operation: str, exc: BaseException) -> tuple[int, str]:
    """Map gRPC failures to clearer HTTP statuses (UNAVAILABLE usually means no server on host:port)."""
    if grpc is not None and isinstance(exc, grpc.RpcError):  # type: ignore[name-defined]
        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            uri_hint = (
                "Start the NVIDIA Riva speech server so gRPC listens on RIVA_SPEECH_URI "
                "(default localhost:50051 - see Backend/unified.env.example), or fix the URI / Docker port mapping. "
                f"gRPC UNAVAILABLE details: {exc.details()}"
            )
            return 503, uri_hint
        return 502, f"Riva {operation} failed: {exc.code().name}: {exc.details()}"
    return 502, f"Riva {operation} failed (is Riva running at RIVA_SPEECH_URI?). {exc!s}"


class SynthesizeBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


@router.get("/speech/riva/health")
async def riva_speech_health():
    """Return whether the Riva Python client is importable (not whether the server is up)."""
    return {"riva_client_installed": riva_installed(), "detail": riva_missing_message() or None}


@router.post("/speech/transcribe")
async def speech_transcribe(file: UploadFile = File(..., description="16-bit PCM WAV from browser mic")):
    if not riva_installed():
        raise HTTPException(status_code=501, detail=riva_missing_message())
    if not file.filename and not file.content_type:
        pass
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    def _run() -> str:
        return transcribe_wav_pcm(raw)

    try:
        text = await asyncio.to_thread(_run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        _log.exception("Riva ASR failed")
        code, detail = _http_and_detail_for_riva_error("ASR", e)
        raise HTTPException(status_code=code, detail=detail) from e

    return {"text": text}


@router.post("/speech/synthesize")
async def speech_synthesize(body: SynthesizeBody):
    if not riva_installed():
        raise HTTPException(status_code=501, detail=riva_missing_message())

    def _run() -> bytes:
        return synthesize_http_wav(body.text)

    try:
        wav = await asyncio.to_thread(_run)
    except Exception as e:  # noqa: BLE001
        _log.exception("Riva TTS failed")
        code, detail = _http_and_detail_for_riva_error("TTS", e)
        raise HTTPException(status_code=code, detail=detail) from e

    return Response(content=wav, media_type="audio/wav")
