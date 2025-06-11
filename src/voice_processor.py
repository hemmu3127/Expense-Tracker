# src/voice_processor.py
import speech_recognition as sr
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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

        Args:
            energy_threshold (int): The energy level threshold for considering
                                    sound as speech. Higher values ignore more noise.
            pause_threshold (float): Seconds of non-speaking audio before a
                                     phrase is considered complete.
            timeout (int): Seconds to wait for speech to start before timing out.
            phrase_limit (int): Maximum possible seconds for a single phrase.

        Returns:
            dict: A dictionary containing 'text', 'status', and 'error'.
        """
        # Apply the dynamic settings to the recognizer instance
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold

        with sr.Microphone() as source:
            try:
                # Use listen_in_background for more robust, non-blocking listening if needed,
                # but for this simple case, listen() is fine.
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                
                # Use Google's recognizer
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