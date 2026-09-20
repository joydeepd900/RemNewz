import os
import unittest
from unittest.mock import patch, MagicMock
from personas.helpzy import Helpzy

class TestSourcesAndConfig(unittest.TestCase):
    @patch('personas.helpzy.send_message')
    @patch('personas.helpzy.save_data')
    @patch('personas.helpzy.load_data')
    def test_source_add_and_list(self, mock_load, mock_save, mock_send):
        mock_load.return_value = {"rss_feeds": [], "topics": ["Python"]}
        helpzy = Helpzy()
        
        # Test add source with explicit label
        helpzy.handle_command("/source add https://news.ycombinator.com/rss Hacker News", chat_id="123")
        self.assertEqual(len(helpzy.settings["rss_feeds"]), 1)
        self.assertEqual(helpzy.settings["rss_feeds"][0]["label"], "Hacker News")
        self.assertEqual(helpzy.settings["rss_feeds"][0]["url"], "https://news.ycombinator.com/rss")
        mock_save.assert_called()
        mock_send.assert_called()
        
        # Test add source with auto-inferred label
        helpzy.handle_command("/source add https://techcrunch.com/feed/", chat_id="123")
        self.assertEqual(len(helpzy.settings["rss_feeds"]), 2)
        self.assertEqual(helpzy.settings["rss_feeds"][1]["label"], "Techcrunch")
        
        # Test add duplicate source
        helpzy.handle_command("/source add https://news.ycombinator.com/rss", chat_id="123")
        self.assertEqual(len(helpzy.settings["rss_feeds"]), 2)
        
        # Test list sources
        helpzy.handle_command("/source", chat_id="123")
        last_msg = mock_send.call_args[0][0]
        self.assertIn("Active News Sources", last_msg)
        self.assertIn("Hacker News", last_msg)
        self.assertIn("Techcrunch", last_msg)
        self.assertIn("Python", last_msg)

    @patch('personas.helpzy.send_message')
    @patch('personas.helpzy.save_data')
    @patch('personas.helpzy.load_data')
    def test_source_remove(self, mock_load, mock_save, mock_send):
        mock_load.return_value = {
            "rss_feeds": [
                {"url": "https://news.ycombinator.com/rss", "label": "Hacker News"},
                {"url": "https://techcrunch.com/feed/", "label": "Techcrunch"}
            ]
        }
        helpzy = Helpzy()
        
        # Remove by 1-based index (remove item 1: Hacker News)
        helpzy.handle_command("/source remove 1", chat_id="123")
        self.assertEqual(len(helpzy.settings["rss_feeds"]), 1)
        self.assertEqual(helpzy.settings["rss_feeds"][0]["label"], "Techcrunch")
        
        # Remove by URL
        helpzy.handle_command("/source remove https://techcrunch.com/feed/", chat_id="123")
        self.assertEqual(len(helpzy.settings["rss_feeds"]), 0)

    @patch('personas.helpzy.send_message')
    @patch('personas.helpzy.save_data')
    @patch('personas.helpzy.load_data')
    def test_set_limit(self, mock_load, mock_save, mock_send):
        mock_load.return_value = {}
        helpzy = Helpzy()
        
        # Valid limit
        helpzy.handle_command("/config set_limit 15", chat_id="123")
        self.assertEqual(helpzy.settings["news_limit"], 15)
        
        # Invalid limit (< 1 or > 15)
        helpzy.handle_command("/config set_limit 16", chat_id="123")
        self.assertEqual(helpzy.settings["news_limit"], 15) # Unchanged

    @patch('personas.helpzy.send_message')
    @patch('personas.helpzy.load_data')
    def test_repo_mode_url_generation(self, mock_load, mock_send):
        mock_load.return_value = {}
        helpzy = Helpzy()
        
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "user/my-repo"}):
            helpzy.handle_command("/config repo_mode", chat_id="123")
            last_msg = mock_send.call_args[0][0]
            self.assertIn("https://github.com/user/my-repo/edit/main/.github/workflows/commands.yml", last_msg)

if __name__ == '__main__':
    unittest.main()
