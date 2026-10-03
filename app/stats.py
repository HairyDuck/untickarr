"""Persist all-time stats: processed, removed, blocklisted, per tag and per extension."""
import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = os.environ.get("DATA_DIR", "/data")
STATS_PATH = Path(DATA_DIR) / "stats.json"


def _default_alltime() -> dict[str, Any]:
    return {
        "processed": 0,
        "removed": 0,
        "blocklisted": 0,
        "by_tag": {},
        "by_extension": {},
    }


def _ensure_counts(d: dict[str, int]) -> dict[str, int]:
    return {
        "processed": d.get("processed", 0),
        "removed": d.get("removed", 0),
        "blocklisted": d.get("blocklisted", 0),
    }


def load_alltime_stats() -> dict[str, Any]:
    """Return all-time stats: processed, removed, blocklisted, by_tag, by_extension."""
    if not STATS_PATH.exists():
        return _default_alltime()
    try:
        data = json.loads(STATS_PATH.read_text(encoding="utf-8"))
        out = _default_alltime()
        out["processed"] = int(data.get("processed", 0))
        out["removed"] = int(data.get("removed", 0))
        out["blocklisted"] = int(data.get("blocklisted", 0))
        for tag, counts in (data.get("by_tag") or {}).items():
            if isinstance(counts, dict):
                out["by_tag"][str(tag)] = _ensure_counts(counts)
        for ext, counts in (data.get("by_extension") or {}).items():
            if isinstance(counts, dict):
                out["by_extension"][str(ext)] = _ensure_counts(counts)
        return out
    except Exception:
        return _default_alltime()


def _merge_run_into_alltime(alltime: dict[str, Any], run: dict[str, Any]) -> None:
    """Merge run stats (by_tag, by_extension, processed, removed, blocklisted) into alltime."""
    alltime["processed"] = alltime.get("processed", 0) + run.get("processed", 0)
    alltime["removed"] = alltime.get("removed", 0) + run.get("removed", 0)
    alltime["blocklisted"] = alltime.get("blocklisted", 0) + run.get("blocklisted", 0)
    by_tag = alltime.setdefault("by_tag", {})
    for tag, counts in (run.get("by_tag") or {}).items():
        t = by_tag.setdefault(tag, {"processed": 0, "removed": 0, "blocklisted": 0})
        t["processed"] = t.get("processed", 0) + counts.get("processed", 0)
        t["removed"] = t.get("removed", 0) + counts.get("removed", 0)
        t["blocklisted"] = t.get("blocklisted", 0) + counts.get("blocklisted", 0)
    by_ext = alltime.setdefault("by_extension", {})
    for ext, counts in (run.get("by_extension") or {}).items():
        e = by_ext.setdefault(ext, {"processed": 0, "removed": 0, "blocklisted": 0})
        e["processed"] = e.get("processed", 0) + counts.get("processed", 0)
        e["removed"] = e.get("removed", 0) + counts.get("removed", 0)
        e["blocklisted"] = e.get("blocklisted", 0) + counts.get("blocklisted", 0)


def add_run_stats(run_stats: dict[str, Any]) -> None:
    """Persist a run's stats into all-time stats (only call for real runs, not dry run)."""
    alltime = load_alltime_stats()
    _merge_run_into_alltime(alltime, run_stats)
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(alltime, indent=2),
        encoding="utf-8",
    )
