"""
notifier/telegram.py — Telegram message sender for RemNewz.

Handles:
  - Sending HTML-formatted messages via the Telegram Bot API.
  - Automatic 4KB message chunking (Telegram's limit is 4096 chars).
  - Inline keyboard buttons for interactive feedback.
  - Retry logic with exponential backoff.
"""

import os
import time
import json
import requests
import re
from engine.store import load_data

# Telegram Bot API limit (chars, not bytes)
MAX_MESSAGE_LENGTH = 4096

# Retry config
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1


def _get_bot_token():
    """Get the Telegram bot token from environment."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set in environment.")
    return token


def _get_chat_id():
    """Get the target chat ID from environment."""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not chat_id:
        raise EnvironmentError("TELEGRAM_CHAT_ID is not set in environment.")
    return chat_id


def _api_url(method):
    """Build a Telegram Bot API URL."""
    return f"https://api.telegram.org/bot{_get_bot_token()}/{method}"


def _chunk_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Split a message into chunks that fit within Telegram's character limit.

    Splits at line boundaries to preserve HTML formatting.
    Tracks open tags to close and reopen them across chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""
    open_tags = []
    
    tag_pattern = re.compile(r'</?([a-zA-Z0-9-]+)[^>]*>')
    
    def update_tags(line_segment):
        for match in tag_pattern.finditer(line_segment):
            tag_text = match.group(0)
            tag_name = match.group(1).lower()
            if tag_text.startswith('</'):
                if open_tags and open_tags[-1][0] == tag_name:
                    open_tags.pop()
            else:
                open_tags.append((tag_name, tag_text))

    for line in lines:
        if len(line) > max_length:
            if current_chunk:
                close_str = "".join(f"</{tag[0]}>" for tag in reversed(open_tags))
                chunks.append(current_chunk.rstrip("\n") + close_str)
                current_chunk = ""
            for i in range(0, len(line), max_length):
                chunks.append(line[i:i + max_length])
            continue

        candidate = current_chunk + line + "\n"
        if len(candidate) > max_length:
            if current_chunk:
                close_str = "".join(f"</{tag[0]}>" for tag in reversed(open_tags))
                chunks.append(current_chunk.rstrip("\n") + close_str)
                
                open_str = "".join(tag[1] for tag in open_tags)
                current_chunk = open_str + line + "\n"
                update_tags(line)
            else:
                current_chunk = line + "\n"
                update_tags(line)
        else:
            current_chunk = candidate
            update_tags(line)

    if current_chunk.strip():
        close_str = "".join(f"</{tag[0]}>" for tag in reversed(open_tags))
        if close_str and not current_chunk.rstrip("\n").endswith(close_str):
             chunks.append(current_chunk.rstrip("\n") + close_str)
        else:
             chunks.append(current_chunk.rstrip("\n"))

    return chunks

def send_message(text, parse_mode="HTML", reply_markup=None, disable_preview=True, chat_id=None, message_thread_id=None):
    """Send a message to the configured Telegram chat, with auto-chunking.

    Args:
        text: Message text (HTML formatted).
        parse_mode: Telegram parse mode ('HTML' or 'MarkdownV2').
        reply_markup: Optional dict for inline keyboard markup.
        disable_preview: Whether to disable link previews.
        chat_id: Optional chat ID. If None, uses default from env.
        message_thread_id: Optional message_thread_id for forum topics.

    Returns:
        List of API response dicts (one per chunk).

    Raises:
        requests.HTTPError: If all retries fail.
    """
    target_chat_id = chat_id if chat_id else _get_chat_id()
    chunks = _chunk_message(text)
    responses = []

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": target_chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id

        # Only attach inline keyboard to the last chunk
        if reply_markup and i == len(chunks) - 1:
            payload["reply_markup"] = json.dumps(reply_markup)

        response = _send_with_retry(payload)
        responses.append(response)

    return responses


def _send_with_retry(payload):
    """Send a single message with exponential backoff retry.

    Args:
        payload: The complete API payload dict.

    Returns:
        The API response JSON dict.

    Raises:
        requests.HTTPError: If all retries are exhausted.
    """
    url = _api_url("sendMessage")
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=30)

            # Handle Telegram rate limiting (429)
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", backoff)
                print(f"[telegram] Rate limited. Waiting {retry_after}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(retry_after)
                backoff *= 2
                continue

            resp.raise_for_status()
            result = resp.json()

            if not result.get("ok"):
                print(f"[telegram] API error: {result.get('description', 'unknown')}")

            return result

        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400:
                try:
                    err_desc = e.response.json().get("description", "")
                    if "can't parse entities" in err_desc.lower() or "html" in err_desc.lower():
                        print(f"[telegram] HTML parse error: {err_desc}. Falling back to plain text.")
                        if "parse_mode" in payload:
                            payload.pop("parse_mode")
                        # Try once more without formatting, bypassing standard retry
                        resp = requests.post(url, json=payload, timeout=30)
                        resp.raise_for_status()
                        return resp.json()
                except Exception:
                    pass

            if attempt == MAX_RETRIES:
                print(f"[telegram] FAILED after {MAX_RETRIES} attempts: {e}")
                raise
            print(f"[telegram] Attempt {attempt} failed: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 2

    return {}  # Should not reach here


def build_inline_keyboard(buttons):
    """Build a Telegram InlineKeyboardMarkup from a list of button rows.

    Args:
        buttons: List of lists, where each inner list contains dicts with
                 'text' and 'callback_data' keys.
                 Example: [[{"text": "👍", "callback_data": "like_123"},
                             {"text": "👎", "callback_data": "dislike_123"}]]

    Returns:
        A dict suitable for the reply_markup parameter.
    """
    return {
        "inline_keyboard": [
            [{"text": btn["text"], "callback_data": btn["callback_data"]} for btn in row]
            for row in buttons
        ]
    }

def get_updates(offset=None, timeout=30):
    """Fetch recent updates from Telegram.
    
    Args:
        offset: The update_id to start fetching from.
        timeout: Long polling timeout in seconds.
        
    Returns:
        List of update dicts.
    """
    url = _api_url("getUpdates")
    payload = {"timeout": timeout}
    if offset:
        payload["offset"] = offset
        
    try:
        resp = requests.post(url, json=payload, timeout=timeout + 5)
        resp.raise_for_status()
        result = resp.json()
        if result.get("ok"):
            return result.get("result", [])
        print(f"[telegram] getUpdates error: {result.get('description')}")
    except requests.exceptions.RequestException as e:
        print(f"[telegram] getUpdates failed: {e}")
    return []

def answer_callback_query(callback_query_id, text=None):
    """Acknowledge a callback query to remove the loading state on the button."""
    url = _api_url("answerCallbackQuery")
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[telegram] answerCallbackQuery failed: {e}")

def resolve_topic_id(topic_name: str) -> int:
    """Resolve configured topic ID from settings if bound."""
    settings = load_data("settings", {})
    return settings.get(f"topic_{topic_name}")

def resolve_supergroup_id():
    """Resolve configured supergroup chat ID from settings if bound."""
    settings = load_data("settings", {})
    return settings.get("supergroup_id")
