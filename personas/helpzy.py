import os
import json
from notifier.telegram import send_message
from engine.store import load_data, save_data
from engine.ai_client import normalize_topic_to_slug
from main_digest import run_digest

class Helpzy:
    """
    Helpzy acts as the configuration and settings manager persona.
    
    It handles commands related to sources (RSS/Topics), digest configurations,
    timezone settings, and displays help/status menus. State is persisted to the
    encrypted store by default.
    """
    def __init__(self, file_path: str = None, *args, **kwargs):
        self.file_path = file_path
        self.settings = {}
        self._load()

    def _load(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = {}
        else:
            self.settings = load_data("settings", {})

    def _save(self):
        if self.file_path:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=2)
            except Exception as e:
                print(f"[helpzy] Failed to save settings to {self.file_path}: {e}")
            return

        try:
            save_data("settings", self.settings)
        except Exception as e:
            print(f"[helpzy] Failed to save settings: {e}")

    def _get_workflow_edit_url(self, workflow_name: str = "commands.yml") -> str:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if repo:
            return f"https://github.com/{repo}/edit/main/.github/workflows/{workflow_name}"
        return f"https://github.com/YOUR_USERNAME/YOUR_REPO/edit/main/.github/workflows/{workflow_name}"

    def handle_command(self, text: str, message_thread_id: int = None, chat_id: str = None) -> bool:
        """
        Process incoming Telegram commands directed at the Helpzy persona.
        
        Evaluates commands like /help, /config, /source, /news, and /digest.
        Returns True if the command was recognized and handled, otherwise False.
        
        Args:
            text (str): The raw text of the incoming message.
            message_thread_id (int, optional): The forum thread ID, if applicable.
            chat_id (str, optional): The Telegram chat ID.
            
        Returns:
            bool: True if command was handled by Helpzy, False otherwise.
        """
        parts = text.strip().split()
        if not parts:
            return False
            
        cmd = parts[0].lower().split("@")[0]
        args = parts[1:]
        
        if cmd == "/help":
            self._send_help(message_thread_id, chat_id=chat_id)
            return True

        if cmd in ["/source", "/sources"]:
            self._handle_source_command(args, message_thread_id, chat_id)
            return True
            
        if cmd == "/digest":
            send_message("📰 Preparing your executive digest...", chat_id=chat_id, message_thread_id=message_thread_id)
            run_digest(chat_id=chat_id, message_thread_id=message_thread_id, mark_seen=True)
            return True
            
        if cmd == "/news":
            send_message("⚡ Fetching your instant news...", chat_id=chat_id, message_thread_id=message_thread_id)
            if args:
                query = " ".join(args)
                run_digest(chat_id=chat_id, message_thread_id=message_thread_id, max_items=3, mark_seen=False, query=query)
            else:
                run_digest(chat_id=chat_id, message_thread_id=message_thread_id, max_items=3, mark_seen=False)
            return True
            
        if cmd == "/config":
            if not args:
                self._send_config(message_thread_id, chat_id=chat_id)
            else:
                subcmd = args[0].lower()
                if subcmd in ["add_source", "add_feed"]:
                    self._handle_source_command(["add"] + args[1:], message_thread_id, chat_id)
                elif subcmd in ["remove_source", "remove_feed"]:
                    self._handle_source_command(["remove"] + args[1:], message_thread_id, chat_id)
                elif subcmd in ["sources", "feeds"]:
                    self._handle_source_command(["list"], message_thread_id, chat_id)
                elif subcmd in ["set_limit", "set_news_limit"] and len(args) > 1:
                    try:
                        limit = int(args[1])
                        if limit < 1 or limit > 15:
                            send_message("❌ Limit must be between 1 and 15.", chat_id=chat_id, message_thread_id=message_thread_id)
                        else:
                            self.settings["news_limit"] = limit
                            self._save()
                            send_message(f"✅ Digest news limit set to: <b>{limit}</b> items per digest.", chat_id=chat_id, message_thread_id=message_thread_id)
                    except ValueError:
                        send_message("❌ Limit must be a valid number.", chat_id=chat_id, message_thread_id=message_thread_id)
                elif subcmd in ["repo_mode", "mode"]:
                    self._send_repo_mode_info(message_thread_id, chat_id)
                elif subcmd == "add_topic" and len(args) > 1:
                    topic = " ".join(args[1:])
                    ai_provider = os.environ.get("AI_PROVIDER", "none")
                    ai_model = os.environ.get("AI_MODEL", "")
                    slug = normalize_topic_to_slug(topic, ai_provider, ai_model)
                    
                    topics = self.settings.get("topics", [])
                    if slug not in topics:
                        topics.append(slug)
                    self.settings["topics"] = topics
                    self._save()
                    send_message(f"✅ Added topic: <b>{topic}</b> (canonical slug: <code>{slug}</code>)", chat_id=chat_id, message_thread_id=message_thread_id)
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

    def _handle_source_command(self, args: list, message_thread_id: int = None, chat_id: str = None):
        """
        Execute sub-commands related to RSS feeds and GitHub topics management.
        
        Provides functionality to list, add, or remove custom news sources.
        
        Args:
            args (list): List of arguments following the base command.
            message_thread_id (int, optional): The forum thread ID.
            chat_id (str, optional): The Telegram chat ID.
        """
        feeds = list(self.settings.get("rss_feeds", []))
        
        if not args or args[0].lower() in ["list", "show"]:
            # List current sources
            topics = self.settings.get("topics", [])
            lines = ["📡 <b>Active News Sources</b>\n"]
            
            lines.append("<b>RSS & News Feeds:</b>")
            if feeds:
                for idx, feed in enumerate(feeds, start=1):
                    label = feed.get("label", "Feed")
                    url = feed.get("url", "")
                    lines.append(f"  {idx}. <b>{label}</b>\n     <code>{url}</code>")
            else:
                lines.append("  <i>No custom RSS feeds configured. Using default template feeds.</i>")
                
            lines.append("\n<b>GitHub Topics:</b>")
            if topics:
                for topic in topics:
                    lines.append(f"  • <code>{topic}</code>")
            else:
                lines.append("  <i>Using default topics from config template.</i>")
                
            lines.append("\n<b>Commands:</b>")
            lines.append("• <code>/source add &lt;url&gt; [label]</code> — Add RSS source")
            lines.append("• <code>/source remove &lt;num or url&gt;</code> — Remove RSS source")
            lines.append("• <code>/config add_topic &lt;topic&gt;</code> — Add GitHub topic")
            lines.append("• <code>/config remove_topic &lt;topic&gt;</code> — Remove GitHub topic")
            
            send_message("\n".join(lines), chat_id=chat_id, message_thread_id=message_thread_id)
            return

        subcmd = args[0].lower()
        if subcmd == "add":
            if len(args) < 2:
                send_message("❌ Usage: <code>/source add &lt;url&gt; [label]</code>", chat_id=chat_id, message_thread_id=message_thread_id)
                return
            url = args[1].strip()
            if not url.startswith(("http://", "https://")):
                send_message("❌ Source URL must start with <code>http://</code> or <code>https://</code>.", chat_id=chat_id, message_thread_id=message_thread_id)
                return
            
            # Label
            if len(args) > 2:
                label = " ".join(args[2:]).strip()
            else:
                # Infer label from domain
                try:
                    domain = url.split("/")[2].replace("www.", "")
                    label = domain.split(".")[0].capitalize()
                except Exception:
                    label = "RSS Feed"
                    
            # Check duplicates
            for f in feeds:
                if f.get("url") == url:
                    send_message(f"⚠️ Source already exists as <b>{f.get('label')}</b>.", chat_id=chat_id, message_thread_id=message_thread_id)
                    return

            feeds.append({"url": url, "label": label})
            self.settings["rss_feeds"] = feeds
            self._save()
            send_message(f"✅ Added RSS source: <b>{label}</b>\n<code>{url}</code>", chat_id=chat_id, message_thread_id=message_thread_id)

        elif subcmd == "remove":
            if len(args) < 2:
                send_message("❌ Usage: <code>/source remove &lt;number or url&gt;</code>", chat_id=chat_id, message_thread_id=message_thread_id)
                return
            target = args[1].strip()
            removed_label = None

            # Try removing by index first
            if target.isdigit():
                idx = int(target) - 1
                if 0 <= idx < len(feeds):
                    removed = feeds.pop(idx)
                    removed_label = removed.get("label", removed.get("url"))
            else:
                # Match by URL or label
                new_feeds = []
                removed = False
                for f in feeds:
                    if not removed and (f.get("url") == target or f.get("label", "").lower() == target.lower()):
                        removed_label = f.get("label", f.get("url"))
                        removed = True
                    else:
                        new_feeds.append(f)
                feeds = new_feeds

            if removed_label:
                self.settings["rss_feeds"] = feeds
                self._save()
                send_message(f"✅ Removed source: <b>{removed_label}</b>", chat_id=chat_id, message_thread_id=message_thread_id)
            else:
                send_message(f"❌ Could not find source matching <code>{target}</code>. Use <code>/source</code> to view list.", chat_id=chat_id, message_thread_id=message_thread_id)

        else:
            send_message("❌ Unknown /source action. Use <code>/source</code>, <code>/source add &lt;url&gt;</code>, or <code>/source remove &lt;num&gt;</code>.", chat_id=chat_id, message_thread_id=message_thread_id)

    def _send_repo_mode_info(self, message_thread_id: int = None, chat_id: str = None):
        """
        Explain the operational differences between Public and Private GitHub repositories.
        
        Provides context on GitHub Actions polling quotas and generates a direct link
        for the user to edit their schedule in `commands.yml`.
        
        Args:
            message_thread_id (int, optional): The forum thread ID.
            chat_id (str, optional): The Telegram chat ID.
        """
        edit_url = self._get_workflow_edit_url("commands.yml")
        msg = (
            "⚙️ <b>Repository Mode & Polling Schedule</b>\n\n"
            "RemNewz runs via GitHub Actions:\n\n"
            "• <b>Public Repositories:</b> Free unlimited Actions minutes. Polling can run every 5 minutes (<code>*/5 * * * *</code>). "
            "<i>(Ensure ENCRYPTION_KEY is set in GitHub Secrets to keep your tasks private!)</i>\n\n"
            "• <b>Private Repositories:</b> Free tier is capped at 2,000 minutes/month. Running every 5 minutes will exhaust quota in ~7 days! "
            "Change schedule to <b>every 35 minutes</b> (<code>0,35 * * * *</code>), or deploy the free Cloudflare Worker for instant webhook replies.\n\n"
            f"🔗 <b><a href=\"{edit_url}\">Click here to edit commands.yml on GitHub</a></b>\n"
            "You can change the cron schedule and commit directly in your browser."
        )
        send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)

    def handle_feedback(self, data: str, weight: int):
        """
        Adjust the priority weight of a specific topic based on user feedback.
        
        Parses callback data formatted as 'like_<topic>' or 'dislike_<topic>' and
        updates the stored tag weights accordingly to tune future AI filtering.
        
        Args:
            data (str): The raw callback string payload from Telegram.
            weight (int): The numerical adjustment to apply (+1 or -1).
        """
        parts = data.split("_", 1)
        if len(parts) < 2:
            return
            
        topic = parts[1]
        weights = self.settings.get("tag_weights", {})
        current = weights.get(topic, 0)
        weights[topic] = current + weight
        self.settings["tag_weights"] = weights
        self._save()

    def _send_help(self, message_thread_id: int = None, chat_id: str = None):
        msg = (
            "🤖 <b>Helpzy — Configuration & Settings</b>\n\n"
            "Here are the available commands:\n\n"
            "<b>Tasks</b>\n"
            "<code>/todo [description]</code> — Add a new task (e.g. /todo Read docs by 5pm)\n"
            "<code>/list</code> — Show active tasks\n"
            "<code>/done [id]</code> — Mark a task as completed\n"
            "<code>/remove [id]</code> — Delete a task without archiving\n"
            "<code>/history</code> — Show recently completed tasks\n"
            "<code>/search &lt;query&gt;</code> — Search active & archived tasks\n"
            "<code>/stats</code> — Productivity & task completion analytics\n\n"
            "<b>News & Sources</b>\n"
            "<code>/source</code> — List all active news sources & topics\n"
            "<code>/source add &lt;url&gt; [label]</code> — Add RSS/Atom feed source\n"
            "<code>/source remove &lt;num or url&gt;</code> — Remove news source\n\n"
            "<b>Configuration</b>\n"
            "<code>/config</code> — Show current settings\n"
            "<code>/config set_limit [1-15]</code> — Max news items per digest\n"
            "<code>/config add_topic [topic]</code> — Add GitHub trending topic\n"
            "<code>/config remove_topic [topic]</code> — Remove GitHub topic\n"
            "<code>/config set_tz [timezone]</code> — Set timezone (e.g. Asia/Kolkata)\n"
            "<code>/config set_style [style]</code> — Set AI digest style (concise, technical...)\n"
            "<code>/config repo_mode</code> — Public vs Private guide & direct cron edit link\n"
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

