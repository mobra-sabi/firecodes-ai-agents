#!/usr/bin/env python3
"""
🎤 Speech-to-Text Service
Folosește Whisper local pentru recunoaștere vocală
"""

import os
import tempfile
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Whisper model path
WHISPER_MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", "/opt/models/whisper-base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ro")


class STTService:
    """Serviciu pentru Speech-to-Text folosind Whisper"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
    
    def _load_model(self):
        """Încarcă modelul Whisper"""
        if self.model_loaded:
            return
        
        try:
            import whisper
            
            # Încearcă să încarce modelul
            if os.path.exists(WHISPER_MODEL_PATH):
                self.model = whisper.load_model(WHISPER_MODEL_PATH)
            else:
                # Folosește modelul default (base)
                self.model = whisper.load_model("base")
            
            self.model_loaded = True
            logger.info("✅ Whisper model loaded")
        except ImportError:
            logger.warning("⚠️ Whisper not installed. Install with: pip install openai-whisper")
            self.model = None
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            self.model = None
    
    def transcribe(self, audio_file_path: str) -> Optional[str]:
        """
        Transcrie audio în text
        
        Args:
            audio_file_path: Path către fișierul audio
        
        Returns:
            Textul transcis sau None dacă eșuează
        """
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
        
        self._load_model()
        
        if not self.model:
            logger.error("Whisper model not available")
            return None
        
        try:
            # Transcrie audio
            result = self.model.transcribe(
                audio_file_path,
                language=WHISPER_LANGUAGE
            )
            
            text = result.get("text", "").strip()
            logger.info(f"Transcribed audio: {text[:50]}...")
            
            return text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    def transcribe_bytes(self, audio_bytes: bytes, format: str = "wav") -> Optional[str]:
        """
        Transcrie audio din bytes
        
        Args:
            audio_bytes: Bytes audio
            format: Format audio (wav, mp3, etc.)
        
        Returns:
            Textul transcis sau None
        """
        try:
            # Salvează temporar
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            # Transcrie
            text = self.transcribe(tmp_path)
            
            # Șterge fișierul temporar
            os.unlink(tmp_path)
            
            return text
        except Exception as e:
            logger.error(f"Error transcribing bytes: {e}")
            return None


# Singleton instance
_stt_service_instance = None

def get_stt_service() -> STTService:
    """Get singleton instance"""
    global _stt_service_instance
    if _stt_service_instance is None:
        _stt_service_instance = STTService()
    return _stt_service_instance


