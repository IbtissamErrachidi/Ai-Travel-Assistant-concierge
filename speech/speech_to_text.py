"""
Module Audio : Faster-Whisper (VAD Silero intégré) + décodage audio manuel via PyAV
+ Normalisation des codes de vol.

Le décodage est fait ici (et non par faster-whisper) pour ne pas dépendre de la
compatibilité entre les versions de faster-whisper et de PyAV.
"""

import logging
import os
import re

import av
import numpy as np
from faster_whisper import WhisperModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SpeechToText")


class AudioConfig:
    SAMPLE_RATE = 16000


class WhisperConfig:
    MODEL_SIZE = "small"
    DEVICE = "cpu"
    COMPUTE_TYPE = "int8"
    BEAM_SIZE = 5
    MIN_AUDIO_DURATION_S = 0.5


_WHISPER_MODEL = None


def _get_whisper_model() -> WhisperModel:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        logger.info(f"Chargement de Whisper '{WhisperConfig.MODEL_SIZE}'...")
        _WHISPER_MODEL = WhisperModel(
            WhisperConfig.MODEL_SIZE,
            device=WhisperConfig.DEVICE,
            compute_type=WhisperConfig.COMPUTE_TYPE,
        )
        logger.info("Whisper prêt.")
    return _WHISPER_MODEL


def _decode_audio(file_path: str, sample_rate: int = AudioConfig.SAMPLE_RATE) -> np.ndarray:
    """Décode webm/ogg/wav... en float32 mono 16 kHz avec PyAV."""
    container = av.open(file_path)
    chunks = []
    try:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        # Vide le buffer interne du resampler
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))
    finally:
        container.close()

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def normalize_flight_codes(text: str) -> str:
    """Normalise les codes de vol mal transcrits à l'oral (ex: 'A H 1 2 3 5' ou 'AH-1235' -> 'AH1235')."""
    if not text:
        return text

    word_to_digit = {
        "zéro": "0", "one": "1", "un": "1", "two": "2", "deux": "2",
        "three": "3", "trois": "3", "four": "4", "quatre": "4",
        "five": "5", "cinq": "5", "six": "6", "seven": "7", "sept": "7",
        "eight": "8", "huit": "8", "nine": "9", "neuf": "9",
    }

    normalized = text
    for word, digit in word_to_digit.items():
        normalized = re.sub(
            rf'\b([A-Za-z])\s+{word}\b',
            lambda m, d=digit: m.group(1) + d,
            normalized,
            flags=re.IGNORECASE,
        )

    def clean_spaced_code(match):
        return match.group(0).replace(" ", "").upper()

    pattern = r'\b[A-Za-z](?:\s+[A-Za-z])+\s+(?:\d\s*)+\b'
    normalized = re.sub(pattern, clean_spaced_code, normalized)
    
    # --- AJOUT : Suppression du tiret dans les codes de vol (ex: AH-1235 -> AH1235) ---
    normalized = re.sub(r'\b([A-Za-z]{2})\s*-\s*(\d+)\b', r'\1\2', normalized)
    
    return re.sub(r'\s+', ' ', normalized).strip()


def transcribe_audio_file(file_path: str) -> str:
    """
    Traite un fichier audio du navigateur (.webm) : décodage PyAV puis Whisper (VAD intégré).

    Retourne "" uniquement s'il n'y a réellement aucune parole.
    Toute erreur technique est propagée (raise) pour que l'API puisse répondre en 500.
    """
    if not file_path or not os.path.exists(file_path):
        logger.warning("Fichier audio introuvable.")
        return ""

    whisper_model = _get_whisper_model()

    try:
        audio = _decode_audio(file_path)
        duration = len(audio) / AudioConfig.SAMPLE_RATE
        logger.info(f"Audio décodé: {duration:.2f}s")

        if duration < WhisperConfig.MIN_AUDIO_DURATION_S:
            logger.info("Audio trop court, ignoré.")
            return ""

        segments, info = whisper_model.transcribe(
            audio,  # tableau numpy 16 kHz mono (et non un chemin de fichier)
            language=None,  # Détection automatique (Français, Arabe, Anglais...)
            beam_size=WhisperConfig.BEAM_SIZE,
            vad_filter=True,  # VAD Silero intégré à faster-whisper
            vad_parameters=dict(
                threshold=0.3,
                min_speech_duration_ms=250,
            ),
        )

        raw_text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info(f"Langue détectée: {info.language} ({info.language_probability:.2f})")
        logger.info(f"Transcription brute: '{raw_text}'")

        final_text = normalize_flight_codes(raw_text)
        logger.info(f"Transcription finale: '{final_text}'")
        return final_text

    except Exception as e:
        logger.error(f"Erreur lors de la transcription Whisper : {e}")
        raise