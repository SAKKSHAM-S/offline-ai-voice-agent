import os
import re
import urllib.parse
import webbrowser
import subprocess
import pyautogui
import psutil
import pyperclip

def clean_app_target(target: str) -> str:
    """Removes common filler words, leading articles, and punctuation from target strings."""
    if not target:
        return ""
    target = target.lower().strip()
    
    # Strip trailing punctuation (like periods or commas from speech transcription)
    target = re.sub(r'[.,!?]+$', '', target)
    
    # Remove leading articles and fillers
    fillers = [
        r"\bthe\b", r"\ba\b", r"\ban\b", r"\bplease\b", r"\bfor me\b", 
        r"\band play\b", r"\bcan you\b", r"\bopen\b", r"\blaunch\b", 
        r"\bstart\b", r"\bapp\b", r"\bapplication\b"
    ]
    for filler in fillers:
        target = re.sub(filler, "", target)
        
    return target.strip()

def fast_action_rules(user_input: str) -> dict | None:
    """
    Evaluates fast-path regex rules to execute instant actions without LLM inference.
    Returns dict with 'reply', 'action', and 'target' if matched, else None.
    """
    text = user_input.lower().strip()

    # Browser search rule
    match = re.search(r"^(?:search\s+(?:for\s+)?|google\s+|look\s+up\s+)(.+)", text)
    if match:
        query = match.group(1).strip()
        return {
            "reply": f"Searching for {query}.",
            "action": "browser_search",
            "target": query
        }

    # Type text rule
    match = re.search(r"^(?:type|write|input)\s+[\"']?(.*?)[\"']?$", text)
    if match:
        content = match.group(1).strip()
        return {
            "reply": "Typing text.",
            "action": "type_text",
            "target": content
        }

    # System metrics rule
    if re.search(r"\b(system info|cpu|ram|memory|battery)\b", text):
        target = "all"
        if "cpu" in text:
            target = "cpu"
        elif "ram" in text or "memory" in text:
            target = "ram"
        elif "battery" in text:
            target = "battery"
        return {
            "reply": "Checking system status.",
            "action": "system_info",
            "target": target
        }

    # Clipboard read rule
    if re.search(r"\b(read|check|what is on|show)\s+(my\s+)?clipboard\b", text):
        return {
            "reply": "Reading clipboard content.",
            "action": "clipboard_read",
            "target": ""
        }

    # Clipboard type rule
    if re.search(r"\b(type|paste)\s+(my\s+)?clipboard\b", text):
        return {
            "reply": "Typing clipboard content.",
            "action": "clipboard_type",
            "target": ""
        }

   # Volume control rule (supports 'increase', 'decrease', 'up', 'down', 'mute')
    if re.search(r"\b(volume|sound|speaker)\b", text):
        direction = "up"
        if re.search(r"\b(down|decrease|lower|quieter)\b", text):
            direction = "down"
        elif re.search(r"\b(mute)\b", text):
            direction = "mute"
        elif re.search(r"\b(unmute)\b", text):
            direction = "unmute"
        return {
            "reply": f"Adjusting volume {direction}.",
            "action": "volume_control",
            "target": direction
        }

    # Open app rule
    match = re.search(r"^(?:open|launch|start)\s+(.+)", text)
    if match:
        app_name = clean_app_target(match.group(1))
        return {
            "reply": f"Opening {app_name}.",
            "action": "open_app",
            "target": app_name
        }

    # Close app rule
    match = re.search(r"^(?:close|exit|terminate)\s+(.+)", text)
    if match:
        app_name = clean_app_target(match.group(1))
        return {
            "reply": f"Closing {app_name}.",
            "action": "close_app",
            "target": app_name
        }

    return None


def execute_windows_action(action: str, target: str) -> str:
    """Executes native Windows actions based on action code and target."""
    try:
        if action == "browser_search":
            query = urllib.parse.quote_plus(target)
            url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return f"Opened browser search for: {target}"

        elif action == "system_search":
            pyautogui.hotkey('win', 's')
            pyautogui.sleep(0.2)
            pyautogui.typewrite(target, interval=0.02)
            return f"Executed Windows search for: {target}"

        elif action == "type_text":
            pyautogui.typewrite(target, interval=0.02)
            return "Typed text into active window."
        elif action == "open_app":
            cleaned = clean_app_target(target)
            if cleaned in ["chrome", "google chrome"]:
                webbrowser.open("https://www.google.com")
            elif cleaned in ["youtube"]:
                webbrowser.open("https://www.youtube.com")
            elif cleaned in ["setting", "settings"]:
                subprocess.Popen("start ms-settings:", shell=True)
                return "Launched Windows Settings."
            elif cleaned in ["vs code", "visual studio code"]:
                subprocess.Popen("code", shell=True)
                return "Launched Visual Studio Code."
            else:
                subprocess.Popen(f"start {cleaned}", shell=True)
            return f"Launched application: {cleaned}"
        elif action == "close_app":
            cleaned = clean_app_target(target)
            subprocess.run(f"taskkill /f /im {cleaned}.exe", shell=True, capture_output=True)
            return f"Terminated process: {cleaned}"

        elif action == "system_info":
            if target == "cpu":
                return f"CPU Usage: {psutil.cpu_percent()}%"
            elif target == "ram":
                ram = psutil.virtual_memory()
                return f"RAM Usage: {ram.percent}% ({round(ram.used / (1024**3), 1)}GB / {round(ram.total / (1024**3), 1)}GB)"
            elif target == "battery":
                battery = psutil.sensors_battery()
                if battery:
                    return f"Battery: {battery.percent}% ({'Plugged in' if battery.power_plugged else 'Discharging'})"
                return "Battery status unavailable."
            else:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                return f"System Metrics - CPU: {cpu}%, RAM: {ram}%"

        elif action == "clipboard_read":
            content = pyperclip.paste()
            return content if content else "Clipboard is empty."

        elif action == "clipboard_type":
            content = pyperclip.paste()
            if content:
                pyautogui.typewrite(content, interval=0.01)
                return "Typed clipboard contents."
            return "Clipboard was empty."

        elif action == "volume_control":
            if target == "up":
                pyautogui.press('volumeup', presses=5)
            elif target == "down":
                pyautogui.press('volumedown', presses=5)
            elif target in ["mute", "unmute"]:
                pyautogui.press('volumemute')
            return f"Adjusted volume: {target}"

        elif action == "media_control":
            if target in ["play", "pause"]:
                pyautogui.press('playpause')
            elif target == "next":
                pyautogui.press('nexttrack')
            elif target == "previous":
                pyautogui.press('prevtrack')
            return f"Media command executed: {target}"

        elif action == "none":
            return "No action required."

        return f"Unknown action: {action}"

    except Exception as e:
        return f"Error executing action {action}: {str(e)}"