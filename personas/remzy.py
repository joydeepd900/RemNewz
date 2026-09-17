from datetime import datetime, timezone, timedelta
from engine.store import TaskStore
from engine.time_utils import format_datetime
from notifier.telegram import send_message

class Remzy:
    def __init__(self):
        self.store = TaskStore()

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

            # Check if task is due or past due
            if now_utc >= due_at:
                reminded_due = task.get("reminded_due", False)
                
                if not reminded_due:
                    # Trigger due notification (exact once)
                    self._send_due_alert(task, due_at)
                    task["reminded_due"] = True
                    dirty = True
                else:
                    # Task is overdue. Check anti-spam guardrail (1 nudge per 24h)
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
        """Send exactly one notification when a task becomes due."""
        title = task.get("title", "Unnamed Task")
        formatted_time = format_datetime(due_at, style="short")
        
        msg = (
            f"🔔 <b>Task Due!</b>\n\n"
            f"<b>{title}</b>\n"
            f"<i>Due at: {formatted_time}</i>\n\n"
            f"Reply with <code>/done {task.get('id')}</code> to complete."
        )
        send_message(msg)

    def _send_overdue_alert(self, task, due_at):
        """Send a polite nudge for overdue tasks."""
        title = task.get("title", "Unnamed Task")
        formatted_time = format_datetime(due_at, style="relative")
        
        msg = (
            f"⚠️ <b>Overdue Reminder</b>\n\n"
            f"<b>{title}</b>\n"
            f"<i>Was due {formatted_time}</i>\n\n"
            f"Reply with <code>/done {task.get('id')}</code> to complete."
        )
        send_message(msg)
