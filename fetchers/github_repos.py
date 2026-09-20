import os
import requests
from datetime import datetime, timedelta, timezone

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
    
    queries = []
    for topic in topics:
        queries.append(f"topic:{topic}")
    for kw in keywords:
        queries.append(kw)
        
    url = "https://api.github.com/search/repositories"
    
    all_items = []
    seen_urls = set()

    for q_base in queries:
        # Try Primary: created in last 7 days, stars > 500
        query_primary = f"{q_base} created:>{created_after_7} stars:>500"
        params_primary = {
            "q": query_primary,
            "sort": "stars",
            "order": "desc",
            "per_page": 3
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params_primary, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            
            # If not enough new repos, try fallback: active this month, stars > 2000
            if len(items) < 3:
                query_fallback = f"{q_base} pushed:>{pushed_after_30} stars:>2000"
                params_fallback = {
                    "q": query_fallback,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 3
                }
                resp_f = requests.get(url, headers=headers, params=params_fallback, timeout=10)
                if resp_f.status_code == 200:
                    fallback_data = resp_f.json()
                    items.extend(fallback_data.get("items", []))
            
            for repo in items:
                if repo["html_url"] in seen_urls:
                    continue
                # Quality guardrails
                if not repo.get("description") or repo.get("stargazers_count", 0) < 500:
                    continue
                seen_urls.add(repo["html_url"])
                all_items.append({
                    "source": "GitHub",
                    "id": repo["html_url"],
                    "url": repo["html_url"],
                    "title": repo["full_name"],
                    "summary": repo.get("description") or "No description provided.",
                    "stars": repo.get("stargazers_count", 0),
                    "pushed_at": repo.get("pushed_at") or repo.get("created_at") or "",
                    "created_at": repo.get("created_at") or ""
                })
        except requests.RequestException as e:
            print(f"[github_repos] Failed to fetch repositories for {q_base}: {e}")
            continue

    # Sort all collected items by recency descending and take top 10
    all_items.sort(key=lambda x: x.get("pushed_at") or x.get("created_at") or "", reverse=True)
    return all_items[:10]
