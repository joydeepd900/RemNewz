import feedparser
import re

def strip_html(text: str) -> str:
    """
    Strip HTML tags from a given text string.
    
    Args:
        text (str): The raw text potentially containing HTML tags.
        
    Returns:
        str: The sanitized plain text string.
    """
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def fetch_rss_feeds(config: dict) -> list:
    """
    Fetch and parse RSS/Atom feeds specified in the configuration.
    
    Args:
        config (dict): The active configuration dictionary containing 'rss_feeds'.
        
    Returns:
        list: A list of standardized dictionaries representing recent feed entries.
    """
    feeds = config.get("rss_feeds", [])
    if not feeds:
        return []

    items = []
    
    for feed_info in feeds:
        url = feed_info.get("url")
        label = feed_info.get("label", "RSS")
        
        if not url:
            continue
            
        try:
            parsed = feedparser.parse(url)
            
            # Take top 20 from each feed to allow Deduplication manager to find fresh unseen stories
            for entry in parsed.entries[:20]:
                items.append({
                    "source": label,
                    "id": entry.get("id", entry.get("link")),
                    "url": entry.get("link"),
                    "title": entry.get("title", "No Title"),
                    "summary": strip_html(entry.get("summary", entry.get("description", "")))[:200]
                })
        except Exception as e:
            print(f"[rss_hn] Failed to parse feed {url}: {e}")
            
    return items
