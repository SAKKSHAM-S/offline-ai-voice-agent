# 🎙️ Local AI Desktop Assistant (Jarvis & Wave)

A fully offline, privacy-first AI desktop assistant built in Python. It listens to your voice commands via Faster-Whisper, processes intent using a locally hosted LLM via Ollama, controls Windows applications and system actions, and responds back in real-time with dual-voice synthesis via Kokoro ONNX.

---

## 🚀 Key Features

- **100% Local & Offline Execution:** No cloud APIs, external tracking, or data leaks.
- **Speech-to-Text (STT):** Powered by `faster-whisper` with automatic Voice Activity Detection (VAD) and interactive model selection (tiny to large-v3).
- **Dual Voice Personalities (TTS):** Instant voice switching between two distinct personalities:
  - **Jarvis** (Default - Male Voice: `am_adam`)
  - **Wave** (Secondary - Female Voice: `af_heart`)
- **Fast-Path Action Engine:** Near zero-latency execution for common OS commands (opening apps, volume control, clipboard operations, system status) using regex rules before reaching the LLM.
- **LLM Tool Calling via Streaming JSON:** Integrates with local Ollama models (e.g., `llama3.2`) to dynamically return structured actions and spoken responses.
- **Background Interruption Listener:** Monitored background listener that cancels speaking when interrupt keywords (*"stop"*, *"shut up"*, *"wait"*) are spoken.

---

## 🏗️ Architecture & How It Works

```text
                        +----------------------+
                        |   User Speech Input  |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        | Faster-Whisper (STT) |
                        +----------+-----------+
                                   |
                        Transcribed Text Prompt
                                   |
           +-----------------------+-----------------------+
           |                                               |
           v                                               v
[Fast-Path Regex Rules]                        [Ollama LLM Streaming Engine]
(Zero-latency system actions)                  (Pulls JSON: reply, action, target)
           |                                               |
           +-----------------------+-----------------------+
                                   |
                                   v
                        +----------------------+
                        |   Action Execution   |
                        | (PyAutoGUI / Subproc)|
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        |   Kokoro ONNX (TTS)  |
                        |   Voice Synthesis    |
                        +----------------------+
```

1. **`audio_engine.py`**: Captures microphone input streaming, applies VAD silence cutoff detection, and transcribes speech into text using Faster-Whisper.
2. **`actions.py`**: Checks if the user's voice command matches instant system action patterns (e.g., *"open chrome"*, *"check cpu"*). If matched, it executes native Windows automation commands immediately via PyAutoGUI, psutil, or subprocess.
3. **`ai_engine.py`**: If no fast action rule matches, the prompt streams to Ollama. The response is parsed into a JSON schema containing `{"reply": "...", "action": "...", "target": "..."}`.
4. **`tts_engine.py`**: Synthesizes the generated text response into high-quality audio using `kokoro-onnx` and plays it through your speakers based on the active voice persona (`Jarvis` or `Wave`).
5. **`main.py`**: Coordinates the entire continuous event loop and multi-threading execution.

---

## 🛠️ Supported System Actions

- **Application Control:** Open or terminate applications (e.g., Chrome, VS Code, Settings).
- **Web & System Search:** Perform Google web searches or trigger Windows search.
- **System Metrics:** Check real-time CPU, RAM, and Battery statuses.
- **Clipboard Utility:** Read aloud or auto-type clipboard content into active windows.
- **Audio & Media Control:** Mute/unmute, adjust volume levels, play/pause, or skip media tracks.

---

## 📋 Prerequisites

1. **Python:** Version 3.10 to 3.12 installed.
2. **Ollama:** Installed locally from [ollama.com](https://ollama.com/).
   Pull your preferred model (e.g., Llama 3.2):
   ```bash
   ollama run llama3.2
   ```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/SAKKSHAM-S/offline-ai-voice-agent.git
cd offline-ai-voice-agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Kokoro TTS Model Files
Download and place the following two model files in the project directory (`jarvis_assistant/`):
- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`

*(You can download these from the official [Kokoro-ONNX Releases](https://github.com/thewh1teagle/kokoro-onnx/releases) page).*

---

## 🏃 How to Use

1. Ensure **Ollama** is running in the background.
2. Run the main script:
   ```bash
   python main.py
   ```
3. **Select Whisper Model:** Choose a model size when prompted (e.g., option `3` for `base`).
4. **Speak Commands:**
   - *"Open Chrome"*
   - *"Check my RAM usage"*
   - *"Switch to Wave"*
   - *"Type hello world"*
   - *"Switch back to Jarvis"*
   - *"Exit assistant"*

---

## 📂 Project Structure

```text
jarvis_assistant/
├── .gitignore          # Ignores cache and large ONNX/BIN binaries
├── LICENSE             # MIT Open Source License
├── README.md           # Project documentation and setup guide
├── requirements.txt    # Python dependency packages
├── config.json         # Local assistant configuration
├── config.example.json # Example configuration template
├── audio_engine.py     # Speech-to-Text and microphone streaming
├── tts_engine.py       # Text-to-Speech voice synthesis engine
├── actions.py          # Fast OS actions and PyAutoGUI rules
├── ai_engine.py        # Ollama LLM integration and parser
└── main.py             # Entry point and main event loop
```