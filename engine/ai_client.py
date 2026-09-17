import os
import requests
import json

def synthesize_item(item: dict, style: str, provider: str, model: str) -> str:
    """
    Use an AI provider to summarize/synthesize a single news item based on the requested style.
    Returns the synthesized text (preferably HTML formatted).
    If provider is 'none' or fails, returns a deterministic fallback string.
    """
    if provider.lower() == "none" or not model:
        return _deterministic_fallback(item)

    prompt = _build_prompt(item, style)
    
    try:
        if provider.lower() == "gemini":
            return _call_gemini(prompt, model)
        elif provider.lower() == "openrouter":
            return _call_openrouter(prompt, model)
        elif provider.lower() == "groq":
            return _call_groq(prompt, model)
        else:
            print(f"[ai_client] Unknown provider {provider}, using fallback.")
            return _deterministic_fallback(item)
    except Exception as e:
        print(f"[ai_client] AI synthesis failed ({e}). Using fallback.")
        return _deterministic_fallback(item)

def _build_prompt(item: dict, style: str) -> str:
    return f"""
You are an expert tech summarizer. Summarize the following news item in the '{style}' style.
Keep it concise and punchy. Use HTML formatting (<b>, <i>, <code>, <a href="...">).
Do not use Markdown. Do not include greetings.

Title: {item.get('title')}
URL: {item.get('url')}
Source: {item.get('source')}
Description: {item.get('summary')}
"""

def _call_gemini(prompt: str, model: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise ValueError("Unexpected response format from Gemini")

def _call_openrouter(prompt: str, model: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise ValueError("Unexpected response format from OpenRouter")

def _call_groq(prompt: str, model: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise ValueError("Unexpected response format from Groq")

import html

def _deterministic_fallback(item: dict) -> str:
    """Fallback formatting if no AI is configured."""
    source = html.escape(item.get('source', 'Unknown'))
    title = html.escape(item.get('title', 'No Title'))
    url = item.get('url', '#')
    summary = html.escape(item.get('summary', ''))
    
    msg = f"📰 <b>{source}</b>\n\n"
    msg += f"<b><a href='{url}'>{title}</a></b>\n"
    if summary:
        msg += f"<i>{summary}</i>"
        
    return msg

import re
from datetime import datetime, timezone, timedelta

def parse_task_nlp(text: str, provider: str, model: str, user_tz: str) -> dict:
    """
    Parse a natural language task description into structured data using AI.
    Returns: {"title": str, "due_at": "ISO", "priority": "normal|high"}
    """
    if provider.lower() == "none" or not model:
        return _deterministic_task_fallback(text, user_tz)

    now_iso = datetime.now(timezone.utc).isoformat()
    prompt = f"""
You are a task parser. The user wants to create a reminder.
Current time in UTC: {now_iso}
User timezone: {user_tz}
User input: "{text}"

Extract the task details and return ONLY a valid JSON object with:
- "title": A clear task title.
- "due_at": An absolute ISO 8601 UTC timestamp for when it is due (or null if no deadline). Do the math based on the current time and user timezone.
- "priority": "normal" or "high".

Return strictly JSON. No markdown backticks.
"""

    try:
        if provider.lower() == "gemini":
            raw_output = _call_gemini(prompt, model)
        elif provider.lower() == "openrouter":
            raw_output = _call_openrouter(prompt, model)
        elif provider.lower() == "groq":
            raw_output = _call_groq(prompt, model)
        else:
            return _deterministic_task_fallback(text, user_tz)
            
        # Robust JSON extraction
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if match:
            raw_output = match.group(0)
        parsed = json.loads(raw_output)
        return {
            "title": parsed.get("title", text),
            "due_at": parsed.get("due_at"),
            "priority": parsed.get("priority", "normal")
        }
    except Exception as e:
        print(f"[ai_client] Task parsing failed ({e}). Using fallback.")
        return _deterministic_task_fallback(text, user_tz)

def _deterministic_task_fallback(text: str, user_tz: str) -> dict:
    """Regex fallback for task parsing if AI fails."""
    # Strip '/todo' if present
    text = re.sub(r'^/todo\s+', '', text, flags=re.IGNORECASE)
    
    # Very basic "tomorrow" parsing
    due_at = None
    if "tomorrow" in text.lower():
        due_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        text = re.sub(r'(?i)\btomorrow\b', '', text).strip()
        
    return {
        "title": text or "New Task",
        "due_at": due_at,
        "priority": "normal"
    }
