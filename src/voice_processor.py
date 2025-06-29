# src/voice_processor.py
import speech_recognition as sr
import whisper
import tempfile
import os
import logging
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# --- Microphone Availability Check ---
def is_microphone_available() -> bool:
    """
    Checks if any microphones are available on the system.
    This is crucial for gracefully handling server environments like Streamlit Cloud.
    """
    try:
        # Get the list of microphone names. If this list is not empty, a mic is available.
        mic_list = sr.Microphone.list_microphone_names()
        return len(mic_list) > 0
    except Exception as e:
        # If any error occurs (like on a server without proper audio libraries), assume no mic.
        logger.warning(f"Could not check for microphones, assuming none are available. Error: {e}")
        return False

# Check for microphone availability once on startup and export it.
MICROPHONE_AVAILABLE = is_microphone_available()

# --- Whisper Model Loading ---
def load_whisper_model() -> Optional[whisper.Whisper]:
    """
    Loads the Whisper small model. Returns None if loading fails.
    """
    try:
        model = whisper.load_model("small")
        logger.info("Whisper small model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        return None

# Load Whisper model once on startup
WHISPER_MODEL = load_whisper_model()
WHISPER_AVAILABLE = WHISPER_MODEL is not None


class VoiceProcessor:
    """
    Enhanced voice processor that uses both Google Speech Recognition and Whisper
    for improved accuracy and fallback options.
    """
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.whisper_model = WHISPER_MODEL

    def recognize_speech_google(
        self,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        timeout: int = 10,
        phrase_limit: int = 15
    ) -> Dict[str, Any]:
        """
        Uses Google Speech Recognition to convert speech to text.
        """
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold

        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                text = self.recognizer.recognize_google(audio)
                logger.info(f"Google recognized: {text}")
                return {
                    "text": text, 
                    "status": "success", 
                    "error": None, 
                    "method": "Google Speech Recognition"
                }

            except sr.WaitTimeoutError:
                error_msg = "Listening timed out. Please try speaking sooner."
                logger.warning(error_msg)
                return {"text": None, "status": "error", "error": error_msg, "method": "Google Speech Recognition"}
            
            except sr.UnknownValueError:
                error_msg = "Speech was unintelligible with Google recognition."
                logger.error(error_msg)
                return {"text": None, "status": "error", "error": error_msg, "method": "Google Speech Recognition"}
            
            except sr.RequestError as e:
                error_msg = f"Could not request results from Google speech service; {e}"
                logger.error(error_msg)
                return {"text": None, "status": "error", "error": error_msg, "method": "Google Speech Recognition"}

    def recognize_speech_whisper(
        self,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        timeout: int = 10,
        phrase_limit: int = 15
    ) -> Dict[str, Any]:
        """
        Uses Whisper model to convert speech to text.
        """
        if not self.whisper_model:
            return {
                "text": None, 
                "status": "error", 
                "error": "Whisper model not available", 
                "method": "Whisper"
            }

        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold

        with sr.Microphone() as source:
            try:
                # Record audio
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                
                # Save audio to temporary file for Whisper
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    temp_audio.write(audio.get_wav_data())
                    temp_audio_path = temp_audio.name

                try:
                    # Use Whisper to transcribe
                    result = self.whisper_model.transcribe(temp_audio_path)
                    text = result["text"].strip()
                    
                    if text:
                        logger.info(f"Whisper recognized: {text}")
                        return {
                            "text": text,
                            "status": "success",
                            "error": None,
                            "method": "Whisper",
                            "confidence": result.get("segments", [{}])[0].get("avg_logprob", 0) if result.get("segments") else 0
                        }
                    else:
                        return {
                            "text": None,
                            "status": "error",
                            "error": "Whisper could not detect any speech",
                            "method": "Whisper"
                        }
                        
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_audio_path):
                        os.unlink(temp_audio_path)

            except sr.WaitTimeoutError:
                error_msg = "Listening timed out. Please try speaking sooner."
                logger.warning(error_msg)
                return {"text": None, "status": "error", "error": error_msg, "method": "Whisper"}
            
            except Exception as e:
                error_msg = f"Whisper transcription error: {str(e)}"
                logger.error(error_msg)
                return {"text": None, "status": "error", "error": error_msg, "method": "Whisper"}

    def recognize_speech_hybrid(
        self,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        timeout: int = 10,
        phrase_limit: int = 15,
        primary_method: str = "google"
    ) -> Dict[str, Any]:
        """
        Hybrid approach: tries primary method first, falls back to secondary if needed.
        """
        if primary_method.lower() == "google":
            primary_result = self.recognize_speech_google(energy_threshold, pause_threshold, timeout, phrase_limit)
            if primary_result["status"] == "success":
                return primary_result
            
            # Fallback to Whisper if Google fails and Whisper is available
            if WHISPER_AVAILABLE:
                logger.info("Google recognition failed, trying Whisper as fallback...")
                fallback_result = self.recognize_speech_whisper(energy_threshold, pause_threshold, timeout, phrase_limit)
                if fallback_result["status"] == "success":
                    fallback_result["method"] = "Whisper (fallback)"
                    return fallback_result
            
            return primary_result
        
        else:  # primary_method == "whisper"
            if not WHISPER_AVAILABLE:
                # If Whisper not available, use Google directly
                return self.recognize_speech_google(energy_threshold, pause_threshold, timeout, phrase_limit)
            
            primary_result = self.recognize_speech_whisper(energy_threshold, pause_threshold, timeout, phrase_limit)
            if primary_result["status"] == "success":
                return primary_result
            
            # Fallback to Google if Whisper fails
            logger.info("Whisper recognition failed, trying Google as fallback...")
            fallback_result = self.recognize_speech_google(energy_threshold, pause_threshold, timeout, phrase_limit)
            if fallback_result["status"] == "success":
                fallback_result["method"] = "Google Speech Recognition (fallback)"
                return fallback_result
            
            return primary_result

    def recognize_speech(
        self,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        timeout: int = 10,
        phrase_limit: int = 15,
        method: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Main speech recognition method with multiple options.
        
        Args:
            method: "google", "whisper", or "hybrid"
        """
        if method.lower() == "google":
            return self.recognize_speech_google(energy_threshold, pause_threshold, timeout, phrase_limit)
        elif method.lower() == "whisper":
            return self.recognize_speech_whisper(energy_threshold, pause_threshold, timeout, phrase_limit)
        else:  # hybrid (default)
            return self.recognize_speech_hybrid(energy_threshold, pause_threshold, timeout, phrase_limit)

    def get_available_methods(self) -> list:
        """Returns list of available recognition methods."""
        methods = ["Google Speech Recognition"]
        if WHISPER_AVAILABLE:
            methods.append("Whisper")
            methods.append("Hybrid (Google + Whisper)")
        return methods