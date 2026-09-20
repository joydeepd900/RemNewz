import os
import requests
from datetime import datetime, timedelta, timezone

def _search_repos(url: str, headers: dict, query: str, per_page: int = 5) -> list:
    """
    Execute a GitHub repository search API request, sorted by recency.
    
    Args:
        url (str): The GitHub Search API endpoint.
        headers (dict): Authorization and accept headers.
        query (str): The search query string.
        per_page (int): Number of results to fetch per page.
        
    Returns:
        list: A list of repository metadata dictionaries from the API.
    """
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
    """
    Validate quality guardrails and format a candidate repository item.
    
    Filters out repositories that have no description or insufficient stars, 
    and checks against the deduplication set to avoid duplicates within a run.
    
    Args:
        repo (dict): Raw repository metadata from GitHub.
        seen_urls (set): A tracking set of already processed repository URLs.
        
    Returns:
        dict | None: A standardized dictionary for the digest, or None if rejected.
    """
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
    """
    Process, format, and collect valid repositories from a raw API response.
    
    Args:
        raw_repos (list): The list of raw repository dictionaries from GitHub.
        seen_urls (set): The set of already encountered URLs for deduplication.
        all_items (list): The master list appending accepted repositories.
        
    Returns:
        int: The number of repositories successfully validated and collected.
    """
    count = 0
    for repo in raw_repos:
        formatted = _format_repo(repo, seen_urls)
        if formatted:
            all_items.append(formatted)
            count += 1
    return count

def fetch_github_repos(config: dict) -> list:
    """
    Fetch recent, trending GitHub repositories based on configured topics and keywords.
    
    This fetcher applies a dual-pass query strategy:
      1. Primary: Repos created in the last 7 days with >500 stars.
      2. Fallback: Repos active in the last 30 days with >2000 stars (if primary yields few results).
    
    Args:
        config (dict): The active configuration dictionary containing 'topics' and 'keywords'.
        
    Returns:
        list: A recency-sorted list of standardized candidate repository dictionaries.
    """
    github_token = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")
    
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
        accepted = _collect_repos(_search_repos(url, headers, query_primary, per_page=30), seen_urls, all_items)
        
        # Fallback: active in last 30 days, stars > 2000, ranked by recency
        if accepted < 3:
            query_fallback = f"{q_base} pushed:>{pushed_after_30} stars:>2000"
            _collect_repos(_search_repos(url, headers, query_fallback, per_page=30), seen_urls, all_items)

    # Apply recency ranking before truncating candidates
    all_items.sort(key=lambda x: x.get("pushed_at") or x.get("created_at") or "", reverse=True)
    return all_items[:10]
