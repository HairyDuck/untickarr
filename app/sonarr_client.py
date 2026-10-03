"""Sonarr API client for blocklisting releases and triggering episode search."""
import httpx
from app.config import SonarrSettings


def _headers(settings: SonarrSettings) -> dict:
    return {"X-Api-Key": settings.api_key, "Content-Type": "application/json"}


def test_connection(settings: SonarrSettings) -> tuple[bool, str]:
    """Test connection to Sonarr. Returns (success, message)."""
    if not settings.enabled:
        return False, "Sonarr is disabled in settings."
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


def blocklist_release(settings: SonarrSettings, release_title: str) -> tuple[bool, str]:
    """
    Add a release to Sonarr's blocklist so it won't be grabbed again.
    Returns (success, message).
    """
    if not settings.enabled or not settings.api_key:
        return False, "Sonarr disabled or missing API key"
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


def find_episode_ids_from_queue(settings: SonarrSettings, release_title: str) -> list[int]:
    """
    Find episode IDs for a release by matching its title in the queue.
    Returns list of episode IDs (may be empty if not found).
    """
    if not settings.enabled or not settings.api_key:
        return []
    base = settings.base_url.rstrip("/")
    url = f"{base}/api/v3/queue"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_headers(settings), params={"includeUnknownSeriesItems": "false"})
        if r.status_code != 200:
            return []
        data = r.json()
        records = data.get("records") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        title_lower = (release_title or "").strip().lower()
        for rec in records:
            t = (rec.get("title") or rec.get("downloadTitle") or "").strip().lower()
            if title_lower in t or t in title_lower:
                episodes = rec.get("episodes") or []
                ids = []
                for ep in episodes:
                    eid = ep.get("id") if isinstance(ep, dict) else (ep if isinstance(ep, int) else None)
                    if eid is not None:
                        ids.append(int(eid))
                if ids:
                    return ids
        return []
    except Exception:
        return []


def trigger_episode_search(settings: SonarrSettings, episode_ids: list[int]) -> tuple[bool, str]:
    """
    Trigger EpisodeSearch command for the given episode IDs.
    Returns (success, message).
    """
    if not settings.enabled or not settings.api_key or not episode_ids:
        return False, "Sonarr disabled, no API key, or no episode IDs"
    base = settings.base_url.rstrip("/")
    url = f"{base}/api/v3/command"
    body = {"name": "EpisodeSearch", "episodeIds": list(episode_ids)}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json=body, headers=_headers(settings))
        if r.status_code in (200, 201):
            return True, "Search triggered"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)
