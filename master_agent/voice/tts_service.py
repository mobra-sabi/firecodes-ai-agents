#!/usr/bin/env python3
"""
🔊 Text-to-Speech Service
Folosește Piper sau Coqui pentru generare vocală
"""

import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# TTS Configuration
TTS_ENGINE = os.getenv("TTS_ENGINE", "piper")
TTS_MODEL_PATH = os.getenv("TTS_MODEL_PATH", "/opt/models/piper/ro_RO-doru-medium")
TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "/srv/hf/ai_agents/master_agent/voice/output")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "22050"))


class TTSService:
    """Serviciu pentru Text-to-Speech"""
    
    def __init__(self):
        self.engine = TTS_ENGINE
        self.model_path = TTS_MODEL_PATH
        self.output_dir = TTS_OUTPUT_DIR
        
        # Creează directorul de output
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.model_loaded = False
    
    def _load_piper(self):
        """Încarcă modelul Piper"""
        try:
            import piper
            from piper import PiperVoice
            from piper.download import ensure_voice_exists, find_voice
            
            # Verifică dacă modelul există
            if os.path.exists(self.model_path):
                voice = PiperVoice.load(self.model_path)
            else:
                # Folosește modelul default
                voice = PiperVoice.load(ensure_voice_exists("ro_RO-doru-medium", None))
            
            self.piper_voice = voice
            self.model_loaded = True
            logger.info("✅ Piper model loaded")
            return True
        except ImportError:
            logger.warning("⚠️ Piper not installed. Install with: pip install piper-tts")
            return False
        except Exception as e:
            logger.error(f"Error loading Piper model: {e}")
            return False
    
    def _load_coqui(self):
        """Încarcă modelul Coqui TTS"""
        try:
            from TTS.api import TTS
            
            # Încarcă modelul
            self.coqui_tts = TTS(model_name="tts_models/ro/cv/vits", gpu=False)
            self.model_loaded = True
            logger.info("✅ Coqui TTS model loaded")
            return True
        except ImportError:
            logger.warning("⚠️ Coqui TTS not installed. Install with: pip install TTS")
            return False
        except Exception as e:
            logger.error(f"Error loading Coqui TTS model: {e}")
            return False
    
    def synthesize(self, text: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Generează audio din text
        
        Args:
            text: Textul de sintetizat
            output_filename: Numele fișierului de output (opțional)
        
        Returns:
            Path către fișierul audio generat sau None
        """
        if not self.model_loaded:
            if self.engine == "piper":
                if not self._load_piper():
                    return None
            elif self.engine == "coqui":
                if not self._load_coqui():
                    return None
        
        # Generează nume fișier
        if not output_filename:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            output_filename = f"response_{timestamp}.wav"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            if self.engine == "piper":
                return self._synthesize_piper(text, output_path)
            elif self.engine == "coqui":
                return self._synthesize_coqui(text, output_path)
            else:
                logger.error(f"Unknown TTS engine: {self.engine}")
                return None
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None
    
    def _synthesize_piper(self, text: str, output_path: str) -> Optional[str]:
        """Sintetizează folosind Piper"""
        try:
            with open(output_path, "wb") as f:
                self.piper_voice.synthesize(text, f, speaker_id=None)
            
            logger.info(f"Generated audio: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error in Piper synthesis: {e}")
            return None
    
    def _synthesize_coqui(self, text: str, output_path: str) -> Optional[str]:
        """Sintetizează folosind Coqui TTS"""
        try:
            self.coqui_tts.tts_to_file(text=text, file_path=output_path)
            logger.info(f"Generated audio: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error in Coqui synthesis: {e}")
            return None


# Singleton instance
_tts_service_instance = None

def get_tts_service() -> TTSService:
    """Get singleton instance"""
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = TTSService()
    return _tts_service_instance


