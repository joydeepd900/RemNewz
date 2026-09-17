import os
import json
from datetime import datetime, timezone

DATA_DIR = "data"
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive_todos.json")
MAX_ARCHIVE_ITEMS = 50

class TaskStore:
    def __init__(self, todos_path=TODOS_FILE, archive_path=ARCHIVE_FILE):
        self.todos_path = todos_path
        self.archive_path = archive_path
        
        self.todos = []
        self.archive = []
        self._load()

    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
        if os.path.exists(self.todos_path):
            try:
                with open(self.todos_path, "r", encoding="utf-8") as f:
                    self.todos = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.todos = []
                
        if os.path.exists(self.archive_path):
            try:
                with open(self.archive_path, "r", encoding="utf-8") as f:
                    self.archive = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.archive = []

    def save(self):
        try:
            with open(self.todos_path, "w", encoding="utf-8") as f:
                json.dump(self.todos, f, indent=2)
            with open(self.archive_path, "w", encoding="utf-8") as f:
                json.dump(self.archive, f, indent=2)
        except IOError as e:
            print(f"[store] Failed to save tasks: {e}")

    def get_task(self, task_id: str):
        for t in self.todos:
            if t.get("id") == task_id:
                return t
        return None

    def update_task(self, updated_task: dict):
        for i, t in enumerate(self.todos):
            if t.get("id") == updated_task.get("id"):
                self.todos[i] = updated_task
                self.save()
                return True
        return False

    def add_task(self, task: dict):
        self.todos.append(task)
        self.save()

    def archive_task(self, task_id: str):
        task = None
        for i, t in enumerate(self.todos):
            if t.get("id") == task_id:
                task = self.todos.pop(i)
                break
                
        if task:
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.archive.insert(0, task) # Add to front
            
            if len(self.archive) > MAX_ARCHIVE_ITEMS:
                self.archive = self.archive[:MAX_ARCHIVE_ITEMS]
                
            self.save()
            return True
        return False
