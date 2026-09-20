import uuid
import html
from datetime import datetime, timezone, timedelta
from engine.store import TaskStore
from engine.time_utils import format_datetime
from engine.ai_client import parse_task_nlp
from notifier.telegram import send_message, resolve_topic_id, resolve_supergroup_id

class Remzy:
    def __init__(self):
        self.store = TaskStore()

    def handle_command(self, text: str, provider: str, model: str, user_tz: str, message_thread_id: int = None, chat_id: str = None) -> bool:
        """Process a Remzy command. Returns True if handled."""
        parts = text.strip().split()
        if not parts:
            return False
            
        cmd = parts[0].lower().split("@")[0]
        args = text[len(parts[0]):].strip()
        
        if cmd == "/todo":
            if not args:
                send_message("❌ Please provide a task description. (e.g. /todo Read docs by 5pm)", chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            send_message("⏳ <i>Parsing task...</i>", chat_id=chat_id, message_thread_id=message_thread_id)
            task_data = parse_task_nlp(args, provider, model, user_tz)
            
            task = {
                "id": str(uuid.uuid4())[:8],
                "title": task_data.get("title", args),
                "due_at": task_data.get("due_at"),
                "priority": task_data.get("priority", "normal"),
                "reminded_due": False,
                "origin_thread_id": message_thread_id,
                "origin_chat_id": chat_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.store.add_task(task)
            
            formatted_due = "No deadline"
            if task["due_at"]:
                formatted_due = format_datetime(datetime.fromisoformat(task["due_at"]), style="short")
                
            safe_title = html.escape(task['title'])
            send_message(f"✅ <b>Task Created:</b> {safe_title}\n📅 Due: {formatted_due}\n🆔 <code>{task['id']}</code>", chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/list":
            if not self.store.todos:
                send_message("📭 No active tasks.", chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            msg = "📋 <b>Active Tasks</b>\n\n"
            for t in self.store.todos:
                formatted_due = format_datetime(datetime.fromisoformat(t["due_at"]), style="short") if t.get("due_at") else "No deadline"
                safe_title = html.escape(t['title'])
                msg += f"• <b>{safe_title}</b>\n  └ <i>{formatted_due}</i> (<code>/done {t['id']}</code>)\n"
            send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/done":
            if not args:
                send_message("❌ Provide task ID (e.g. /done abc1234)", chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            task_id = args.split()[0]
            if self.store.archive_task(task_id):
                send_message(f"✅ Task <code>{task_id}</code> marked as done and archived.", chat_id=chat_id, message_thread_id=message_thread_id)
            else:
                send_message(f"❌ Task <code>{task_id}</code> not found.", chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/remove":
            if not args:
                send_message("❌ Provide task ID (e.g. /remove abc1234)", chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            task_id = args.split()[0]
            if self.store.delete_task(task_id):
                send_message(f"🗑️ Task <code>{task_id}</code> deleted permanently.", chat_id=chat_id, message_thread_id=message_thread_id)
            else:
                send_message(f"❌ Task <code>{task_id}</code> not found.", chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/history":
            if not self.store.archive:
                send_message("📭 Archive is empty.", chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            msg = "📜 <b>Recently Completed (Last 10)</b>\n\n"
            for t in self.store.archive[:10]:
                completed = format_datetime(datetime.fromisoformat(t["completed_at"]), style="short")
                safe_title = html.escape(t['title'])
                msg += f"• <s>{safe_title}</s> (<i>{completed}</i>)\n"
            send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/search":
            if not args:
                msg = (
                    "🔍 <b>Task Search</b>\n\n"
                    "Usage: <code>/search &lt;query&gt;</code>\n"
                    "Example: <code>/search meeting</code> or <code>/search abc1234</code>\n\n"
                    "<i>Searches across all active and completed tasks.</i>"
                )
                send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            results = self.store.search_tasks(args, limit=15)
            if not results:
                safe_query = html.escape(args)
                msg = f"🔍 <b>Task Search</b>\n\nNo tasks found matching \"<b>{safe_query}</b>\".\n\n💡 <i>Try searching with a partial keyword or use <code>/list</code>.</i>"
                send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            active_matches = [t for t in results if t.get("status") == "active"]
            archived_matches = [t for t in results if t.get("status") == "archived"]
            
            safe_query = html.escape(args)
            msg = f"🔍 <b>Search Results for \"<i>{safe_query}</i>\"</b>\n\n"
            
            if active_matches:
                msg += "📋 <b>Active Tasks</b>\n"
                for t in active_matches:
                    formatted_due = format_datetime(datetime.fromisoformat(t["due_at"]), style="short") if t.get("due_at") else "No deadline"
                    safe_title = html.escape(t['title'])
                    msg += f"• <b>{safe_title}</b>\n  └ 📅 <i>{formatted_due}</i> • 🆔 <code>{t['id']}</code> (<code>/done {t['id']}</code>)\n"
                msg += "\n"
                
            if archived_matches:
                msg += "📜 <b>Completed Tasks</b>\n"
                for t in archived_matches:
                    completed = format_datetime(datetime.fromisoformat(t["completed_at"]), style="short") if t.get("completed_at") else "Unknown"
                    safe_title = html.escape(t['title'])
                    msg += f"• <s>{safe_title}</s>\n  └ ✅ <i>{completed}</i> • 🆔 <code>{t['id']}</code>\n"
                    
            if len(results) == 15:
                msg += "\n<i>...and possibly more results. Narrow your search query to see them.</i>"
                
            send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
            return True
            
        if cmd == "/stats":
            stats = self.store.get_stats()
            if stats["total_tasks"] == 0:
                msg = (
                    "📊 <b>Remzy Productivity Analytics</b>\n\n"
                    "📭 No tasks recorded yet!\n"
                    "Start adding tasks with <code>/todo &lt;description&gt;</code> to unlock productivity analytics."
                )
                send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
                return True
                
            pct = stats["completion_rate_pct"]
            filled = min(10, max(0, round(pct / 10)))
            progress_bar = "🟩" * filled + "⬜" * (10 - filled)
            
            comp_rate_str = f"{stats['deadline_compliance']['rate_pct']}% on-time" if stats['deadline_compliance']['rate_pct'] is not None else "<i>No deadlines set</i>"
            overdue_icon = "⚠️" if stats["overdue_count"] > 0 else "✅"
            overdue_hint = " <i>(Use /list to tackle them)</i>" if stats["overdue_count"] > 0 else ""
            
            msg = (
                "📊 <b>Remzy Productivity Analytics</b>\n"
                "<i>Your task health, velocity & completion metrics</i>\n\n"
                "📈 <b>Velocity & Output</b>\n"
                f"• <b>This Week (7d):</b> <b>{stats['completed_7d']}</b> tasks completed\n"
                f"• <b>This Month (30d):</b> <b>{stats['completed_30d']}</b> tasks completed\n"
                f"• <b>Weekly Pace:</b> ~{stats['daily_velocity']:.1f} tasks/day\n\n"
                "🎯 <b>Completion & Compliance</b>\n"
                f"• <b>Active Backlog:</b> {stats['active_count']} pending\n"
                f"• <b>Retained History:</b> {stats['archived_count']} completed tasks\n"
                f"• <b>All-Time Progress:</b> [{progress_bar}] {pct}%\n"
                f"• <b>Deadline Compliance:</b> {comp_rate_str}\n\n"
                "⏰ <b>Deadline Health</b>\n"
                f"• {overdue_icon} <b>Overdue Now:</b> {stats['overdue_count']}{overdue_hint}\n"
                f"• ⏳ <b>Due in 24h:</b> {stats['due_today_count']}\n"
                f"• 📅 <b>Upcoming (Later):</b> {stats['upcoming_count']}\n"
                f"• ⚪ <b>No Deadline:</b> {stats['no_deadline_count']}\n"
            )
            
            send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)
            return True

        return False

    def handle_remind_me(self, callback_data: str, message_thread_id: int = None, chat_id: str = None):
        """Create a task from a Remind Me button."""
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": "Review News Item",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "priority": "normal",
            "reminded_due": False,
            "origin_thread_id": message_thread_id,
            "origin_chat_id": chat_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.store.add_task(task)
        send_message(f"📌 Task Created: <b>Review News Item</b>\n📅 Due: Tomorrow\n🆔 <code>{task['id']}</code>", chat_id=chat_id, message_thread_id=message_thread_id)
        
    def check_deadlines(self):
        """Evaluate task deadlines and send due/overdue notifications."""
        now_utc = datetime.now(timezone.utc)
        dirty = False
        
        tasks_topic_id = resolve_topic_id('tasks')
        supergroup_id = resolve_supergroup_id()
        
        for task in self.store.todos:
            due_at_str = task.get("due_at")
            if not due_at_str:
                continue
                
            try:
                due_at = datetime.fromisoformat(due_at_str)
            except ValueError:
                continue

            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)

            if now_utc >= due_at:
                reminded_due = task.get("reminded_due", False)
                
                if tasks_topic_id is not None:
                    target_chat = supergroup_id
                    thread_id = tasks_topic_id
                else:
                    target_chat = task.get("origin_chat_id")
                    thread_id = task.get("origin_thread_id")

                if not reminded_due:
                    self._send_due_alert(task, due_at, chat_id=target_chat, message_thread_id=thread_id)
                    task["reminded_due"] = True
                    # Initialize the nudge timer so we don't spam 5 minutes later
                    task["last_overdue_nudge"] = now_utc.isoformat()
                    dirty = True
                else:
                    last_nudge_str = task.get("last_overdue_nudge")
                    if last_nudge_str:
                        try:
                            last_nudge = datetime.fromisoformat(last_nudge_str)
                            if last_nudge.tzinfo is None:
                                last_nudge = last_nudge.replace(tzinfo=timezone.utc)
                            time_since_nudge = now_utc - last_nudge
                            needs_nudge = time_since_nudge >= timedelta(hours=24)
                        except (ValueError, TypeError):
                            needs_nudge = True
                    else:
                        needs_nudge = True

                    if needs_nudge:
                        self._send_overdue_alert(task, due_at, chat_id=target_chat, message_thread_id=thread_id)
                        task["last_overdue_nudge"] = now_utc.isoformat()
                        dirty = True
                        
        if dirty:
            self.store.save()

    def _send_due_alert(self, task, due_at, chat_id=None, message_thread_id=None):
        title = html.escape(task.get("title", "Unnamed Task"))
        formatted_time = format_datetime(due_at, style="short")
        msg = f"🔔 <b>Task Due!</b>\n\n<b>{title}</b>\n<i>Due at: {formatted_time}</i>\n\nReply with <code>/done {task.get('id')}</code> to complete."
        send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)

    def _send_overdue_alert(self, task, due_at, chat_id=None, message_thread_id=None):
        title = html.escape(task.get("title", "Unnamed Task"))
        formatted_time = format_datetime(due_at, style="relative")
        msg = f"⚠️ <b>Overdue Reminder</b>\n\n<b>{title}</b>\n<i>Was due {formatted_time}</i>\n\nReply with <code>/done {task.get('id')}</code> to complete."
        send_message(msg, chat_id=chat_id, message_thread_id=message_thread_id)

