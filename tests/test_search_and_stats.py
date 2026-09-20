import unittest
import os
import tempfile
import json
from datetime import datetime, timezone, timedelta
from engine.store import TaskStore
from personas.remzy import Remzy

class TestSearchAndStats(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.todos_file = os.path.join(self.test_dir.name, "todos.json")
        self.archive_file = os.path.join(self.test_dir.name, "archive.json")
        self.store = TaskStore(self.todos_file, self.archive_file)
        
        # We simulate a few tasks
        self.now = datetime.now(timezone.utc)
        
        # 1. Active: High priority, due today
        self.store.add_task({
            "id": "t1",
            "title": "Fix critical bug in engine",
            "due_at": (self.now + timedelta(hours=2)).isoformat(),
            "priority": "high"
        })
        
        # 2. Active: Normal priority, overdue
        self.store.add_task({
            "id": "t2",
            "title": "Review marketing docs",
            "due_at": (self.now - timedelta(hours=5)).isoformat(),
            "priority": "normal"
        })
        
        # 3. Active: No deadline
        self.store.add_task({
            "id": "t3",
            "title": "Brainstorm new features",
            "due_at": None,
            "priority": "normal"
        })
        
        # 4. Active: Upcoming
        self.store.add_task({
            "id": "t4",
            "title": "Plan next quarter",
            "due_at": (self.now + timedelta(days=5)).isoformat(),
            "priority": "low"
        })
        
        # Now add some archived tasks directly via archive_task flow
        self.store.add_task({
            "id": "a1",
            "title": "Set up database schema",
            "due_at": (self.now - timedelta(days=3)).isoformat(),
            "priority": "high"
        })
        self.store.archive_task("a1")
        # For testing deadline compliance, we need to manually adjust completed_at in DB
        # because archive_task sets it to now.
        conn = self.store._get_active_conn()
        cur = conn.cursor()
        
        # a1: completed on time (completed 4 days ago, due 3 days ago)
        completed_a1 = (self.now - timedelta(days=4)).isoformat()
        cur.execute("UPDATE tasks SET completed_at = ? WHERE id = 'a1'", (completed_a1,))
        
        self.store.add_task({
            "id": "a2",
            "title": "Write unit tests",
            "due_at": (self.now - timedelta(days=10)).isoformat(),
            "priority": "normal"
        })
        self.store.archive_task("a2")
        # a2: completed late (completed 8 days ago, due 10 days ago)
        completed_a2 = (self.now - timedelta(days=8)).isoformat()
        cur.execute("UPDATE tasks SET completed_at = ? WHERE id = 'a2'", (completed_a2,))
        
        self.store.add_task({
            "id": "a3",
            "title": "Legacy refactor",
            "due_at": None,
            "priority": "low"
        })
        self.store.archive_task("a3")
        # a3: completed very long ago (40 days ago)
        completed_a3 = (self.now - timedelta(days=40)).isoformat()
        cur.execute("UPDATE tasks SET completed_at = ? WHERE id = 'a3'", (completed_a3,))

    def tearDown(self):
        self.test_dir.cleanup()

    def test_search_tasks(self):
        # 1. Search keyword in active
        res1 = self.store.search_tasks("bug")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["id"], "t1")
        
        # 2. Search keyword in archived
        res2 = self.store.search_tasks("schema")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["id"], "a1")
        
        # 3. Search case-insensitive substring
        res3 = self.store.search_tasks("UNIT ")
        self.assertEqual(len(res3), 1)
        self.assertEqual(res3[0]["id"], "a2")
        
        # 4. Search ID
        res4 = self.store.search_tasks("t4")
        self.assertEqual(len(res4), 1)
        self.assertEqual(res4[0]["id"], "t4")
        
        # 5. Search with status filter
        res5 = self.store.search_tasks("e", status="active") # matches 'feature', 'quarter', etc
        self.assertTrue(all(t["status"] == "active" for t in res5))
        self.assertGreater(len(res5), 0)
        
        # 6. Search returning empty
        res6 = self.store.search_tasks("NonExistentTaskXYZ")
        self.assertEqual(len(res6), 0)

    def test_get_stats(self):
        stats = self.store.get_stats(self.now)
        
        self.assertEqual(stats["total_tasks"], 7) # 4 active, 3 archived
        self.assertEqual(stats["active_count"], 4)
        self.assertEqual(stats["archived_count"], 3)
        self.assertEqual(stats["completion_rate_pct"], round(3 / 7 * 100, 1))
        
        # Active counts
        self.assertEqual(stats["overdue_count"], 1) # t2
        self.assertEqual(stats["due_today_count"], 1) # t1
        self.assertEqual(stats["upcoming_count"], 1) # t4
        self.assertEqual(stats["no_deadline_count"], 1) # t3
        
        # Priorities (active)
        self.assertEqual(stats["priorities"]["high"], 1)
        self.assertEqual(stats["priorities"]["normal"], 2)
        self.assertEqual(stats["priorities"]["low"], 1)
        
        # Archived velocity
        # a1: 4 days ago -> 7d and 30d
        # a2: 8 days ago -> 30d only
        # a3: 40 days ago -> neither
        self.assertEqual(stats["completed_7d"], 1)
        self.assertEqual(stats["completed_30d"], 2)
        self.assertEqual(stats["daily_velocity"], round(1 / 7.0, 1))
        
        # Deadline compliance
        # a1: on-time (completed 4d ago, due 3d ago -> comp <= due)
        # a2: late (completed 8d ago, due 10d ago -> comp > due)
        # a3: no deadline
        comp = stats["deadline_compliance"]
        self.assertEqual(comp["with_deadline"], 2)
        self.assertEqual(comp["on_time"], 1)
        self.assertEqual(comp["late"], 1)
        self.assertEqual(comp["rate_pct"], 50.0)

    def test_delete_task(self):
        # Verify t1 exists
        self.assertIsNotNone(self.store.get_task("t1"))
        
        # Delete t1
        deleted = self.store.delete_task("t1")
        self.assertTrue(deleted)
        
        # Verify t1 no longer in self._todos
        self.assertIsNone(self.store.get_task("t1"))
        
        # Verify t1 is gone from DB
        conn = self.store._get_active_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = 't1'")
        self.assertIsNone(cur.fetchone())
        
        # Delete non-existent
        deleted_none = self.store.delete_task("nonexistent")
        self.assertFalse(deleted_none)
        
        # Delete archived
        deleted_archived = self.store.delete_task("a1")
        self.assertTrue(deleted_archived)
        cur.execute("SELECT * FROM tasks WHERE id = 'a1'")
        self.assertIsNone(cur.fetchone())

if __name__ == "__main__":
    unittest.main()
