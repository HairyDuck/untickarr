"""Pushover notification client."""
import httpx
from app.config import PushoverSettings


def test_connection(settings: PushoverSettings) -> tuple[bool, str]:
    """Test Pushover by sending a silent test message (priority -2). Returns (success, message)."""
    if not settings.enabled:
        return False, "Pushover is disabled in settings."
    if not (settings.user_key or "").strip() or not (settings.api_token or "").strip():
        return False, "User key and API token are required."
    ok, msg = send(
        settings,
        title="Untickarr test",
        message="Connection test from Untickarr.",
        priority=-2,
    )
    return ok, msg


def send(settings: PushoverSettings, title: str, message: str, priority: int = 0) -> tuple[bool, str]:
    """
    Send a Pushover notification. priority: -2 to 2 (0 = normal).
    Returns (success, message).
    """
    if not settings.enabled or not settings.user_key or not settings.api_token:
        return False, "Pushover disabled or missing keys"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": settings.api_token,
                    "user": settings.user_key,
                    "title": title[:250],
                    "message": message[:1024],
                    "priority": priority,
                },
            )
        if r.status_code == 200:
            return True, "Sent"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)
