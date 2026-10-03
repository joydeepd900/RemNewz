import os
import math
import requests
from datetime import datetime, timedelta, timezone

def _search_repos(url: str, headers: dict, query: str, per_page: int = 10) -> list:
    """
    Execute a GitHub repository search API request, sorted by star count.
    
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
        "sort": "stars",
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

def _score_repo(repo: dict, now_utc: datetime) -> float:
    """
    Compute a composite quality score for a repository candidate.
    
    Scoring formula:
      - Star gravity:   log10(stars) * 2.0  (logarithmic to avoid mega-repo dominance)
      - Recency bonus:  0-3 points based on how recently the repo was pushed
      - Novelty bonus:  1.5 points if created within the last 30 days
      - Quality signal: 1.0 point if the repo has a description
    
    Args:
        repo (dict): Raw repository metadata from GitHub.
        now_utc (datetime): Current UTC datetime for freshness calculations.
        
    Returns:
        float: The composite quality score.
    """
    stars = max(repo.get("stargazers_count", 0), 1)
    score = math.log10(stars) * 2.0

    # Recency bonus based on last push
    pushed_str = repo.get("pushed_at") or repo.get("updated_at") or ""
    if pushed_str:
        try:
            pushed_dt = datetime.fromisoformat(pushed_str.replace("Z", "+00:00"))
            days_since_push = max((now_utc - pushed_dt).total_seconds() / 86400, 0)
            if days_since_push < 1:
                score += 3.0
            elif days_since_push < 3:
                score += 2.0
            elif days_since_push < 7:
                score += 1.0
        except (ValueError, TypeError):
            pass

    # Novelty bonus for genuinely new repos
    created_str = repo.get("created_at") or ""
    if created_str:
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if (now_utc - created_dt).days <= 30:
                score += 1.5
        except (ValueError, TypeError):
            pass

    # Quality signal: repos with descriptions are more likely to be intentional projects
    if repo.get("description"):
        score += 1.0

    return score

def _format_repo(repo: dict, seen_urls: set, now_utc: datetime) -> dict | None:
    """
    Validate quality guardrails, score, and format a candidate repository item.
    
    Filters out repositories that have no description or are below the minimum
    star threshold, and checks against the deduplication set to avoid duplicates
    within a run.
    
    Args:
        repo (dict): Raw repository metadata from GitHub.
        seen_urls (set): A tracking set of already processed repository URLs.
        now_utc (datetime): Current UTC datetime for scoring calculations.
        
    Returns:
        dict | None: A standardized dictionary for the digest, or None if rejected.
    """
    repo_url = repo.get("html_url")
    if not repo_url or repo_url in seen_urls:
        return None
    if not repo.get("description") or repo.get("stargazers_count", 0) < 50:
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
        "created_at": repo.get("created_at") or "",
        "_score": _score_repo(repo, now_utc)
    }

def _collect_repos(raw_repos: list, seen_urls: set, all_items: list, now_utc: datetime) -> int:
    """
    Process, format, and collect valid repositories from a raw API response.
    
    Args:
        raw_repos (list): The list of raw repository dictionaries from GitHub.
        seen_urls (set): The set of already encountered URLs for deduplication.
        all_items (list): The master list appending accepted repositories.
        now_utc (datetime): Current UTC datetime for scoring calculations.
        
    Returns:
        int: The number of repositories successfully validated and collected.
    """
    count = 0
    for repo in raw_repos:
        formatted = _format_repo(repo, seen_urls, now_utc)
        if formatted:
            all_items.append(formatted)
            count += 1
    return count

def fetch_github_repos(config: dict) -> list:
    """
    Fetch trending GitHub repositories using a multi-strategy quality-ranked approach.
    
    This fetcher applies three search strategies per topic/keyword, each targeting
    a different segment of the trending spectrum:
    
      1. Rising Stars:  Repos created in the last 7 days with >100 stars (breakout detection).
      2. Hot Updates:   Established repos pushed in the last 3 days with >5000 stars.
      3. Weekly Best:   Fallback — repos pushed in the last 14 days with >1000 stars
                        (only fires if strategies 1+2 yield fewer than 3 results).
    
    All strategies sort by stars on the API side and exclude forks and archived repos.
    Results are ranked by a composite quality score (star gravity + recency + novelty)
    rather than by raw date.
    
    Args:
        config (dict): The active configuration dictionary containing 'topics' and 'keywords'.
        
    Returns:
        list: A score-ranked list of standardized candidate repository dictionaries.
    """
    github_token = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    topics = config.get("topics", [])
    keywords = config.get("keywords", [])

    if not topics and not keywords:
        return []

    now_utc = datetime.now(timezone.utc)
    cutoff_7d = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_3d = (now_utc - timedelta(days=3)).strftime("%Y-%m-%d")
    cutoff_14d = (now_utc - timedelta(days=14)).strftime("%Y-%m-%d")
    
    # Common filters to exclude forks and archived repos
    base_filters = "fork:false archived:false"
    
    queries = [f"topic:{topic}" for topic in topics] + list(keywords)
    url = "https://api.github.com/search/repositories"
    
    all_items = []
    seen_urls = set()

    for q_base in queries:
        # Strategy 1 — Rising Stars: new repos gaining traction fast
        query_rising = f"{q_base} created:>{cutoff_7d} stars:>100 {base_filters}"
        _collect_repos(_search_repos(url, headers, query_rising), seen_urls, all_items, now_utc)
        
        # Strategy 2 — Hot Updates: high-quality established repos with very recent activity
        query_hot = f"{q_base} pushed:>{cutoff_3d} stars:>5000 {base_filters}"
        _collect_repos(_search_repos(url, headers, query_hot), seen_urls, all_items, now_utc)
        
        # Strategy 3 — Weekly Best (fallback): broader net if strategies 1+2 are thin
        if len(all_items) < 3:
            query_weekly = f"{q_base} pushed:>{cutoff_14d} stars:>1000 {base_filters}"
            _collect_repos(_search_repos(url, headers, query_weekly), seen_urls, all_items, now_utc)

    # Rank by composite quality score, not by raw date
    all_items.sort(key=lambda x: x.get("_score", 0), reverse=True)
    
    # Strip internal scoring field before returning
    for item in all_items:
        item.pop("_score", None)
    
    return all_items[:10]
