import unittest
import os
import json
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from engine.store import TaskStore
from personas.remzy import Remzy

class TestReminders(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.todos_file = os.path.join(self.test_dir.name, "todos.json")
        self.archive_file = os.path.join(self.test_dir.name, "archive.json")
        
        # Write empty lists
        with open(self.todos_file, 'w') as f: json.dump([], f)
        with open(self.archive_file, 'w') as f: json.dump([], f)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_store_archive_rotation(self):
        store = TaskStore(self.todos_file, self.archive_file)
        
        # Add 55 tasks
        for i in range(55):
            store.add_task({"id": f"task_{i}", "title": f"Task {i}"})
            
        self.assertEqual(len(store.todos), 55)
        
        # Archive all 55 tasks
        for i in range(55):
            store.archive_task(f"task_{i}")
            
        self.assertEqual(len(store.todos), 0)
        self.assertEqual(len(store.archive), 50)
        
        # The oldest items (task_0 to task_4) should be pruned because archive limit is 50.
        # Since archive_task inserts at index 0, the last ones added (task_54) are at the front.
        # So task_0 to task_4 should fall off the end.
        archived_ids = [t["id"] for t in store.archive]
        self.assertNotIn("task_0", archived_ids)
        self.assertIn("task_54", archived_ids)

    @patch('personas.remzy.send_message')
    def test_anti_spam_guardrails(self, mock_send):
        # Setup Remzy with custom store
        remzy = Remzy()
        remzy.store = TaskStore(self.todos_file, self.archive_file)
        
        now = datetime.now(timezone.utc)
        
        # Task 1: due 5 minutes ago, hasn't been reminded
        task1 = {
            "id": "t1",
            "title": "Task 1",
            "due_at": (now - timedelta(minutes=5)).isoformat(),
            "reminded_due": False
        }
        
        # Task 2: due 2 days ago, reminded, last nudge 12 hours ago
        task2 = {
            "id": "t2",
            "title": "Task 2",
            "due_at": (now - timedelta(days=2)).isoformat(),
            "reminded_due": True,
            "last_overdue_nudge": (now - timedelta(hours=12)).isoformat()
        }
        
        # Task 3: due 3 days ago, reminded, last nudge 25 hours ago
        task3 = {
            "id": "t3",
            "title": "Task 3",
            "due_at": (now - timedelta(days=3)).isoformat(),
            "reminded_due": True,
            "last_overdue_nudge": (now - timedelta(hours=25)).isoformat()
        }
        
        remzy.store.add_task(task1)
        remzy.store.add_task(task2)
        remzy.store.add_task(task3)
        
        # Run check
        remzy.check_deadlines()
        
        # Expect 2 messages: task 1 (due) and task 3 (overdue nudge)
        # Task 2 should be suppressed by the 24-hour guardrail
        self.assertEqual(mock_send.call_count, 2)
        
        # Check mutations
        t1_updated = remzy.store.get_task("t1")
        self.assertTrue(t1_updated["reminded_due"])
        
        t3_updated = remzy.store.get_task("t3")
        last_nudge_dt = datetime.fromisoformat(t3_updated["last_overdue_nudge"])
        self.assertGreater(last_nudge_dt, now) # now was recorded before checking
        
        # Run check again, immediately
        remzy.check_deadlines()
        
        # Call count should still be 2, because no new notifications should trigger
        self.assertEqual(mock_send.call_count, 2)

if __name__ == '__main__':
    unittest.main()
