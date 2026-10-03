"""Radarr API client for blocklisting releases and triggering movie search."""
import httpx
from app.config import RadarrSettings


def _headers(settings: RadarrSettings) -> dict:
    return {"X-Api-Key": settings.api_key, "Content-Type": "application/json"}


def test_connection(settings: RadarrSettings) -> tuple[bool, str]:
    """Test connection to Radarr. Returns (success, message)."""
    if not settings.enabled:
        return False, "Radarr is disabled in settings."
    if not (settings.api_key or "").strip():
        return False, "API key is required."
    base = (settings.base_url or "").rstrip("/")
    if not base:
        return False, "Base URL is required."
    url = f"{base}/api/v3/system/status"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, headers=_headers(settings))
        if r.status_code == 200:
            return True, "Connected successfully."
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def blocklist_release(settings: RadarrSettings, release_title: str) -> tuple[bool, str]:
    """
    Add a release to Radarr's blocklist so it won't be grabbed again.
    Returns (success, message).
    """
    if not settings.enabled or not settings.api_key:
        return False, "Radarr disabled or missing API key"
    base = settings.base_url.rstrip("/")
    url = f"{base}/api/v3/blocklist"
    body = {"title": release_title, "sourceTitle": release_title}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json=body, headers=_headers(settings))
        if r.status_code in (200, 201):
            return True, "Blocklisted"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def find_movie_id_from_queue(settings: RadarrSettings, release_title: str) -> int | None:
    """
    Find movie ID for a release by matching its title in the queue.
    Returns movie ID or None.
    """
    if not settings.enabled or not settings.api_key:
        return None
    base = settings.base_url.rstrip("/")
    url = f"{base}/api/v3/queue"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_headers(settings))
        if r.status_code != 200:
            return None
        data = r.json()
        records = data.get("records") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        title_lower = (release_title or "").strip().lower()
        for rec in records:
            t = (rec.get("title") or rec.get("downloadTitle") or "").strip().lower()
            if title_lower in t or t in title_lower:
                mid = rec.get("movieId")
                if mid is None and isinstance(rec.get("movie"), dict):
                    mid = rec["movie"].get("id")
                if mid is not None:
                    return int(mid)
        return None
    except Exception:
        return None


def trigger_movie_search(settings: RadarrSettings, movie_ids: list[int]) -> tuple[bool, str]:
    """
    Trigger MoviesSearch command for the given movie IDs.
    Returns (success, message).
    """
    if not settings.enabled or not settings.api_key or not movie_ids:
        return False, "Radarr disabled, no API key, or no movie IDs"
    base = settings.base_url.rstrip("/")
    url = f"{base}/api/v3/command"
    body = {"name": "MoviesSearch", "movieIds": list(movie_ids)}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json=body, headers=_headers(settings))
        if r.status_code in (200, 201):
            return True, "Search triggered"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)
