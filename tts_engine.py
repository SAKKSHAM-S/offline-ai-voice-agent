import os
import threading
import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from pathlib import Path

class TTSEngine:
    """
    Manages text-to-speech synthesis using Kokoro ONNX with dual voices
    (Jarvis: am_adam, Wave: af_heart) and thread-safe audio playback locks.
    """
    def __init__(self, config: dict):
        self.config = config
        tts_cfg = config.get("tts", {})
        self.engine_name = tts_cfg.get("engine", "kokoro")
        self.jarvis_voice = tts_cfg.get("jarvis_voice", "am_adam")
        self.wave_voice = tts_cfg.get("wave_voice", "af_heart")
        self.speed = tts_cfg.get("speed", 1.1)

        self.kokoro = None
        self.audio_lock = threading.Lock()
        self._load_engine()

    def _load_engine(self):
        """Initializes the Kokoro ONNX model and tokenizer files from local directory."""
        try:
            print("🔊 Initializing Kokoro ONNX TTS engine...")
            
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            
            model_path = script_dir / "kokoro-v1.0.onnx"
            voices_path = script_dir / "voices-v1.0.bin"
            
            
            if model_path.exists() and voices_path.exists():
                # Pass strings to Kokoro if it requires strings instead of Path objects
                self.kokoro = Kokoro(str(model_path), str(voices_path))
                print("🔊 Kokoro TTS initialized successfully.")
            else:
                print(f"⚠️ Kokoro model files not found in: {script_dir.absolute()}")
        except Exception as e:
            print(f"❌ Error initializing Kokoro TTS: {str(e)}")

    def speak(self, text: str, character: str = "Jarvis"):
        """Synthesizes and plays text audio using the specified character's voice."""
        if not text.strip():
            return

        # Select voice based on active persona (Jarvis vs Wave)
        voice = self.wave_voice if character.lower() == "wave" else self.jarvis_voice

        # Print the text to the console so you can read it too!
        print(f"[{character}]: {text}")

        with self.audio_lock:
            try:
                if self.kokoro:
                    samples, sample_rate = self.kokoro.create(
                        text, 
                        voice=voice, 
                        speed=self.speed, 
                        lang="en-us"
                    )
                    if len(samples) > 0:
                        sd.play(samples, sample_rate)
                        sd.wait()
                else:
                    print(f"⚠️ Kokoro engine missing, text-only mode.")
            except Exception as e:
                print(f"❌ TTS Playback Error: {str(e)}")