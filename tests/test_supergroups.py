import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from personas.helpzy import Helpzy
from personas.remzy import Remzy

class TestSupergroups(unittest.TestCase):
    
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    @patch('personas.helpzy.send_message')
    @patch('personas.helpzy.os.makedirs')
    def test_helpzy_bind_commands(self, mock_makedirs, mock_send_message):
        helpzy = Helpzy(file_path=self.temp_file.name)
        helpzy.settings = {}
        
        # Test bind_news without message_thread_id
        helpzy.handle_command("/config bind_news", message_thread_id=None, chat_id="-100123")
        self.assertNotIn("topic_news", helpzy.settings)
        mock_send_message.assert_called_with("❌ Cannot bind: this is not a topic thread.", chat_id="-100123", message_thread_id=None)
        
        # Test bind_news with message_thread_id and bot mention
        helpzy.handle_command("/config@RemNewzBot bind_news", message_thread_id=42, chat_id="-100123")
        self.assertEqual(helpzy.settings["topic_news"], 42)
        self.assertEqual(helpzy.settings["supergroup_id"], "-100123")
        mock_send_message.assert_called_with("✅ Bound News digests to this topic.", chat_id="-100123", message_thread_id=42)

        # Test set_topic_tasks
        helpzy.handle_command("/config set_topic_tasks 100", message_thread_id=None, chat_id="-100123")
        self.assertEqual(helpzy.settings["topic_tasks"], 100)

    @patch('personas.remzy.send_message')
    @patch('personas.remzy.TaskStore')
    @patch('personas.remzy.resolve_topic_id')
    @patch('personas.remzy.parse_task_nlp')
    def test_remzy_origin_thread(self, mock_parse, mock_resolve_topic, mock_store_cls, mock_send_message):
        mock_parse.return_value = {"title": "Test task", "due_at": None, "priority": "normal"}
        
        # Setup mock store
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        
        remzy = Remzy()
        remzy.handle_command("/todo@RemNewzBot Test task", "none", "", "UTC", message_thread_id=55, chat_id="-100123")
        
        # Verify origin_thread_id and origin_chat_id were saved
        task = mock_store.add_task.call_args[0][0]
        self.assertEqual(task["origin_thread_id"], 55)
        self.assertEqual(task["origin_chat_id"], "-100123")
        
        # Verify message_thread_id and chat_id in send_message
        mock_send_message.assert_called_with("✅ <b>Task Created:</b> Test task\n📅 Due: No deadline\n🆔 <code>" + task["id"] + "</code>", chat_id="-100123", message_thread_id=55)

if __name__ == '__main__':
    unittest.main()

