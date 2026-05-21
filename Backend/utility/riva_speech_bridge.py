"""
Call a local (or remote) NVIDIA Riva server over gRPC for ASR / TTS.

Requires: ``pip install nvidia-riva-client`` (see ``Backend/requirements-riva-speech.txt``).
Run Riva yourself (e.g. Docker quickstart) - no cloud usage for self-hosted speech.
"""

from __future__ import annotations

import io
import logging
import os
import wave
from typing import TYPE_CHECKING

_log = logging.getLogger(__name__)

try:
    import riva.client.proto.riva_asr_pb2 as rasr
    from riva.client import ASRService, Auth, SpeechSynthesisService
    from riva.client.proto.riva_audio_pb2 import AudioEncoding

    _RIVA_IMPORT_OK = True
except ImportError as _e:  # pragma: no cover
    _RIVA_IMPORT_ERROR = str(_e)
    _RIVA_IMPORT_OK = False


def riva_installed() -> bool:
    return _RIVA_IMPORT_OK


def riva_missing_message() -> str:
    if _RIVA_IMPORT_OK:
        return ""
    return (
        "nvidia-riva-client not installed or failed to import. "
        "Run: pip install -r requirements-riva-speech.txt (from Backend folder). "
        f"Original error: {_RIVA_IMPORT_ERROR!r}"
    )


def _clean(v: str | None, default: str = "") -> str:
    if v is None:
        return default
    s = str(v).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


def _auth() -> "Auth":
    if not _RIVA_IMPORT_OK:
        raise RuntimeError(riva_missing_message())
    uri = _clean(os.getenv("RIVA_SPEECH_URI"), "localhost:50051")
    use_ssl = _clean(os.getenv("RIVA_SPEECH_SSL"), "").lower() in ("1", "true", "yes")
    ssl_root = _clean(os.getenv("RIVA_SPEECH_SSL_ROOT_CERT")) or None
    metadata_args_raw = _clean(os.getenv("RIVA_SPEECH_METADATA_JSON"))  # unused by default for local riva

    kwargs: dict = dict(
        uri=uri,
        use_ssl=use_ssl,
        ssl_root_cert=ssl_root,
    )
    if metadata_args_raw:
        _log.warning("RIVA_SPEECH_METADATA_JSON parsing not implemented; ignoring")

    return Auth(**kwargs)


def _pcm_mono_from_wav(wav_bytes: bytes) -> tuple[bytes, int, int]:
    """Return interleaved PCM s16le, sample rate, channels."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError("Only 16-bit PCM WAV is supported for Riva offline ASR.")
        sr = wf.getframerate()
        ch = wf.getnchannels()
        pcm = wf.readframes(wf.getnframes())
    return pcm, sr, ch


def transcribe_wav_pcm(wav_file_bytes: bytes) -> str:
    """
    WAV (16-bit PCM) -> transcript using Riva offline Recognize.
    """
    if not _RIVA_IMPORT_OK:
        raise RuntimeError(riva_missing_message())

    pcm, sr, ch = _pcm_mono_from_wav(wav_file_bytes)
    model = _clean(os.getenv("RIVA_ASR_MODEL"))
    lang = _clean(os.getenv("RIVA_ASR_LANGUAGE"), "en-US")

    config = rasr.RecognitionConfig(
        encoding=AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=sr,
        audio_channel_count=ch,
        language_code=lang,
        enable_automatic_punctuation=True,
        max_alternatives=1,
    )
    if model:
        config.model = model

    auth = _auth()
    asr = ASRService(auth)
    resp = asr.offline_recognize(pcm, config)
    parts: list[str] = []
    for result in resp.results:
        if result.alternatives:
            parts.append(result.alternatives[0].transcript.strip())
    return " ".join(p for p in parts if p).strip()


def _linear_pcm_bytes_to_wav(pcm_bytes: bytes, sample_rate_hz: int, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate_hz)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def synthesize_http_wav(text: str) -> bytes:
    """Text -> WAV (16-bit PCM) bytes for browsers via ``<audio src=URL />``."""
    if not _RIVA_IMPORT_OK:
        raise RuntimeError(riva_missing_message())

    t = text.strip()
    if not t:
        raise ValueError("Empty text")

    lang = _clean(os.getenv("RIVA_TTS_LANGUAGE"), "en-US")
    voice = _clean(os.getenv("RIVA_TTS_VOICE")) or None
    sr = int(_clean(os.getenv("RIVA_TTS_SAMPLE_RATE_HZ"), "24000"))

    auth = _auth()
    tts = SpeechSynthesisService(auth)
    resp = tts.synthesize(
        text=t,
        voice_name=voice,
        language_code=lang,
        encoding=AudioEncoding.LINEAR_PCM,
        sample_rate_hz=sr,
    )
    pcm = bytes(resp.audio)
    return _linear_pcm_bytes_to_wav(pcm, sr, channels=1)
