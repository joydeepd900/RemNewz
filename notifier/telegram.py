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
    Falls back to hard-split if a single line exceeds the limit.

    Args:
        text: The full message text.
        max_length: Maximum characters per chunk.

    Returns:
        A list of message chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        # If a single line exceeds the limit, hard-split it
        if len(line) > max_length:
            if current_chunk:
                chunks.append(current_chunk.rstrip("\n"))
                current_chunk = ""
            # Split the long line into max_length segments
            for i in range(0, len(line), max_length):
                chunks.append(line[i:i + max_length])
            continue

        # Check if adding this line would exceed the limit
        candidate = current_chunk + line + "\n"
        if len(candidate) > max_length:
            if current_chunk:
                chunks.append(current_chunk.rstrip("\n"))
            current_chunk = line + "\n"
        else:
            current_chunk = candidate

    if current_chunk.strip():
        chunks.append(current_chunk.rstrip("\n"))

    return chunks


def send_message(text, parse_mode="HTML", reply_markup=None, disable_preview=True):
    """Send a message to the configured Telegram chat, with auto-chunking.

    Args:
        text: Message text (HTML formatted).
        parse_mode: Telegram parse mode ('HTML' or 'MarkdownV2').
        reply_markup: Optional dict for inline keyboard markup.
        disable_preview: Whether to disable link previews.

    Returns:
        List of API response dicts (one per chunk).

    Raises:
        requests.HTTPError: If all retries fail.
    """
    chat_id = _get_chat_id()
    chunks = _chunk_message(text)
    responses = []

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

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
