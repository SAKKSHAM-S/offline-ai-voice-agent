import json
import os
import threading
import time

from actions import execute_windows_action, fast_action_rules
from ai_engine import background_interrupt_monitor, query_ollama_stream
from audio_engine import AudioEngine
from tts_engine import TTSEngine


def load_config(filepath="config.json"):
    """Loads configuration from JSON file or provides defaults."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {
        "system": {"assistant_name": "Jarvis", "secondary_assistant_name": "Wave"},
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama3.2",
            "temperature": 0.2,
            "max_tokens": 150,
        },
        "whisper": {
            "model_size": "base.en",
            "device": "cpu",
            "compute_type": "int8",
            "silence_cutoff_sec": 0.8,
        },
        "tts": {
            "engine": "kokoro",
            "jarvis_voice": "am_adam",
            "wave_voice": "af_heart",
            "speed": 1.1,
        },
    }


def main():
    print("🚀 Initializing AI Desktop Assistant...")
    config = load_config()

    audio = AudioEngine(config)
    tts = TTSEngine(config)

    active_character = config["system"].get("assistant_name", "Jarvis")
    secondary_character = config["system"].get("secondary_assistant_name", "Wave")

    print(
        f"\n✨ Assistant Online! Current Active Character: {active_character}"
    )
    print("Speak into your microphone or say 'exit' / 'quit' to stop.\n")

    tts.speak(
        f"All systems nominal. {active_character} online and ready.",
        active_character,
    )

    while True:
        try:
            # Listen for user command via microphone & Faster-Whisper
            user_input = audio.listen_for_command(timeout=15.0)
            if not user_input:
                continue

            print(f'\n🗣️ You said: "{user_input}"')
            lower_input = user_input.lower().strip()

            # Exit check
            if any(
                term in lower_input
                for term in ["exit assistant", "quit assistant", "shut down"]
            ):
                tts.speak("Goodbye!", active_character)
                print("👋 Shutting down assistant. Goodbye!")
                break

            # Character switching check (Jarvis vs. Wave)
            if (
                "switch to wave" in lower_input
                or "wave" in lower_input
                and "switch" in lower_input
                or lower_input == "wave"
            ):
                active_character = secondary_character
                print(f"🔄 Switched active personality to: {active_character}")
                tts.speak("Switching to Wave personality.", active_character)
                continue
            elif (
                "switch to jarvis" in lower_input
                or "jarvis" in lower_input
                and "switch" in lower_input
                or lower_input == "jarvis"
            ):
                active_character = config["system"].get("assistant_name", "Jarvis")
                print(f"🔄 Switched active personality to: {active_character}")
                tts.speak("Switching back to Jarvis.", active_character)
                continue

            # 1. Check Fast Action Rules (Zero-latency path)
            fast_result = fast_action_rules(user_input)
            if fast_result:
                reply_text = fast_result["reply"]
                action = fast_result["action"]
                target = fast_result["target"]

                print(f"⚡ Fast Action Triggered: {action} (Target: '{target}')")
                tts.speak(reply_text, active_character)
                execution_result = execute_windows_action(action, target)
                print(f"⚙️ Action Result: {execution_result}")
                continue

            # 2. LLM Inference Path with streaming TTS & interrupt monitor
            system_prompt = config.get("system_prompt", "")
            if not system_prompt:
                system_prompt = (
                    "You are a dual-personality AI voice assistant named Jarvis and"
                    " Wave. Always output valid JSON strictly matching the schema:"
                    ' {"reply": "<spoken response>", "action": "<action_code>",'
                    ' "target": "<target_string>"}.'
                )

            print("🧠 Processing via Ollama LLM...")

            interrupt_flag = [False]
            stop_event = threading.Event()

            # Start background interrupt monitor thread
            monitor_thread = threading.Thread(
                target=background_interrupt_monitor,
                args=(stop_event, interrupt_flag, audio),
                daemon=True,
            )
            monitor_thread.start()

            full_reply_buffer = ""
            final_response = {"reply": "", "action": "none", "target": ""}

            def stream_callback(text_chunk, parsed_data):
                nonlocal full_reply_buffer, final_response
                final_response = parsed_data
                if text_chunk and not interrupt_flag[0]:
                    full_reply_buffer += text_chunk
                    if any(p in text_chunk for p in [".", "!", "?", ",", ";"]):
                        tts.speak(full_reply_buffer.strip(), active_character)
                        full_reply_buffer = ""

            # Query Ollama with streaming
            response_data = query_ollama_stream(
                user_input, config, system_prompt, callback=stream_callback
            )
            if response_data:
                final_response = response_data

            # Stop interrupt monitor thread
            stop_event.set()
            monitor_thread.join(timeout=0.5)

            if interrupt_flag[0]:
                print("🛑 Speech interrupted by user!")
                continue

            # Flush remaining text buffer if any (Prevents double playback)
            if full_reply_buffer.strip():
                tts.speak(full_reply_buffer.strip(), active_character)

            # Execute action if any returned by LLM
            action = final_response.get("action", "none")
            target = final_response.get("target", "")
            if action and action != "none":
                print(f"⚙️ Executing action: {action} (Target: '{target}')")
                exec_res = execute_windows_action(action, target)
                print(f"⚙️ Result: {exec_res}")

        except KeyboardInterrupt:
            print("\n👋 Exiting via keyboard interrupt.")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {str(e)}")


if __name__ == "__main__":
    main()