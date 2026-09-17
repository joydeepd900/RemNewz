import os
import requests
from datetime import datetime, timedelta, timezone

def fetch_github_repos(config: dict) -> list:
    """Fetch recent trending GitHub repositories based on config topics and keywords."""
    github_token = os.environ.get("GITHUB_TOKEN")
    
    # It's okay if GITHUB_TOKEN is not set for public searches, but rate limits are lower.
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    topics = config.get("topics", [])
    keywords = config.get("keywords", [])

    if not topics and not keywords:
        return []

    # Fetch repos created in the last 7 days
    created_after = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    
    query_parts = []
    
    # Add topics
    for topic in topics:
        query_parts.append(f"topic:{topic}")
        
    # Add keywords
    for kw in keywords:
        query_parts.append(kw)
        
    # Construct query: (topic1 OR topic2 OR keyword1) created:>YYYY-MM-DD
    # GitHub search doesn't strictly support OR across different fields easily without complex syntax,
    # but we can join them with OR if we use the same field or just keywords.
    # Actually, simpler is just keyword OR keyword
    q_str = " OR ".join(query_parts)
    query = f"{q_str} created:>{created_after}"

    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5 # We only want top 5 new repos to avoid overwhelming the digest
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        items = []
        for repo in data.get("items", []):
            items.append({
                "source": "GitHub",
                "id": repo["html_url"],
                "url": repo["html_url"],
                "title": repo["full_name"],
                "summary": repo.get("description") or "No description provided.",
                "stars": repo.get("stargazers_count", 0)
            })
        return items
    except requests.RequestException as e:
        print(f"[github_repos] Failed to fetch repositories: {e}")
        return []
