import os
import json
import atexit
import sqlite3
from datetime import datetime, timezone
from engine.crypto import CryptoManager, DecryptionError

DATA_DIR = "data"
DB_FILE_ENC = os.path.join(DATA_DIR, "remnewz.db.enc")
DB_FILE = os.path.join(DATA_DIR, "remnewz.db")
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive_todos.json")
TODOS_FILE_ENC = os.path.join(DATA_DIR, "todos.enc")
ARCHIVE_FILE_ENC = os.path.join(DATA_DIR, "archive_todos.enc")
MAX_ARCHIVE_ITEMS = 50

# Global Connection
_conn = None

def _atomic_write_file(file_path, data, is_binary=False):
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

def init_db(db_path=DB_FILE):
    """Decrypts DB (if exists) and initializes SQLite connection."""
    global _conn
    if _conn is not None:
        return _conn
        
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        
    crypto = CryptoManager()
    
    # 1. Decrypt Database to Disk if encrypted version exists and target is default
    if db_path == DB_FILE and crypto.is_enabled and os.path.exists(DB_FILE_ENC):
        try:
            with open(DB_FILE_ENC, "rb") as f:
                cipher_data = f.read()
            plain_data = crypto.decrypt_bytes(cipher_data)
            with open(DB_FILE, "wb") as f:
                f.write(plain_data)
        except DecryptionError as e:
            print(f"[store] FATAL decrypting remnewz.db.enc: {e}")
            raise
    
    # 2. Connect
    _conn = sqlite3.connect(db_path)
    _conn.row_factory = sqlite3.Row
    
    # 3. Create Tables
    with _conn:
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value JSON
            )
        """)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT,
                data JSON,
                completed_at TEXT
            )
        """)
        
    # 4. Migrate old JSON/ENC files if they exist (one-time)
    if db_path == DB_FILE:
        _migrate_legacy_files(crypto, _conn)

    return _conn

def _migrate_kv_files(crypto, conn):
    for key in ["settings", "seen", "last_update_id"]:
        path_enc = os.path.join(DATA_DIR, f"{key}.enc")
        path_json = os.path.join(DATA_DIR, f"{key}.json")
        data = None
        if os.path.exists(path_enc) and crypto.is_enabled:
            try:
                with open(path_enc, "rb") as f:
                    data = crypto.decrypt_dict(f.read())
                os.remove(path_enc)
            except Exception as e:
                print(f"[store] Migration failed for {key}.enc: {e}")
        elif os.path.exists(path_json):
            try:
                with open(path_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                os.remove(path_json)
            except Exception as e:
                print(f"[store] Migration failed for {key}.json: {e}")
        if data is not None:
            with conn:
                conn.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                             (key, json.dumps(data)))

def _migrate_task_files(crypto, conn):
    todos_enc = os.path.join(DATA_DIR, "todos.enc")
    archive_enc = os.path.join(DATA_DIR, "archive_todos.enc")
    
    if os.path.exists(todos_enc) and crypto.is_enabled:
        try:
            with open(todos_enc, "rb") as f:
                todos = crypto.decrypt_dict(f.read())
            with conn:
                for t in todos:
                    conn.execute("INSERT OR REPLACE INTO tasks (id, status, data, completed_at) VALUES (?, ?, ?, ?)",
                                 (t.get("id"), "active", json.dumps(t), None))
            os.remove(todos_enc)
        except Exception as e:
            print(f"[store] Migration failed for todos.enc: {e}")

    if os.path.exists(archive_enc) and crypto.is_enabled:
        try:
            with open(archive_enc, "rb") as f:
                archive = crypto.decrypt_dict(f.read())
            with conn:
                for t in archive:
                    conn.execute("INSERT OR REPLACE INTO tasks (id, status, data, completed_at) VALUES (?, ?, ?, ?)",
                                 (t.get("id"), "archived", json.dumps(t), t.get("completed_at")))
            os.remove(archive_enc)
        except Exception as e:
            print(f"[store] Migration failed for archive_todos.enc: {e}")

def _migrate_legacy_files(crypto, conn):
    """Detects legacy .enc and .json files, migrates to DB, and deletes them."""
    _migrate_kv_files(crypto, conn)
    _migrate_task_files(crypto, conn)

def get_conn():
    global _conn
    if _conn is None:
        init_db()
    return _conn

def close_db():
    """Encrypts DB back to .enc and deletes plaintext file."""
    global _conn
    if _conn is None:
        return
        
    try:
        _conn.commit()
        _conn.close()
    except Exception:
        pass
    finally:
        _conn = None
    
    crypto = CryptoManager()
    if crypto.is_enabled and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                plain_data = f.read()
            cipher_data = crypto.encrypt_bytes(plain_data)
            _atomic_write_file(DB_FILE_ENC, cipher_data, is_binary=True)
            # Verified Encryption: remove plaintext ONLY after successful encryption and write
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
        except Exception as e:
            print(f"[store] Failed to encrypt database: {e}")
            raise

# Auto-cleanup on script exit
atexit.register(close_db)

def load_data(key, default_val):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
    row = cur.fetchone()
    if row:
        return json.loads(row["value"])
    return default_val

def save_data(key, data):
    conn = get_conn()
    with conn:
        conn.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", 
                     (key, json.dumps(data)))

