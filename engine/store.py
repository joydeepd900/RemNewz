import os
import json
from datetime import datetime, timezone
from engine.crypto import CryptoManager, DecryptionError

DATA_DIR = "data"
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive_todos.json")
TODOS_FILE_ENC = os.path.join(DATA_DIR, "todos.enc")
ARCHIVE_FILE_ENC = os.path.join(DATA_DIR, "archive_todos.enc")
MAX_ARCHIVE_ITEMS = 50

class TaskStore:
    def __init__(self, 
                 todos_path=TODOS_FILE, 
                 archive_path=ARCHIVE_FILE, 
                 todos_path_enc=TODOS_FILE_ENC, 
                 archive_path_enc=ARCHIVE_FILE_ENC):
        self.todos_path = todos_path
        self.archive_path = archive_path
        self.todos_path_enc = todos_path_enc
        self.archive_path_enc = archive_path_enc
        
        self.todos = []
        self.archive = []
        self.crypto = CryptoManager()
        self.load_failed = False
        self._load()

    def _load(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
        try:
            # Load active tasks
            if self.crypto.is_enabled and os.path.exists(self.todos_path_enc):
                with open(self.todos_path_enc, "rb") as f:
                    self.todos = self.crypto.decrypt_dict(f.read())
            elif os.path.exists(self.todos_path):
                try:
                    with open(self.todos_path, "r", encoding="utf-8") as f:
                        self.todos = json.load(f)
                except (json.JSONDecodeError, IOError):
                    self.todos = []
            
            # Load archive tasks
            if self.crypto.is_enabled and os.path.exists(self.archive_path_enc):
                with open(self.archive_path_enc, "rb") as f:
                    self.archive = self.crypto.decrypt_dict(f.read())
            elif os.path.exists(self.archive_path):
                try:
                    with open(self.archive_path, "r", encoding="utf-8") as f:
                        self.archive = json.load(f)
                except (json.JSONDecodeError, IOError):
                    self.archive = []
        except DecryptionError as e:
            self.load_failed = True
            print(f"[store] FATAL: {e}")
            raise

    def _atomic_write(self, file_path, data, is_binary=False):
        tmp_path = file_path + ".tmp"
        mode = "wb" if is_binary else "w"
        encoding = None if is_binary else "utf-8"
        
        with open(tmp_path, mode, encoding=encoding) as f:
            if is_binary:
                f.write(data)
            else:
                json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)

    def save(self):
        if self.load_failed:
            raise RuntimeError("TaskStore is in an invalid/unloaded state due to decryption failure. Writes are blocked to prevent data loss.")
            
        try:
            if self.crypto.is_enabled:
                todos_cipher = self.crypto.encrypt_dict(self.todos)
                archive_cipher = self.crypto.encrypt_dict(self.archive)
                
                self._atomic_write(self.todos_path_enc, todos_cipher, is_binary=True)
                self._atomic_write(self.archive_path_enc, archive_cipher, is_binary=True)
                
                # Verified Migration cleanup: only remove plaintext if we can decrypt back
                try:
                    self.crypto.decrypt_dict(todos_cipher)
                    self.crypto.decrypt_dict(archive_cipher)
                    
                    if os.path.exists(self.todos_path):
                        os.remove(self.todos_path)
                    if os.path.exists(self.archive_path):
                        os.remove(self.archive_path)
                except DecryptionError as e:
                    print(f"[store] Integrity check failed post-encryption. Retaining plaintext. ({e})")
            else:
                self._atomic_write(self.todos_path, self.todos, is_binary=False)
                self._atomic_write(self.archive_path, self.archive, is_binary=False)
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
