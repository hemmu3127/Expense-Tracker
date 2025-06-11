# src/voice_processor.py
import speech_recognition as sr
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- THIS IS THE SECTION THAT WAS MISSING ---
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
# --- END OF MISSING SECTION ---


class VoiceProcessor:
    """
    Handles voice input and converts it to text with robust settings
    for noise and speech detection.
    """
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def recognize_speech(
        self,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        timeout: int = 10,
        phrase_limit: int = 15
    ) -> dict:
        """
        Listens for audio and returns a dictionary with the recognized text
        and any potential status or error messages.
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
                return {"text": text, "status": "success", "error": None}

            except sr.WaitTimeoutError:
                error_msg = "Listening timed out. Please try speaking sooner."
                logger.warning(error_msg)
                return {"text": None, "status": "error", "error": error_msg}
            
            except sr.UnknownValueError:
                error_msg = "Speech was unintelligible. Please speak clearly."
                logger.error(error_msg)
                return {"text": None, "status": "error", "error": error_msg}
            
            except sr.RequestError as e:
                error_msg = f"Could not request results from speech service; {e}"
                logger.error(error_msg)
                return {"text": None, "status": "error", "error": error_msg}