class TaskStore:
    def __init__(self, 
                 todos_path=TODOS_FILE, 
                 archive_path=ARCHIVE_FILE, 
                 todos_path_enc=None, 
                 archive_path_enc=None):
        self.todos_path = todos_path
        self.archive_path = archive_path
        self.todos_path_enc = todos_path_enc or (TODOS_FILE_ENC if todos_path == TODOS_FILE else todos_path + ".enc")
        self.archive_path_enc = archive_path_enc or (ARCHIVE_FILE_ENC if archive_path == ARCHIVE_FILE else archive_path + ".enc")
        
        self.crypto = CryptoManager()
        self.load_failed = False
        self._todos = None
        self._archive = None
        
        # Test isolation check: if custom test paths provided, use isolated in-memory or custom DB
        self.is_custom = (todos_path != TODOS_FILE or archive_path != ARCHIVE_FILE or todos_path_enc is not None)
        if self.is_custom:
            self._conn = sqlite3.connect(":memory:")
            self._conn.row_factory = sqlite3.Row
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE tasks (
                        id TEXT PRIMARY KEY,
                        status TEXT,
                        data JSON,
                        completed_at TEXT
                    )
                """)
            # Check if encrypted file was explicitly provided for testing decryption failure
            if self.todos_path_enc and os.path.exists(self.todos_path_enc) and self.crypto.is_enabled:
                try:
                    with open(self.todos_path_enc, "rb") as f:
                        decrypted = self.crypto.decrypt_dict(f.read())
                    self._todos = decrypted
                except DecryptionError:
                    self.load_failed = True
                    raise
        else:
            self._conn = None  # Uses global connection

    def _get_active_conn(self):
        if self.is_custom:
            return self._conn
        return get_conn()

    def _load_todos(self):
        conn = self._get_active_conn()
        cur = conn.cursor()
        cur.execute("SELECT data FROM tasks WHERE status = 'active'")
        self._todos = [json.loads(row["data"]) for row in cur.fetchall()]

    def _load_archive(self):
        conn = self._get_active_conn()
        cur = conn.cursor()
        cur.execute("SELECT data FROM tasks WHERE status = 'archived' ORDER BY completed_at DESC, rowid DESC LIMIT ?", (MAX_ARCHIVE_ITEMS,))
        self._archive = [json.loads(row["data"]) for row in cur.fetchall()]

    @property
    def todos(self):
        if self._todos is None:
            self._load_todos()
        return self._todos

    @todos.setter
    def todos(self, value):
        self._todos = value

    @property
    def archive(self):
        if self._archive is None:
            self._load_archive()
        return self._archive

    @archive.setter
    def archive(self, value):
        self._archive = value

    def get_task(self, task_id: str):
        for t in self.todos:
            if t.get("id") == task_id:
                return t
        return None

    def update_task(self, updated_task: dict):
        task_id = updated_task.get("id")
        for i, t in enumerate(self.todos):
            if t.get("id") == task_id:
                self.todos[i] = updated_task
                conn = self._get_active_conn()
                with conn:
                    conn.execute("UPDATE tasks SET data = ? WHERE id = ? AND status = 'active'",
                                 (json.dumps(updated_task), task_id))
                return True
        return False

    def add_task(self, task: dict):
        if self._todos is None:
            self._load_todos()
        self._todos.append(task)
        conn = self._get_active_conn()
        with conn:
            conn.execute("INSERT OR REPLACE INTO tasks (id, status, data, completed_at) VALUES (?, 'active', ?, NULL)",
                         (task.get("id"), json.dumps(task)))

    def archive_task(self, task_id: str):
        if self._todos is None:
            self._load_todos()
        if self._archive is None:
            self._load_archive()
            
        task = None
        for i, t in enumerate(self._todos):
            if t.get("id") == task_id:
                task = self._todos.pop(i)
                break
                
        if task:
            now_iso = datetime.now(timezone.utc).isoformat()
            task["completed_at"] = now_iso
            self._archive.insert(0, task)
            if len(self._archive) > MAX_ARCHIVE_ITEMS:
                self._archive = self._archive[:MAX_ARCHIVE_ITEMS]
                
            conn = self._get_active_conn()
            with conn:
                conn.execute("UPDATE tasks SET status = 'archived', data = ?, completed_at = ? WHERE id = ?",
                             (json.dumps(task), now_iso, task_id))
                # Delete excess archived tasks from DB
                conn.execute(f"""
                    DELETE FROM tasks 
                    WHERE status = 'archived' 
                    AND rowid NOT IN (
                        SELECT rowid FROM tasks WHERE status = 'archived' ORDER BY completed_at DESC, rowid DESC LIMIT {MAX_ARCHIVE_ITEMS}
                    )
                """)
            return True
        return False

    def save(self):
        if getattr(self, "load_failed", False):
            raise RuntimeError("TaskStore is in an invalid/unloaded state due to decryption failure. Writes are blocked to prevent data loss.")
        if self._todos is not None:
            conn = self._get_active_conn()
            with conn:
                for t in self._todos:
                    conn.execute("INSERT OR REPLACE INTO tasks (id, status, data, completed_at) VALUES (?, 'active', ?, NULL)",
                                 (t.get("id"), json.dumps(t)))
        conn = self._get_active_conn()
        conn.commit()
