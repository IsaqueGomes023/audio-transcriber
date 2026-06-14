"""
transcriber.py
--------------
Transcrição de áudio via Groq API (whisper-large-v3-turbo).
Suporta arquivos de até 200 MB via chunking automático.
"""

import io
import os
import logging
from typing import Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_AUDIO_MODELS = {
    "whisper-large-v3-turbo":     "Whisper Large v3 Turbo ⚡ (Rápido — Recomendado)",
    "whisper-large-v3":           "Whisper Large v3 🎯 (Máxima precisão — Mais lento)",
    "distil-whisper-large-v3-en": "Distil-Whisper English 🇺🇸 (Somente inglês, ultra-rápido)",
}

SUPPORTED_FORMATS = {
    ".mp3":  "audio/mpeg",
    ".m4a":  "audio/mp4",
    ".mp4":  "audio/mp4",
    ".ogg":  "audio/ogg",
    ".wav":  "audio/wav",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
}

CHUNK_THRESHOLD_MB  = 25    # Acima disso, usa chunking automático
CHUNK_DURATION_SEC  = 600   # Cada chunk = 10 minutos de áudio


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY não encontrada!\n"
            "1. Acesse https://console.groq.com/keys\n"
            "2. Crie uma conta gratuita e gere uma API Key\n"
            "3. Adicione no arquivo .env: GROQ_API_KEY=gsk_..."
        )
    return Groq(api_key=api_key)


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _get_duration_ffprobe(audio_bytes: bytes, ext: str) -> float:
    """Obtém duração do áudio em segundos via ffprobe."""
    import subprocess, tempfile, os, json
    suffix = ext if ext.startswith(".") else f".{ext}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        path = tmp.name
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", path],
            capture_output=True, timeout=30,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _convert_to_mp3_ffmpeg(audio_bytes: bytes, ext: str) -> bytes:
    """Converte áudio para MP3 usando ffmpeg via subprocess (sem pydub)."""
    import subprocess
    import tempfile
    import os

    suffix_in = ext if ext.startswith(".") else f".{ext}"
    with tempfile.NamedTemporaryFile(suffix=suffix_in, delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        path_in = tmp_in.name

    path_out = path_in.rsplit(".", 1)[0] + ".mp3"

    try:
        result = subprocess.run(
            ["ffmpeg", "-i", path_in, "-q:a", "4", "-y", path_out],
            capture_output=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="ignore"))
        with open(path_out, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(path_in):
            os.unlink(path_in)
        if os.path.exists(path_out):
            os.unlink(path_out)


def _transcribe_bytes(
    client: Groq,
    audio_bytes: bytes,
    filename: str,
    model: str,
    language: Optional[str],
    offset_seconds: float = 0.0,
) -> dict:
    """Transcreve um único chunk de áudio (deve ser < 25 MB)."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # M4A e MP4 causam rejeição de MIME type na Groq — converte para MP3 via ffmpeg
    send_bytes = audio_bytes
    send_ext   = ext
    if ext in (".m4a", ".mp4"):
        try:
            send_bytes = _convert_to_mp3_ffmpeg(audio_bytes, ext)
            send_ext   = ".mp3"
            logger.info("M4A convertido para MP3 via ffmpeg.")
        except Exception as e:
            logger.warning(f"Conversão M4A→MP3 falhou ({e}). Tentando envio direto.")

    mime        = SUPPORTED_FORMATS.get(send_ext, "audio/mpeg")
    safe_name   = "audio" + send_ext   # nome limpo, sem espaços ou caracteres especiais

    params = {
        "file":                    (safe_name, send_bytes, mime),
        "model":                   model,
        "response_format":         "verbose_json",
        "timestamp_granularities": ["segment"],
    }
    if language and language != "auto":
        params["language"] = language

    result = client.audio.transcriptions.create(**params)

    segments = []
    for seg in (getattr(result, "segments", []) or []):
        segments.append({
            "id":    getattr(seg, "id",    0),
            "start": _format_timestamp(getattr(seg, "start", 0) + offset_seconds),
            "end":   _format_timestamp(getattr(seg, "end",   0) + offset_seconds),
            "text":  getattr(seg, "text",  "").strip(),
        })

    duration = 0.0
    raw_segs = getattr(result, "segments", []) or []
    if raw_segs:
        duration = getattr(raw_segs[-1], "end", 0)

    return {
        "text":     result.text.strip(),
        "segments": segments,
        "language": getattr(result, "language", language or "desconhecido"),
        "duration": duration + offset_seconds,
        "model":    model,
    }


def _chunk_and_transcribe(
    audio_bytes: bytes,
    filename: str,
    model: str,
    language: Optional[str],
) -> dict:
    """Divide áudio em chunks de 10 min via ffmpeg e transcreve cada um."""
    import subprocess
    import tempfile
    import os

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".mp3"

    # Duração total via ffprobe
    duration_total = _get_duration_ffprobe(audio_bytes, ext)
    if duration_total == 0:
        raise ValueError(
            "Não foi possível determinar a duração do áudio.\n"
            "Certifique-se de que o FFmpeg está instalado e no PATH."
        )

    # Grava input em arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        path_in = tmp_in.name

    client = _get_client()
    all_texts     = []
    all_segments  = []
    detected_lang = language or "desconhecido"

    try:
        start     = 0.0
        chunk_idx = 1
        while start < duration_total:
            path_out = path_in.rsplit(".", 1)[0] + f"_chunk{chunk_idx}.mp3"
            try:
                result = subprocess.run(
                    ["ffmpeg", "-i", path_in,
                     "-ss", str(start),
                     "-t",  str(CHUNK_DURATION_SEC),
                     "-q:a", "4", "-y", path_out],
                    capture_output=True, timeout=300,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.decode(errors="ignore"))

                with open(path_out, "rb") as f:
                    chunk_bytes = f.read()

                logger.info(f"Chunk {chunk_idx}: {len(chunk_bytes)/1024/1024:.1f} MB")
                r = _transcribe_bytes(client, chunk_bytes, f"chunk_{chunk_idx:03d}.mp3",
                                      model, language, start)
                all_texts.append(r["text"])
                all_segments.extend(r["segments"])
                detected_lang = r["language"]
            finally:
                if os.path.exists(path_out):
                    os.unlink(path_out)

            start += CHUNK_DURATION_SEC
            chunk_idx += 1
    finally:
        if os.path.exists(path_in):
            os.unlink(path_in)

    return {
        "text":     " ".join(all_texts),
        "segments": all_segments,
        "language": detected_lang,
        "duration": duration_total,
        "model":    model,
    }


def transcribe(
    audio_bytes: bytes,
    filename: str,
    model: str = "whisper-large-v3-turbo",
    language: Optional[str] = None,
) -> dict:
    """
    Transcreve áudio. Usa chunking automático (via ffmpeg) para arquivos > 25 MB.

    Returns:
        dict com: text, segments, language, duration, model
    """
    size_mb = len(audio_bytes) / (1024 * 1024)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext and ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Formato '{ext}' não suportado.\n"
            f"Formatos aceitos: {', '.join(SUPPORTED_FORMATS.keys())}"
        )

    if size_mb > CHUNK_THRESHOLD_MB:
        logger.info(f"Arquivo grande ({size_mb:.1f} MB) — usando chunking automático.")
        return _chunk_and_transcribe(audio_bytes, filename, model, language)

    client = _get_client()
    result = _transcribe_bytes(client, audio_bytes, filename, model, language)

    # Se duração não veio da API (turbo model), busca via ffprobe
    if result["duration"] == 0:
        result["duration"] = _get_duration_ffprobe(audio_bytes, ext)

    return result


def transcribe_with_segments_text(result: dict) -> str:
    segments = result.get("segments", [])

    # Se todos os timestamps são 00:00:00 (modelo não retornou tempos), exibe só o texto
    has_real_timestamps = any(
        seg.get("start", "00:00:00") != "00:00:00" or seg.get("end", "00:00:00") != "00:00:00"
        for seg in segments
    )

    if not has_real_timestamps:
        return "[00:00:00 → 00:00:00]"

    lines = []
    for seg in segments:
        lines.append(f"[{seg['start']} → {seg['end']}] {seg['text']}")
    return "\n".join(lines) if lines else result.get("text", "")
