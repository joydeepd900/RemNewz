import uuid
from datetime import datetime, timezone, timedelta
from engine.store import TaskStore
from engine.time_utils import format_datetime
from engine.ai_client import parse_task_nlp
from notifier.telegram import send_message

class Remzy:
    def __init__(self):
        self.store = TaskStore()

    def handle_command(self, text: str, provider: str, model: str, user_tz: str) -> bool:
        """Process a Remzy command. Returns True if handled."""
        parts = text.strip().split()
        if not parts:
            return False
            
        cmd = parts[0].lower()
        args = text[len(cmd):].strip()
        
        if cmd == "/todo":
            if not args:
                send_message("❌ Please provide a task description. (e.g. /todo Read docs by 5pm)")
                return True
                
            send_message("⏳ <i>Parsing task...</i>")
            task_data = parse_task_nlp(args, provider, model, user_tz)
            
            task = {
                "id": str(uuid.uuid4())[:8],
                "title": task_data.get("title", args),
                "due_at": task_data.get("due_at"),
                "priority": task_data.get("priority", "normal"),
                "reminded_due": False
            }
            self.store.add_task(task)
            
            formatted_due = "No deadline"
            if task["due_at"]:
                formatted_due = format_datetime(datetime.fromisoformat(task["due_at"]), style="short")
                
            send_message(f"✅ <b>Task Created:</b> {task['title']}\n📅 Due: {formatted_due}\n🆔 <code>{task['id']}</code>")
            return True
            
        if cmd == "/list":
            if not self.store.todos:
                send_message("📭 No active tasks.")
                return True
                
            msg = "📋 <b>Active Tasks</b>\n\n"
            for t in self.store.todos:
                formatted_due = format_datetime(datetime.fromisoformat(t["due_at"]), style="short") if t.get("due_at") else "No deadline"
                msg += f"• <b>{t['title']}</b>\n  └ <i>{formatted_due}</i> (<code>/done {t['id']}</code>)\n"
            send_message(msg)
            return True
            
        if cmd == "/done":
            if not args:
                send_message("❌ Provide task ID (e.g. /done abc1234)")
                return True
                
            task_id = args.split()[0]
            if self.store.archive_task(task_id):
                send_message(f"✅ Task <code>{task_id}</code> marked as done and archived.")
            else:
                send_message(f"❌ Task <code>{task_id}</code> not found.")
            return True
            
        if cmd == "/remove":
            if not args:
                send_message("❌ Provide task ID (e.g. /remove abc1234)")
                return True
                
            task_id = args.split()[0]
            # Just delete it without archiving
            for i, t in enumerate(self.store.todos):
                if t.get("id") == task_id:
                    self.store.todos.pop(i)
                    self.store.save()
                    send_message(f"🗑️ Task <code>{task_id}</code> deleted permanently.")
                    return True
            send_message(f"❌ Task <code>{task_id}</code> not found.")
            return True
            
        if cmd == "/history":
            if not self.store.archive:
                send_message("📭 Archive is empty.")
                return True
                
            msg = "📜 <b>Recently Completed (Last 10)</b>\n\n"
            for t in self.store.archive[:10]:
                completed = format_datetime(datetime.fromisoformat(t["completed_at"]), style="short")
                msg += f"• <s>{t['title']}</s> (<i>{completed}</i>)\n"
            send_message(msg)
            return True
            
        return False

    def handle_remind_me(self, callback_data: str):
        """Create a task from a Remind Me button."""
        # For Phase 3, we just create a generic reminder since we used placeholder callback_data
        # We can enhance this if we pass the URL in the callback.
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": "Review News Item",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "priority": "normal",
            "reminded_due": False
        }
        self.store.add_task(task)
        send_message(f"📌 Task Created: <b>Review News Item</b>\n📅 Due: Tomorrow\n🆔 <code>{task['id']}</code>")
        
    def check_deadlines(self):
        """Evaluate task deadlines and send due/overdue notifications."""
        now_utc = datetime.now(timezone.utc)
        dirty = False
        
        for task in self.store.todos:
            due_at_str = task.get("due_at")
            if not due_at_str:
                continue
                
            try:
                due_at = datetime.fromisoformat(due_at_str)
            except ValueError:
                continue

            if now_utc >= due_at:
                reminded_due = task.get("reminded_due", False)
                
                if not reminded_due:
                    self._send_due_alert(task, due_at)
                    task["reminded_due"] = True
                    # Initialize the nudge timer so we don't spam 5 minutes later
                    task["last_overdue_nudge"] = now_utc.isoformat()
                    dirty = True
                else:
                    last_nudge_str = task.get("last_overdue_nudge")
                    if last_nudge_str:
                        try:
                            last_nudge = datetime.fromisoformat(last_nudge_str)
                            time_since_nudge = now_utc - last_nudge
                            needs_nudge = time_since_nudge >= timedelta(hours=24)
                        except ValueError:
                            needs_nudge = True
                    else:
                        needs_nudge = True

                    if needs_nudge:
                        self._send_overdue_alert(task, due_at)
                        task["last_overdue_nudge"] = now_utc.isoformat()
                        dirty = True
                        
        if dirty:
            self.store.save()

    def _send_due_alert(self, task, due_at):
        title = task.get("title", "Unnamed Task")
        formatted_time = format_datetime(due_at, style="short")
        msg = f"🔔 <b>Task Due!</b>\n\n<b>{title}</b>\n<i>Due at: {formatted_time}</i>\n\nReply with <code>/done {task.get('id')}</code> to complete."
        send_message(msg)

    def _send_overdue_alert(self, task, due_at):
        title = task.get("title", "Unnamed Task")
        formatted_time = format_datetime(due_at, style="relative")
        msg = f"⚠️ <b>Overdue Reminder</b>\n\n<b>{title}</b>\n<i>Was due {formatted_time}</i>\n\nReply with <code>/done {task.get('id')}</code> to complete."
        send_message(msg)
