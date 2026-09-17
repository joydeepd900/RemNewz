import unittest
import os
import json
import tempfile
import html
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from engine.crypto import CryptoManager, DecryptionError
from engine.store import TaskStore
from notifier.telegram import _chunk_message
from personas.remzy import Remzy

class TestResilience(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.todos_file = os.path.join(self.test_dir.name, "todos.json")
        self.archive_file = os.path.join(self.test_dir.name, "archive.json")
        self.todos_enc = os.path.join(self.test_dir.name, "todos.enc")
        self.archive_enc = os.path.join(self.test_dir.name, "archive.enc")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch.dict(os.environ, {"ENCRYPTION_KEY": "wrongkey"})
    def test_decryption_error_blocks_writes(self):
        # We need a valid fernet key to encrypt initially
        from cryptography.fernet import Fernet
        valid_key = Fernet.generate_key()
        invalid_key = Fernet.generate_key()
        
        fernet_valid = Fernet(valid_key)
        
        # Create an encrypted file
        data = [{"id": "t1", "title": "secret task"}]
        with open(self.todos_enc, "wb") as f:
            f.write(fernet_valid.encrypt(json.dumps(data).encode('utf-8')))

        # Now attempt to load with invalid key
        with patch.dict(os.environ, {"ENCRYPTION_KEY": invalid_key.decode('utf-8')}):
            with self.assertRaises(DecryptionError):
                store = TaskStore(self.todos_file, self.archive_file, self.todos_enc, self.archive_enc)
            
            # Since _load raised, store object creation failed. Let's manually trigger it to test save block
            store = TaskStore.__new__(TaskStore)
            store.todos_path = self.todos_file
            store.archive_path = self.archive_file
            store.todos_path_enc = self.todos_enc
            store.archive_path_enc = self.archive_enc
            store.todos = []
            store.archive = []
            store.crypto = CryptoManager()
            store.load_failed = True # Simulate the failure

            with self.assertRaises(RuntimeError):
                store.save()

    def test_tag_safe_chunking(self):
        # Test that open tags are closed and reopened
        text = "<b>Line 1\nLine 2\nLine 3</b>"
        # We use a very small max_length to force chunking
        chunks = _chunk_message(text, max_length=15)
        
        self.assertTrue(chunks[0].startswith("<b>"))
        self.assertTrue(chunks[0].endswith("</b>"))
        self.assertTrue(chunks[1].startswith("<b>"))
        self.assertTrue(chunks[-1].endswith("</b>"))

    def test_timezone_naive_safeguard(self):
        remzy = Remzy()
        remzy.store = MagicMock()
        
        # Test task with a naive datetime
        task = {
            "id": "t1",
            "title": "naive test",
            "due_at": "2024-01-01T12:00:00", # Naive
            "reminded_due": True,
            "last_overdue_nudge": "2024-01-01T13:00:00" # Naive
        }
        
        remzy.store.todos = [task]
        
        with patch('personas.remzy.send_message') as mock_send:
            # Should not raise TypeError when subtracting aware now_utc from naive last_nudge
            remzy.check_deadlines()
            self.assertTrue(remzy.store.save.called)

if __name__ == '__main__':
    unittest.main()
