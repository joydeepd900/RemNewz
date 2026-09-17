import os
import json
from notifier.telegram import send_message

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

class Helpzy:
    def __init__(self, file_path=SETTINGS_FILE):
        self.file_path = file_path
        self.settings = {}
        self._load()

    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.settings = {}

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"[helpzy] Failed to save settings: {e}")

    def handle_command(self, text: str) -> bool:
        """Process a Helpzy command. Returns True if handled."""
        parts = text.strip().split()
        if not parts:
            return False
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "/help":
            self._send_help()
            return True
            
        if cmd == "/config":
            if not args:
                self._send_config()
            else:
                subcmd = args[0].lower()
                if subcmd == "add_topic" and len(args) > 1:
                    topic = " ".join(args[1:])
                    topics = self.settings.get("topics", [])
                    if topic not in topics:
                        topics.append(topic)
                    self.settings["topics"] = topics
                    self._save()
                    send_message(f"✅ Added topic: <b>{topic}</b>")
                elif subcmd == "remove_topic" and len(args) > 1:
                    topic = " ".join(args[1:])
                    topics = self.settings.get("topics", [])
                    if topic in topics:
                        topics.remove(topic)
                    self.settings["topics"] = topics
                    self._save()
                    send_message(f"✅ Removed topic: <b>{topic}</b>")
                elif subcmd == "set_tz" and len(args) > 1:
                    tz = args[1]
                    self.settings["timezone"] = tz
                    self._save()
                    send_message(f"✅ Timezone set to: <b>{tz}</b>")
                elif subcmd == "set_style" and len(args) > 1:
                    style = args[1]
                    self.settings["digest_style"] = style
                    self._save()
                    send_message(f"✅ Digest style set to: <b>{style}</b>")
                else:
                    send_message("❌ Invalid /config syntax.")
            return True
            
        return False

    def handle_feedback(self, tag: str, weight: int):
        """Adjust weight of a tag based on likes/dislikes."""
        weights = self.settings.get("tag_weights", {})
        current = weights.get(tag, 0)
        weights[tag] = current + weight
        self.settings["tag_weights"] = weights
        self._save()
        # No message sent, usually a toast via answerCallbackQuery handles it.

    def _send_help(self):
        msg = (
            "🤖 <b>Helpzy — Configuration & Settings</b>\n\n"
            "Here are the available commands:\n\n"
            "<b>Tasks</b>\n"
            "<code>/todo [description]</code> — Add a new task (e.g. /todo Read docs by 5pm)\n"
            "<code>/list</code> — Show active tasks\n"
            "<code>/done [id]</code> — Mark a task as completed\n"
            "<code>/remove [id]</code> — Delete a task without archiving\n"
            "<code>/history</code> — Show recently completed tasks\n\n"
            "<b>Configuration</b>\n"
            "<code>/config</code> — Show current overrides\n"
            "<code>/config set_tz [timezone]</code> — Set timezone (e.g. Asia/Kolkata)\n"
            "<code>/config set_style [style]</code> — Set AI digest style\n"
        )
        send_message(msg)

    def _send_config(self):
        msg = "⚙️ <b>Current Settings Overrides</b>\n<pre>"
        msg += json.dumps(self.settings, indent=2)
        msg += "</pre>"
        send_message(msg)
