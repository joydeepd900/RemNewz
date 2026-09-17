import unittest
import os
import json
import tempfile
from datetime import datetime, timedelta, timezone
from engine.dedup import DedupManager
from engine.ai_client import _deterministic_fallback, synthesize_item

class TestDedupManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and file for tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.test_dir.name, "seen_test.json")
        self.dedup = DedupManager(file_path=self.test_file)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_mark_and_check_seen(self):
        self.assertFalse(self.dedup.is_seen("item1"))
        self.dedup.mark_seen("item1")
        self.assertTrue(self.dedup.is_seen("item1"))

    def test_prune_old_items(self):
        # Add an old item directly to internal dict to bypass datetime.now() in mark_seen
        old_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        self.dedup.seen_items["old_item"] = old_time
        
        # Add a new item
        self.dedup.mark_seen("new_item")
        
        # Prune should remove old_item but keep new_item
        self.dedup.prune()
        
        self.assertFalse(self.dedup.is_seen("old_item"))
        self.assertTrue(self.dedup.is_seen("new_item"))

    def test_max_items_limit(self):
        # Add 1005 items
        for i in range(1005):
            # slightly varied timestamps to ensure sorting
            ts = (datetime.now(timezone.utc) - timedelta(seconds=1005-i)).isoformat()
            self.dedup.seen_items[f"item_{i}"] = ts
            
        self.dedup.prune()
        
        self.assertEqual(len(self.dedup.seen_items), 1000)
        # The oldest items (item_0 to item_4) should be pruned
        self.assertFalse(self.dedup.is_seen("item_0"))
        # The newest items should be kept
        self.assertTrue(self.dedup.is_seen("item_1004"))


class TestAIClient(unittest.TestCase):
    def test_deterministic_fallback(self):
        item = {
            "source": "GitHub",
            "title": "Test Repo",
            "url": "https://github.com/test/repo",
            "summary": "A test repository"
        }
        
        result, topic = _deterministic_fallback(item)
        
        self.assertIn("Test Repo", result)
        self.assertIn("https://github.com/test/repo", result)
        self.assertIn("A test repository", result)
        self.assertIsNone(topic)

    def test_synthesize_item_fallback(self):
        item = {
            "source": "RSS",
            "title": "Test News",
            "url": "https://example.com/news",
            "summary": "Some breaking news"
        }
        
        # Should use fallback if provider is 'none'
        result, topic = synthesize_item(item, style="concise", provider="none", model="any")
        
        self.assertIn("Test News", result)
        self.assertIn("https://example.com/news", result)
        self.assertIsNone(topic)
        
if __name__ == '__main__':
    unittest.main()
