import json
import re
import requests
import threading
import time

try:
    from duckduckgo_search import DDGS  # type: ignore
except ImportError:
    try:
        from ddgs import DDGS  # type: ignore
    except ImportError:
        DDGS = None

def extract_json_from_stream(text_buffer: str) -> dict | None:
    """
    Resilient key-agnostic parser to extract JSON reply, action, and target
    regardless of key order or partial stream chunk states.
    """
    try:
        return json.loads(text_buffer)
    except json.JSONDecodeError:
        pass

    result = {"reply": "", "action": "none", "target": ""}

    reply_match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)', text_buffer)
    if reply_match:
        result["reply"] = reply_match.group(1).encode().decode('unicode-escape', errors='ignore')

    action_match = re.search(r'"action"\s*:\s*"([^"]*)"', text_buffer)
    if action_match:
        result["action"] = action_match.group(1)

    target_match = re.search(r'"target"\s*:\s*"((?:[^"\\]|\\.)*)', text_buffer)
    if target_match:
        result["target"] = target_match.group(1).encode().decode('unicode-escape', errors='ignore')

    if result["reply"] or result["action"] != "none":
        return result

    return None


def background_interrupt_monitor(stop_event: threading.Event, interrupt_flag: list, audio_engine_ref):
    """
    Monitors background audio for interruption phrases (e.g., 'stop', 'shut up', 'wait')
    while the assistant is speaking.
    """
    while not stop_event.is_set():
        try:
            phrase = audio_engine_ref.record_audio_snippet(duration=0.6)
            if phrase:
                lower_phrase = phrase.lower()
                if any(w in lower_phrase for w in ["stop", "shut up", "wait", "hold on", "quiet"]):
                    interrupt_flag[0] = True
                    break
        except Exception:
            pass
        time.sleep(0.05)


def query_ollama_stream(prompt: str, config: dict, system_prompt: str, callback=None):
    """
    Sends prompt to Ollama with streaming enabled.
    Calls callback(parsed_chunk) as valid JSON fields are recognized.
    """
    url = f"{config['ollama']['base_url']}/api/generate"
    payload = {
        "model": config["ollama"]["model"],
        "prompt": f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
        "options": {
            "temperature": config["ollama"]["temperature"],
            "num_predict": config["ollama"]["max_tokens"]
        },
        "stream": True
    }

    buffer = ""
    last_extracted_reply_len = 0

    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        for line in response.iter_lines():
            if line:
                body = json.loads(line.decode('utf-8'))
                token = body.get("response", "")
                buffer += token

                parsed = extract_json_from_stream(buffer)
                if parsed and callback:
                    current_reply = parsed.get("reply", "")
                    if len(current_reply) > last_extracted_reply_len:
                        new_text_chunk = current_reply[last_extracted_reply_len:]
                        callback(new_text_chunk, parsed)
                        last_extracted_reply_len = len(current_reply)

                if body.get("done", False):
                    break

        return extract_json_from_stream(buffer) or {"reply": "Done.", "action": "none", "target": ""}

    except Exception as e:
        return {"reply": f"Error connecting to AI engine: {str(e)}", "action": "none", "target": ""}