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
    """
    Retrieve the Telegram Bot API token from environment variables.
    
    Returns:
        str: The bot token.
        
    Raises:
        EnvironmentError: If TELEGRAM_BOT_TOKEN is not configured.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set in environment.")
    return token


def _get_chat_id():
    """
    Retrieve the primary target Telegram chat ID from environment variables.
    
    Returns:
        str: The chat ID.
        
    Raises:
        EnvironmentError: If TELEGRAM_CHAT_ID is not configured.
    """
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not chat_id:
        raise EnvironmentError("TELEGRAM_CHAT_ID is not set in environment.")
    return chat_id


def _api_url(method):
    """
    Construct the full HTTPS URL for a specific Telegram Bot API method.
    
    Args:
        method (str): The API method name (e.g., 'sendMessage').
        
    Returns:
        str: The fully qualified API URL.
    """
    return f"https://api.telegram.org/bot{_get_bot_token()}/{method}"


def _chunk_message(text, max_length=MAX_MESSAGE_LENGTH):
    """
    Split a lengthy text payload into chunks that fit within Telegram's character limits.

    This function carefully splits text at line boundaries to avoid breaking HTML syntax.
    It tracks open HTML tags across boundaries, ensuring they are cleanly closed at the 
    end of one chunk and reopened at the start of the next chunk.
    
    Args:
        text (str): The HTML-formatted message text to split.
        max_length (int): Maximum allowed characters per chunk (default: 4096).
        
    Returns:
        list[str]: A list of message chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""
    open_tags = []
    
    tag_pattern = re.compile(r'(</?[a-zA-Z0-9-]+[^>]*>)')
    
    def update_tags(tag_text):
        match = re.match(r'</?([a-zA-Z0-9-]+)', tag_text)
        if match:
            tag_name = match.group(1).lower()
            if tag_text.startswith('</'):
                if open_tags and open_tags[-1][0] == tag_name:
                    open_tags.pop()
            else:
                open_tags.append((tag_name, tag_text))

    for line in lines:
        if len(line) <= max_length and len(current_chunk) + len(line) + 1 <= max_length:
            # Fits nicely
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
                
            for match in tag_pattern.finditer(line):
                update_tags(match.group(0))
            continue
            
        # Current line pushes chunk over limit, or line itself is > max_length
        # First flush current chunk if not empty
        if current_chunk:
            close_str = "".join(f"</{tag[0]}>" for tag in reversed(open_tags))
            chunks.append(current_chunk + close_str)
            open_str = "".join(tag[1] for tag in open_tags)
            current_chunk = open_str
        else:
            current_chunk = ""
            
        # Process long line by tokens (text blocks and HTML tags)
        tokens = tag_pattern.split(line)
        
        for token in tokens:
            if not token:
                continue
                
            is_tag = tag_pattern.match(token)
            
            # If a single non-tag token is massive, we must split it by characters
            if not is_tag and len(token) > max_length:
                for i in range(0, len(token), max_length):
                    part = token[i:i + max_length]
                    if len(current_chunk) + len(part) > max_length:
                        close_str = "".join(f"</{t[0]}>" for t in reversed(open_tags))
                        chunks.append(current_chunk + close_str)
                        open_str = "".join(t[1] for t in open_tags)
                        current_chunk = open_str + part
                    else:
                        current_chunk += part
                continue
                
            # If token fits in chunk
            if len(current_chunk) + len(token) <= max_length:
                current_chunk += token
                if is_tag:
                    update_tags(token)
            else:
                # Flush and start new chunk
                close_str = "".join(f"</{t[0]}>" for t in reversed(open_tags))
                chunks.append(current_chunk + close_str)
                open_str = "".join(t[1] for t in open_tags)
                current_chunk = open_str + token
                if is_tag:
                    update_tags(token)

    if current_chunk.strip():
        close_str = "".join(f"</{tag[0]}>" for tag in reversed(open_tags))
        if close_str and not current_chunk.rstrip("\n").endswith(close_str):
             chunks.append(current_chunk.rstrip("\n") + close_str)
        else:
             chunks.append(current_chunk.rstrip("\n"))

    return chunks

def send_message(text, parse_mode="HTML", reply_markup=None, disable_preview=True, chat_id=None, message_thread_id=None):
    """
    Transmit a message to a Telegram chat, handling long text by chunking automatically.

    Args:
        text (str): The message text body (HTML formatted by default).
        parse_mode (str): Formatting mode for Telegram ('HTML' or 'MarkdownV2').
        reply_markup (dict, optional): A dictionary defining an inline keyboard matrix.
        disable_preview (bool): Whether to suppress URL link previews in the client.
        chat_id (str, optional): The target chat ID. Defaults to the environment configuration.
        message_thread_id (int, optional): The thread ID for forum topics within a supergroup.

    Returns:
        list[dict]: A list containing the JSON responses from the API for each chunk sent.

    Raises:
        requests.HTTPError: If the maximum number of network retries is exhausted.
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
    """
    Execute a POST request to Telegram with built-in exponential backoff.

    Handles temporary network failures and Telegram API rate limits (HTTP 429),
    backing off and retrying automatically. Also attempts a fallback to plain 
    text if the Telegram server rejects the payload due to HTML parsing errors.

    Args:
        payload (dict): The complete JSON payload for the API request.

    Returns:
        dict: The parsed JSON response from the API.

    Raises:
        requests.HTTPError: If all retry attempts are exhausted without success.
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
    """
    Construct a valid Telegram InlineKeyboardMarkup dictionary from a layout definition.

    Args:
        buttons (list[list[dict]]): A matrix (list of lists) representing rows and 
                                    columns of buttons. Each button dict should contain
                                    'text' and 'callback_data'.

    Returns:
        dict: A dictionary structure compatible with the Telegram API 'reply_markup' field.
    """
    return {
        "inline_keyboard": [
            [{"text": btn["text"], "callback_data": btn["callback_data"]} for btn in row]
            for row in buttons
        ]
    }

def get_updates(offset=None, timeout=30):
    """
    Poll the Telegram server for recent inbound updates (messages, callbacks, etc.).
    
    Args:
        offset (int, optional): The update_id to start fetching from. Used to acknowledge previous updates.
        timeout (int): The long-polling timeout in seconds.
        
    Returns:
        list[dict]: A list containing update payload dictionaries.
    """
    url = _api_url("getUpdates")
    payload = {"timeout": timeout}
    if offset is not None:
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
    """
    Acknowledge a Telegram callback query to dismiss the loading indicator on the client.
    
    Args:
        callback_query_id (str): The unique ID of the callback query to answer.
        text (str, optional): A brief notification text to display to the user.
    """
    url = _api_url("answerCallbackQuery")
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[telegram] answerCallbackQuery failed: {e}")

def resolve_topic_id(topic_name: str) -> int:
    """
    Resolve the configured forum topic ID from user settings.
    
    Args:
        topic_name (str): The logical name of the topic (e.g., 'news', 'tasks').
        
    Returns:
        int: The thread ID of the specified topic, or None if not bound.
    """
    settings = load_data("settings", {})
    return settings.get(f"topic_{topic_name}")

def resolve_supergroup_id():
    """
    Resolve the configured master supergroup ID from user settings.
    
    Returns:
        int | None: The chat ID of the authorized supergroup, if bound.
    """
    settings = load_data("settings", {})
    return settings.get("supergroup_id")
