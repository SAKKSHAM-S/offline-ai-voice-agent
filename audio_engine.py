import queue
import threading
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

class AudioEngine:
    """
    Manages persistent microphone input streaming, Voice Activity Detection (VAD)
    silence cutoffs, and Faster-Whisper transcription with access to all standard models.
    """
    def __init__(self, config: dict):
        self.config = config
        whisper_cfg = config.get("whisper", {})
        self.device = whisper_cfg.get("device", "cpu")
        self.compute_type = whisper_cfg.get("compute_type", "int8")
        self.silence_cutoff = whisper_cfg.get("silence_cutoff_sec", 0.8)
        
        self.sample_rate = 16000
        self.audio_queue = queue.Queue()
        self.model = None
        self._load_model()

    def _load_model(self):
        """Interactive prompt to select any Whisper model, check local cache, and download if needed."""
        print("\n" + "="*65)
        print("🎙️ SELECT ANY WHISPER MODEL FOR SPEECH-TO-TEXT")
        print("="*65)
        print("  [1] tiny          [6] small.en")
        print("  [2] tiny.en       [7] medium")
        print("  [3] base          [8] medium.en")
        print("  [4] base.en       [9] large-v2")
        print("  [5] small         [10] large-v3")
        print("-"*65)

        choice = input("👉 Enter your choice (1-10, default 3 for base): ").strip()

        model_map = {
            "1": "tiny",
            "2": "tiny.en",
            "3": "base",
            "4": "base.en",
            "5": "small",
            "6": "small.en",
            "7": "medium",
            "8": "medium.en",
            "9": "large-v2",
            "10": "large-v3"
        }
        model_size = model_map.get(choice, "base")
        print(f"🔹 Selected Model: {model_size}")

        try:
            print(f"Checking local cache / downloading Faster-Whisper model ({model_size})...")
            # Automatically checks local HuggingFace cache or downloads if missing
            self.model = WhisperModel(model_size, device=self.device, compute_type=self.compute_type)
            print(f"🚀 Faster-Whisper model ({model_size}) ready!")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {str(e)}")

    def record_audio_snippet(self, duration: float = 0.6) -> str:
        """Records a short audio snippet for quick background monitoring."""
        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()
            audio_flattened = recording.flatten()
            
            if self.model and len(audio_flattened) > 0:
                segments, _ = self.model.transcribe(audio_flattened, beam_size=1, language="en")
                return " ".join([seg.text for seg in segments]).strip()
        except Exception:
            pass
        return ""

    def listen_for_command(self, timeout: float = 10.0) -> str:
        """Listens continuously from the microphone until speech is detected and silence cutoff triggers."""
        print("🎤 Listening for command...")
        audio_chunks = []
        silence_duration = 0.0
        chunk_duration = 0.1
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        speech_detected = False
        start_time = time.time()

        def callback(indata, frames, time_info, status):
            if status:
                pass
            self.audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=chunk_samples,
                callback=callback
            ):
                while True:
                    if time.time() - start_time > timeout and not speech_detected:
                        return ""

                    try:
                        chunk = self.audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    amplitude = np.max(np.abs(chunk))
                    
                    if amplitude > 0.015:
                        if not speech_detected:
                            speech_detected = True
                        audio_chunks.append(chunk)
                        silence_duration = 0.0
                    elif speech_detected:
                        audio_chunks.append(chunk)
                        silence_duration += chunk_duration
                        if silence_duration >= self.silence_cutoff:
                            break

            if not audio_chunks:
                return ""

            full_audio = np.concatenate(audio_chunks, axis=0).flatten()
            segments, _ = self.model.transcribe(full_audio, beam_size=1, language="en")
            transcript = " ".join([seg.text for seg in segments]).strip()

            # Filter out common Whisper silence hallucination artifacts
            hallucinations = ["thanks for watching!", "subtitles by", "thank you."]
            if any(h in transcript.lower() for h in hallucinations):
                return ""

            return transcript

        except Exception as e:
            print(f"❌ Audio Recording Error: {str(e)}")
            return ""
          