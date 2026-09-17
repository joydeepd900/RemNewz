import feedparser
import re

def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def fetch_rss_feeds(config: dict) -> list:
    """Fetch RSS feeds specified in config."""
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
            
            # Take top 3 from each feed to avoid overwhelming
            for entry in parsed.entries[:3]:
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
