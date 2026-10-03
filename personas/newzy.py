"""
personas/newzy.py — Newzy news scout persona.
Exposes the Newzy digest pipeline interface and presentation formatting.
"""

from main_digest import run_digest

class Newzy:
    """
    Newzy acts as the news and intelligence scout persona.
    
    It operates autonomously to discover, synthesize, and deliver technical news 
    on schedule and on demand. It encapsulates the digest pipeline logic.
    """
    
    @staticmethod
    def deliver_digest(chat_id=None, message_thread_id=None, max_items=None, mark_seen=True, query=None):
        """
        Trigger the full end-to-end digest pipeline.
        
        Args:
            chat_id (str, optional): Target Telegram chat ID.
            message_thread_id (int, optional): Target topic thread ID for Supergroups.
            max_items (int, optional): Maximum number of items to process. Overrides config limit.
            mark_seen (bool, optional): Whether to mark processed items as seen in the deduplication store.
            query (str, optional): Specific search query to override general topics (used for /news).
            
        Returns:
            int: Exit status code (0 for success).
        """
        return run_digest(chat_id=chat_id, 
                          message_thread_id=message_thread_id, 
                          max_items=max_items, 
                          mark_seen=mark_seen, 
                          query=query)
