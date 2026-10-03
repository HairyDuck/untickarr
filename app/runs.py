"""Persist run history for visible logs."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = os.environ.get("DATA_DIR", "/data")
RUN_HISTORY_PATH = Path(DATA_DIR) / "run_history.json"
# Retention: keep last N runs that ran regardless, and last M that did something (processed/removed > 0)
MAX_RECENT_ANY = 10
MAX_DID_SOMETHING = 20
MAX_ENTRIES_CAP = 50  # hard cap on total stored


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _did_something(entry: dict) -> bool:
    """True if this run processed or removed any torrents."""
    p = entry.get("processed")
    r = entry.get("removed")
    if p is None and r is None:
        return False
    return (p or 0) + (r or 0) > 0


def _trim_entries(entries: list[dict]) -> list[dict]:
    """Keep last MAX_RECENT_ANY runs regardless, and last MAX_DID_SOMETHING that did something."""
    if not entries:
        return []
    # Newest first (entries already in that order when we load after insert(0, entry))
    recent_any_ats = {e.get("at") for e in entries[:MAX_RECENT_ANY] if e.get("at")}
    did_something = [e for e in entries if _did_something(e)][:MAX_DID_SOMETHING]
    did_something_ats = {e.get("at") for e in did_something if e.get("at")}
    keep_ats = recent_any_ats | did_something_ats
    result = [e for e in entries if e.get("at") in keep_ats]
    return result[:MAX_ENTRIES_CAP]


def append_run(ok: bool, log: str, processed: int = 0, removed: int = 0) -> dict:
    entry = {"at": _now_iso(), "ok": ok, "log": log or "", "processed": processed, "removed": removed}
    RUN_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if RUN_HISTORY_PATH.exists():
        try:
            data = json.loads(RUN_HISTORY_PATH.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else []
        except Exception:
            entries = []
    entries.insert(0, entry)
    trimmed = _trim_entries(entries)
    RUN_HISTORY_PATH.write_text(
        json.dumps(trimmed, indent=2),
        encoding="utf-8",
    )
    return entry


def get_run_history(limit: int = 20) -> list[dict]:
    """Return recent runs, newest first. Each dict has at, ok, log."""
    if not RUN_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(RUN_HISTORY_PATH.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else []
        return entries[:limit]
    except Exception:
        return []
