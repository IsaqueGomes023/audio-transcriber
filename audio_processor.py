"""
audio_processor.py
------------------
Valida e prepara arquivos de áudio para envio à API Groq.

Como a Groq aceita os formatos mais comuns diretamente (MP3, M4A, OGG,
WAV, FLAC), não é necessário converter o áudio — apenas validar o formato
e o tamanho antes de enviar.

Formatos aceitos pela Groq: MP3, M4A, MP4, OGG, WAV, FLAC, WebM
Tamanho máximo: 25 MB
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Formatos suportados pela Groq Whisper API
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".ogg", ".wav", ".flac", ".webm", ".mpeg", ".mpga"}
SUPPORTED_DISPLAY    = "MP3, M4A, MP4, OGG, WAV, FLAC, WebM"
MAX_FILE_SIZE_MB     = 1024


def validate_audio_file(filename: str, file_bytes: bytes) -> dict:
    """
    Valida formato e tamanho do arquivo de áudio.

    Args:
        filename:   Nome do arquivo (ex: "audio.mp3").
        file_bytes: Conteúdo do arquivo em bytes.

    Returns:
        Dicionário com informações do arquivo:
          - filename:     Nome original.
          - extension:    Extensão detectada.
          - size_mb:      Tamanho em MB.
          - is_valid:     True se o arquivo passou na validação.
          - error:        Mensagem de erro, ou None.

    Raises:
        ValueError: Se o formato ou tamanho forem inválidos.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    ext     = Path(filename).suffix.lower()

    info = {
        "filename":  filename,
        "extension": ext,
        "size_mb":   round(size_mb, 2),
        "is_valid":  True,
        "error":     None,
    }

    # Verifica formato
    if ext not in SUPPORTED_EXTENSIONS:
        info["is_valid"] = False
        info["error"]    = (
            f"Formato '{ext}' não suportado.\n"
            f"Formatos aceitos: {SUPPORTED_DISPLAY}"
        )
        raise ValueError(info["error"])

    # Verifica tamanho
    if size_mb > MAX_FILE_SIZE_MB:
        info["is_valid"] = False
        info["error"]    = (
            f"Arquivo muito grande: {size_mb:.1f} MB.\n"
            f"Limite máximo suportado: {MAX_FILE_SIZE_MB} MB."
        )
        raise ValueError(info["error"])

    logger.info(f"Arquivo válido: {filename} ({size_mb:.1f} MB, {ext})")
    return info
