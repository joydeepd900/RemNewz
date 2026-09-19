"""
main_commands.py — Entrypoint for the Remzy & Helpzy command workflow.

Phase 3: Fetches Telegram updates, routes commands to personas, evaluates deadlines,
and allows commands.yml to persist state.
"""

import os
import sys
import json
from engine.store import load_data, save_data, init_db, close_db


if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from personas.remzy import Remzy
from personas.helpzy import Helpzy
from notifier.telegram import get_updates, answer_callback_query

def load_last_update_id() -> int:
    data = load_data("last_update_id", {})
    return data.get("last_id", -1) if data else -1

def save_last_update_id(last_id: int):
    try:
        save_data("last_update_id", {"last_id": last_id})
    except Exception as e:
        print(f"[main_commands] Failed to save last_update_id: {e}")

def run_pipeline():
    print("[main_commands] Starting RemNewz commands pipeline (Phase 3)...")
    
    allowed_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    ai_provider = os.environ.get("AI_PROVIDER", "none")
    ai_model = os.environ.get("AI_MODEL", "")
    
    remzy = Remzy()
    helpzy = Helpzy()
    user_tz = helpzy.settings.get("timezone", "UTC")
    
    last_id = load_last_update_id()
    
    # Check if this run was triggered by a webhook dispatch (e.g. Cloudflare Worker)
    webhook_payload = os.environ.get("TELEGRAM_UPDATE_PAYLOAD")
    if webhook_payload and webhook_payload.strip() and webhook_payload.strip() != "null":
        try:
            update_obj = json.loads(webhook_payload)
            updates = [update_obj] if isinstance(update_obj, dict) else []
            print("[main_commands] Processing update received from repository_dispatch webhook.")
        except Exception as e:
            print(f"[main_commands] Failed to parse webhook payload: {e}")
            updates = []
    else:
        # Fallback to polling: fetch updates with a short timeout
        if last_id == -1:
            offset = -1
        else:
            offset = last_id + 1 if last_id else None
        print(f"[main_commands] Fetching updates from Telegram (offset={offset})...")
        updates = get_updates(offset=offset, timeout=5)
    
    highest_id = last_id
    
    for update in updates:
        update_id = update.get("update_id")
        if highest_id is None or update_id > highest_id:
            highest_id = update_id
            
        try:
            # Handle Messages
            if "message" in update:
                msg = update["message"]
                chat_id = str(msg.get("chat", {}).get("id", ""))
                from_id = str(msg.get("from", {}).get("id", ""))
                
                # Security Allowlist Check:
                # Allow if message is in authorized chat OR sent by the authorized user (e.g. in a Supergroup)
                if chat_id != allowed_chat_id and from_id != allowed_chat_id:
                    print(f"[main_commands] Blocked unauthorized message from user {from_id} in chat {chat_id}")
                    continue
                    
                text = msg.get("text", "")
                message_thread_id = msg.get("message_thread_id")
                
                if text.startswith("/"):
                    # Try Helpzy first, then Remzy
                    if not helpzy.handle_command(text, message_thread_id=message_thread_id, chat_id=chat_id):
                        if not remzy.handle_command(text, ai_provider, ai_model, user_tz, message_thread_id=message_thread_id, chat_id=chat_id):
                            pass # Ignore unknown commands
                            
            # Handle Callback Queries (Inline Buttons)
            elif "callback_query" in update:
                cb = update["callback_query"]
                chat_id = str(cb.get("message", {}).get("chat", {}).get("id", ""))
                from_id = str(cb.get("from", {}).get("id", ""))
                message_thread_id = cb.get("message", {}).get("message_thread_id")
                
                if chat_id != allowed_chat_id and from_id != allowed_chat_id:
                    continue
                    
                data = cb.get("data", "")
                query_id = cb.get("id")
                
                if data == "remind_me":
                    remzy.handle_remind_me(data, message_thread_id=message_thread_id, chat_id=chat_id)
                    answer_callback_query(query_id, "Task Created!")
                elif data.startswith("like_"):
                    helpzy.handle_feedback(data, 1)
                    answer_callback_query(query_id, "Feedback recorded (Like)")
                elif data.startswith("dislike_"):
                    helpzy.handle_feedback(data, -1)
                    answer_callback_query(query_id, "Feedback recorded (Dislike)")
                else:
                    answer_callback_query(query_id) # Acknowledge anyway
        except Exception as e:
            # Note: Do not print raw `update` payload here to avoid leaking data in GitHub Actions logs.
            print(f"[main_commands] Error processing update {update_id}: {type(e).__name__} - {e}")

    if highest_id is not None and highest_id != last_id:
        save_last_update_id(highest_id)
        
    print("[main_commands] Evaluating task deadlines...")
    remzy.check_deadlines()
    
    print("[main_commands] Pipeline complete.")
    return 0

def main():
    init_db()
    try:
        return run_pipeline()
    finally:
        close_db()

if __name__ == "__main__":
    sys.exit(main())
