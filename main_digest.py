"""
main_digest.py — Entrypoint for the Newzy digest workflow.

Phase 1: Fetches news from GitHub and RSS, dedups, synthesizes with AI, 
and sends individual items as digest messages to Telegram.
"""

import os
import sys
import yaml

# Fix Windows console encoding for emoji in print statements
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # Running in GitHub Actions, encoding is fine

from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

from engine.store import load_data, init_db, close_db
from engine.time_utils import now_local, format_datetime
from notifier.telegram import send_message, build_inline_keyboard, resolve_topic_id, resolve_supergroup_id
from fetchers.github_repos import fetch_github_repos
from fetchers.rss_hn import fetch_rss_feeds
from engine.dedup import DedupManager
from engine.ai_client import synthesize_item

def load_config() -> dict:
    """
    Load configuration settings from config.yml or fallback to config.example.yml.
    
    Returns:
        dict: The loaded configuration dictionary, or an empty dictionary if no file is found.
    """
    if os.path.exists("config.yml"):
        path = "config.yml"
    elif os.path.exists("config.example.yml"):
        path = "config.example.yml"
    else:
        print("[main_digest] Warning: No config file found. Using defaults.")
        return {}
        
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def run_digest(chat_id=None, message_thread_id=None, max_items=None, mark_seen=True, query=None) -> int:
    """
    Execute the core digest pipeline to fetch, deduplicate, synthesize, and send news.
    
    Args:
        chat_id (str, optional): Target Telegram chat ID. Defaults to environment setting.
        message_thread_id (int, optional): Target topic thread ID for Supergroups.
        max_items (int, optional): Maximum number of items to process. Overrides config limit.
        mark_seen (bool, optional): Whether to mark processed items as seen in the deduplication store.
        query (str, optional): Specific search query to override general topics (used for /news).
        
    Returns:
        int: Exit status code (0 for success).
    """
    print("[main_digest] Starting RemNewz digest pipeline...")
    
    config = load_config()
    settings = load_data("settings", {})
    
    # Merge dynamic overrides from settings.enc into config
    if "topics" in settings:
        config["topics"] = settings["topics"]
    if "digest_style" in settings:
        config["digest_style"] = settings["digest_style"]
        
    # If query is provided (e.g. via /news), override topics to just that query
    if query:
        config["topics"] = [query]
        config["keywords"] = []
        
    # Merge custom RSS feeds
    base_feeds = config.get("rss_feeds", []) or []
    custom_feeds = settings.get("rss_feeds", []) or []
    seen_feed_urls = {f.get("url") for f in base_feeds if isinstance(f, dict) and "url" in f}
    combined_feeds = list(base_feeds)
    for cf in custom_feeds:
        if isinstance(cf, dict) and cf.get("url") and cf.get("url") not in seen_feed_urls:
            combined_feeds.append(cf)
            seen_feed_urls.add(cf.get("url"))
    config["rss_feeds"] = combined_feeds

    dedup = DedupManager()
    
    ai_provider = os.environ.get("AI_PROVIDER", "none")
    ai_model = os.environ.get("AI_MODEL", "")
    digest_style = config.get("digest_style", "concise")
    
    # 1. Fetch items
    print("[main_digest] Fetching items from sources...")
    all_items = []
    all_items.extend(fetch_github_repos(config))
    if not query:
        all_items.extend(fetch_rss_feeds(config))
    
    # 2. Dedup and limit
    unseen_items = []
    for item in all_items:
        if not dedup.is_seen(item["id"]):
            unseen_items.append(item)
            
    # Configurable news limit per digest (default: 5, overridden by max_items)
    max_digest_items = max_items if max_items is not None else int(settings.get("news_limit", config.get("news_limit", 5)))
    items_to_process = unseen_items[:max_digest_items]
    
    print(f"[main_digest] Found {len(all_items)} total items, {len(unseen_items)} unseen. Processing top {len(items_to_process)}.")
    
    if not items_to_process:
        print("[main_digest] No new items to send. Exiting.")
        if mark_seen:
            dedup.prune()
        return 0
        
    # Destination Routing Safety
    target_chat = chat_id
    target_thread = message_thread_id
    
    if target_chat is None:
        # Running via automated cron
        news_topic_id = resolve_topic_id("news")
        supergroup_id = resolve_supergroup_id()
        if supergroup_id and news_topic_id is not None:
            target_chat = supergroup_id
            target_thread = news_topic_id
        else:
            target_chat = os.environ.get("TELEGRAM_CHAT_ID")
            target_thread = None
            
    # 3. Process and send each item
    for item in items_to_process:
        print(f"[main_digest] Synthesizing: {item['title']}...")
        
        # Synthesize text and extract topic
        msg_text, topic = synthesize_item(item, digest_style, ai_provider, ai_model)
        
        # Build interactive buttons
        # callback_data limit is 64 bytes. "remind_me:" is 10 bytes. Leaving 54 bytes for the title.
        encoded_title = item['title'].encode('utf-8')[:50].decode('utf-8', 'ignore')
        buttons = [{"text": "📌 Remind Me", "callback_data": f"remind_me:{encoded_title}"}]
        
        if topic:
            # Truncate topic to fit Telegram's 64-byte callback_data limit
            safe_topic = topic[:40]
            buttons.append({"text": "👍", "callback_data": f"like_{safe_topic}"})
            buttons.append({"text": "👎", "callback_data": f"dislike_{safe_topic}"})
            
        reply_markup = build_inline_keyboard([buttons])
        
        print(f"[main_digest] Sending to Telegram: {item['title']}...")
        responses = send_message(msg_text, reply_markup=reply_markup, chat_id=target_chat, message_thread_id=target_thread)
        
        # Check if successful
        if responses and responses[-1].get("ok"):
            if mark_seen:
                dedup.mark_seen(item["id"])
        else:
            print(f"[main_digest] Failed to send {item['title']}: {responses}")
            
    # 4. Cleanup
    if mark_seen:
        dedup.prune()
    print("[main_digest] Digest pipeline complete.")
    return 0

def main():
    """
    Main entry point for the scheduled digest workflow.
    Ensures that the encrypted database is initialized and properly closed
    even if the pipeline raises an exception.
    """
    init_db()
    try:
        return run_digest()
    finally:
        close_db()

if __name__ == "__main__":
    sys.exit(main())
