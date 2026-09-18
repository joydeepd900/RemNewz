import os
import json
from notifier.telegram import send_message
from engine.store import load_data, save_data

class Helpzy:
    def __init__(self):
        self.settings = {}
        self._load()

    def _load(self):
        self.settings = load_data("settings", {})

    def _save(self):
        try:
            save_data("settings", self.settings)
        except Exception as e:
            print(f"[helpzy] Failed to save settings: {e}")

    def handle_command(self, text: str, message_thread_id: int = None, chat_id: str = None) -> bool:
        """Process a Helpzy command. Returns True if handled."""
        parts = text.strip().split()
        if not parts:
            return False
            
        cmd = parts[0].lower().split("@")[0]
        args = parts[1:]
        
        if cmd == "/help":
            self._send_help(message_thread_id, chat_id=chat_id)
            return True
            
        if cmd == "/config":
            if not args:
                self._send_config(message_thread_id, chat_id=chat_id)
            else:
                subcmd = args[0].lower()
                if subcmd == "add_topic" and len(args) > 1:
                    topic = " ".join(args[1:])
                    topics = self.settings.get("topics", [])
                    if topic not in topics:
                        topics.append(topic)
                    self.settings["topics"] = topics
                    self._save()
                    send_message(f"✅ Added topic: <b>{topic}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "remove_topic" and len(args) > 1:
                    topic = " ".join(args[1:])
                    topics = self.settings.get("topics", [])
                    if topic in topics:
                        topics.remove(topic)
                    self.settings["topics"] = topics
                    self._save()
                    send_message(f"✅ Removed topic: <b>{topic}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "set_tz" and len(args) > 1:
                    tz = args[1]
                    self.settings["timezone"] = tz
                    self._save()
                    send_message(f"✅ Timezone set to: <b>{tz}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "set_style" and len(args) > 1:
                    style = args[1]
                    self.settings["digest_style"] = style
                    self._save()
                    send_message(f"✅ Digest style set to: <b>{style}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "bind_news":
                    if message_thread_id is not None:
                        self.settings["topic_news"] = message_thread_id
                        if chat_id:
                            self.settings["supergroup_id"] = chat_id
                        self._save()
                        send_message("✅ Bound News digests to this topic.", chat_id=chat_id, message_thread_id=message_thread_id)
                    else:
                        send_message("❌ Cannot bind: this is not a topic thread.", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "bind_tasks":
                    if message_thread_id is not None:
                        self.settings["topic_tasks"] = message_thread_id
                        if chat_id:
                            self.settings["supergroup_id"] = chat_id
                        self._save()
                        send_message("✅ Bound Task alerts to this topic.", chat_id=chat_id, message_thread_id=message_thread_id)
                    else:
                        send_message("❌ Cannot bind: this is not a topic thread.", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "set_topic_news" and len(args) > 1:
                    try:
                        topic_id = int(args[1])
                        self.settings["topic_news"] = topic_id
                        if chat_id:
                            self.settings["supergroup_id"] = chat_id
                        self._save()
                        send_message(f"✅ Set News topic to: <b>{topic_id}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                    except ValueError:
                        send_message("❌ Topic ID must be an integer.", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "set_topic_tasks" and len(args) > 1:
                    try:
                        topic_id = int(args[1])
                        self.settings["topic_tasks"] = topic_id
                        if chat_id:
                            self.settings["supergroup_id"] = chat_id
                        self._save()
                        send_message(f"✅ Set Tasks topic to: <b>{topic_id}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
                    except ValueError:
                        send_message("❌ Topic ID must be an integer.", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd == "clear_topics":
                    self.settings.pop("topic_news", None)
                    self.settings.pop("topic_tasks", None)
                    self.settings.pop("supergroup_id", None)
                    self._save()
                    send_message("✅ Cleared topic bindings.", chat_id=chat_id, message_thread_id=message_thread_id)
                else:
                    send_message("❌ Invalid /config syntax.", chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        return False

    def handle_feedback(self, data: str, weight: int):
        """Adjust weight of a topic based on likes/dislikes. Data is like_<topic> or dislike_<topic>."""
        parts = data.split("_", 1)
        if len(parts) < 2:
            return
            
        topic = parts[1]
        weights = self.settings.get("tag_weights", {})
        current = weights.get(topic, 0)
        weights[topic] = current + weight
        self.settings["tag_weights"] = weights
        self._save()
        # No message sent, usually a toast via answerCallbackQuery handles it.

    def _send_help(self, message_thread_id: int = None, chat_id: str = None):
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
            "<code>/config bind_news</code> — Route news to current topic (Supergroups)\n"
            "<code>/config bind_tasks</code> — Route task alerts to current topic (Supergroups)\n"
            "<code>/config clear_topics</code> — Reset topic routing\n"
        )
        send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)

    def _send_config(self, message_thread_id: int = None, chat_id: str = None):
        msg = "⚙️ <b>Current Settings Overrides</b>\n<pre>"
        msg += json.dumps(self.settings, indent=2)
        msg += "</pre>"
        send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)

