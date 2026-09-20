import os
import requests
from datetime import datetime, timedelta, timezone

def _search_repos(url: str, headers: dict, query: str, per_page: int = 5) -> list:
    """Execute GitHub repository search sorted by recency descending."""
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": per_page
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.RequestException as e:
        print(f"[github_repos] Failed to search repositories for '{query}': {e}")
        return []

def _format_repo(repo: dict, seen_urls: set) -> dict | None:
    """Validate quality guardrails and format candidate repo item."""
    repo_url = repo.get("html_url")
    if not repo_url or repo_url in seen_urls:
        return None
    if not repo.get("description") or repo.get("stargazers_count", 0) <= 500:
        return None
    seen_urls.add(repo_url)
    return {
        "source": "GitHub",
        "id": repo_url,
        "url": repo_url,
        "title": repo.get("full_name", "Unknown"),
        "summary": repo.get("description") or "No description provided.",
        "stars": repo.get("stargazers_count", 0),
        "pushed_at": repo.get("pushed_at") or repo.get("created_at") or "",
        "created_at": repo.get("created_at") or ""
    }

def _collect_repos(raw_repos: list, seen_urls: set, all_items: list) -> int:
    """Format and collect valid repos, returning the count of accepted items."""
    count = 0
    for repo in raw_repos:
        formatted = _format_repo(repo, seen_urls)
        if formatted:
            all_items.append(formatted)
            count += 1
    return count

def fetch_github_repos(config: dict) -> list:
    """Fetch recent trending GitHub repositories based on config topics and keywords."""
    github_token = os.environ.get("GITHUB_TOKEN")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    topics = config.get("topics", [])
    keywords = config.get("keywords", [])

    if not topics and not keywords:
        return []

    created_after_7 = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    pushed_after_30 = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    
    queries = [f"topic:{topic}" for topic in topics] + list(keywords)
    url = "https://api.github.com/search/repositories"
    
    all_items = []
    seen_urls = set()

    for q_base in queries:
        # Primary: created in last 7 days, stars > 500, ranked by recency
        query_primary = f"{q_base} created:>{created_after_7} stars:>500"
        accepted = _collect_repos(_search_repos(url, headers, query_primary, per_page=5), seen_urls, all_items)
        
        # Fallback: active in last 30 days, stars > 2000, ranked by recency
        if accepted < 3:
            query_fallback = f"{q_base} pushed:>{pushed_after_30} stars:>2000"
            _collect_repos(_search_repos(url, headers, query_fallback, per_page=5), seen_urls, all_items)

    # Apply recency ranking before truncating candidates
    all_items.sort(key=lambda x: x.get("pushed_at") or x.get("created_at") or "", reverse=True)
    return all_items[:10]
