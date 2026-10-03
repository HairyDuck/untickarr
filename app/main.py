"""FastAPI app: settings API, run job, static UI."""
import asyncio
import time as _time
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import AppSettings
from app.store import load_settings, save_settings
from app.cleaner import run_cleaner
from app.runs import append_run, get_run_history
from app.stats import load_alltime_stats, add_run_stats
from app.transmission_client import test_connection as test_transmission, get_diagnostic as transmission_diagnostic
from app.sonarr_client import test_connection as test_sonarr
from app.radarr_client import test_connection as test_radarr
from app.pushover_client import test_connection as test_pushover, send as pushover_send

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_bg_task = None
_last_run_at_ts: float | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background runner if interval > 0 and not paused."""
    global _bg_task

    async def loop():
        global _last_run_at_ts
        while True:
            s = load_settings()
            interval = max(s.run_interval_seconds or 0, 0)
            paused = getattr(s, "scheduler_paused", False)
            if interval > 0 and not paused:
                ok, log, processed, removed, run_stats = run_cleaner(s)
                _last_run_at_ts = _time.time()
                s.last_run_ok = ok
                s.last_run_log = log
                s.last_run_processed = processed
                s.last_run_removed = removed
                save_settings(s)
                append_run(ok, log, processed, removed)
                add_run_stats(run_stats)
                _maybe_send_run_notification(s, ok, log)
            await asyncio.sleep(interval if interval > 0 else 60)

    _bg_task = asyncio.create_task(loop())
    yield
    if _bg_task:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Untickarr", lifespan=lifespan)


# --- API models ---
class TransmissionSettingsUpdate(BaseModel):
    enabled: bool = True
    host: str = "localhost"
    port: int = 9091
    path: str = "/transmission/"
    use_ssl: bool = False
    username: str | None = None
    password: str | None = None


class SonarrSettingsUpdate(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:8989"
    api_key: str = ""


class RadarrSettingsUpdate(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:7878"
    api_key: str = ""


class PushoverSettingsUpdate(BaseModel):
    enabled: bool = False
    user_key: str = ""
    api_token: str = ""
    notify_on_remove: bool | None = None
    notify_on_run_complete: bool | None = None
    notify_on_error: bool | None = None


class SettingsUpdate(BaseModel):
    transmission: TransmissionSettingsUpdate | None = None
    sonarr: SonarrSettingsUpdate | None = None
    radarr: RadarrSettingsUpdate | None = None
    pushover: PushoverSettingsUpdate | None = None
    managed_tags: list[str] | None = None
    blacklisted_extensions: list[str] | None = None
    whitelisted_extensions: list[str] | None = None
    run_interval_seconds: int | None = None
    on_remove_all_unwanted: Literal["remove_only", "blocklist_only", "blocklist_and_search"] | None = None
    scheduler_paused: bool | None = None
    run_cooldown_seconds: int | None = None
    remove_delete_data: bool | None = None


# --- Routes ---
@app.get("/api/settings")
def api_get_settings():
    s = load_settings()
    out = s.model_dump()
    out["run_history"] = get_run_history(limit=30)
    out["last_run_at"] = out["run_history"][0]["at"] if out["run_history"] else None
    out["alltime_stats"] = load_alltime_stats()
    return out


@app.post("/api/settings")
def api_save_settings(body: SettingsUpdate):
    s = load_settings()
    d = body.model_dump(exclude_none=True)
    if "transmission" in d and d["transmission"]:
        s.transmission = s.transmission.model_validate(
            {**s.transmission.model_dump(), **d["transmission"]}
        )
    if "sonarr" in d and d["sonarr"]:
        s.sonarr = s.sonarr.model_validate({**s.sonarr.model_dump(), **d["sonarr"]})
    if "radarr" in d and d["radarr"]:
        s.radarr = s.radarr.model_validate({**s.radarr.model_dump(), **d["radarr"]})
    if "pushover" in d and d["pushover"]:
        s.pushover = s.pushover.model_validate(
            {**s.pushover.model_dump(), **d["pushover"]}
        )
    if "managed_tags" in d:
        s.managed_tags = d["managed_tags"] or []
    if "blacklisted_extensions" in d:
        s.blacklisted_extensions = d["blacklisted_extensions"] or []
    if "run_interval_seconds" in d:
        s.run_interval_seconds = d["run_interval_seconds"]
    if "on_remove_all_unwanted" in d and d["on_remove_all_unwanted"] in ("remove_only", "blocklist_only", "blocklist_and_search"):
        s.on_remove_all_unwanted = d["on_remove_all_unwanted"]
    if "scheduler_paused" in d:
        s.scheduler_paused = bool(d["scheduler_paused"])
    if "run_cooldown_seconds" in d:
        v = d["run_cooldown_seconds"]
        s.run_cooldown_seconds = max(0, int(v)) if v is not None else 0
    if "remove_delete_data" in d:
        s.remove_delete_data = bool(d["remove_delete_data"])
    if "whitelisted_extensions" in d:
        s.whitelisted_extensions = [x for x in (d["whitelisted_extensions"] or []) if isinstance(x, str) and x.strip()]
    save_settings(s)
    return {"ok": True}


def _maybe_send_run_notification(settings: AppSettings, ok: bool, log: str):
    """Send Pushover run complete or error if enabled and flags allow."""
    p = settings.pushover
    if not p.enabled or not (p.user_key and p.api_token):
        return
    if ok and p.notify_on_run_complete:
        pushover_send(p, title="Untickarr: Run complete", message=log or "Run finished.", priority=0)
    elif not ok and p.notify_on_error:
        pushover_send(p, title="Untickarr: Run error", message=log or "Run failed.", priority=1)
    return


@app.post("/api/run")
def api_run_now():
    global _last_run_at_ts
    s = load_settings()
    cooldown = getattr(s, "run_cooldown_seconds", 0) or 0
    if cooldown > 0 and _last_run_at_ts is not None:
        elapsed = _time.time()
        if (elapsed - _last_run_at_ts) < cooldown:
            wait = max(0, cooldown - int(elapsed - _last_run_at_ts))
            raise HTTPException(
                status_code=429,
                detail=f"Run cooldown active. Wait {wait}s before running again.",
            )
    ok, log, processed, removed, run_stats = run_cleaner(s)
    _last_run_at_ts = _time.time()
    s.last_run_ok = ok
    s.last_run_log = log
    s.last_run_processed = processed
    s.last_run_removed = removed
    save_settings(s)
    entry = append_run(ok, log, processed, removed)
    add_run_stats(run_stats)
    _maybe_send_run_notification(s, ok, log)
    return {"ok": ok, "log": log, "at": entry.get("at"), "processed": processed, "removed": removed}


@app.get("/api/status")
def api_status():
    s = load_settings()
    history = get_run_history(limit=1)
    last_at = history[0]["at"] if history else None
    interval = max(s.run_interval_seconds or 0, 0)
    paused = getattr(s, "scheduler_paused", False)
    return {
        "last_run_ok": s.last_run_ok,
        "last_run_log": s.last_run_log,
        "last_run_at": last_at,
        "last_run_processed": getattr(s, "last_run_processed", None),
        "last_run_removed": getattr(s, "last_run_removed", None),
        "run_interval_seconds": s.run_interval_seconds,
        "scheduler_paused": paused,
        "next_run_in_seconds": None if paused or interval <= 0 else interval,
    }


@app.get("/api/logs")
def api_logs(limit: int = 30):
    """Return recent run logs for the UI."""
    return {"run_history": get_run_history(limit=min(limit, 50))}


@app.get("/api/stats")
def api_stats():
    """Return all-time stats: processed, removed, blocklisted, by_tag, by_extension."""
    return load_alltime_stats()


@app.get("/health")
@app.get("/api/health")
def api_health():
    """Health check: tests Transmission connection. Returns 200 if OK, 503 if not."""
    s = load_settings()
    ok, msg = test_transmission(s.transmission)
    if ok:
        return {"status": "ok", "transmission": msg}
    raise HTTPException(status_code=503, detail=msg or "Transmission unreachable")


@app.post("/api/preview")
def api_preview():
    """Run cleaner in dry-run mode; no changes made. Returns log and counts."""
    s = load_settings()
    ok, log, processed, removed, _ = run_cleaner(s, dry_run=True)
    return {"ok": ok, "log": log, "processed": processed, "removed": removed}


@app.get("/api/settings/export")
def api_export_settings():
    """Export current settings as JSON for backup/import elsewhere."""
    s = load_settings()
    return s.model_dump()


@app.post("/api/settings/import")
def api_import_settings(body: dict):
    """Import settings from JSON (full replace after validation)."""
    try:
        s = AppSettings.model_validate(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    save_settings(s)
    return {"ok": True}


@app.get("/api/logs/export")
def api_export_logs(format: str = "txt"):
    """Export run history as plain text or csv. format: txt | csv"""
    history = get_run_history(limit=500)
    if (format or "").lower() == "csv":
        lines = ["at,ok,processed,removed,log_preview"]
        for h in history:
            at = h.get("at") or ""
            ok_val = "ok" if h.get("ok") else "error"
            proc = h.get("processed", "")
            rem = h.get("removed", "")
            preview = (h.get("log") or "")[:200].replace('"', '""').replace("\n", " ")
            lines.append(f'"{at}","{ok_val}",{proc},{rem},"{preview}"')
        return PlainTextResponse(
            "\n".join(lines),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=untickarr-logs.csv"},
        )
    lines = []
    for h in history:
        at = h.get("at") or ""
        ok_val = "OK" if h.get("ok") else "ERROR"
        proc = h.get("processed", "")
        rem = h.get("removed", "")
        lines.append(f"[{at}] {ok_val} processed={proc} removed={rem}")
        lines.append((h.get("log") or "").strip())
        lines.append("")
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=untickarr-logs.txt"},
    )


@app.get("/api/test")
def api_test_connections(service: str = "all"):
    """
    Test connection to one or all services. Uses current saved settings.
    service: transmission | sonarr | radarr | pushover | all
    Returns e.g. { "transmission": { "ok": true, "message": "..." }, ... }
    """
    s = load_settings()
    result = {}
    service = (service or "all").strip().lower()
    if service in ("all", "transmission"):
        ok, msg = test_transmission(s.transmission)
        result["transmission"] = {"ok": ok, "message": msg}
    if service in ("all", "sonarr"):
        ok, msg = test_sonarr(s.sonarr)
        result["sonarr"] = {"ok": ok, "message": msg}
    if service in ("all", "radarr"):
        ok, msg = test_radarr(s.radarr)
        result["radarr"] = {"ok": ok, "message": msg}
    if service in ("all", "pushover"):
        ok, msg = test_pushover(s.pushover)
        result["pushover"] = {"ok": ok, "message": msg}
    return result


@app.get("/api/transmission/diagnostic")
def api_transmission_diagnostic():
    """
    Connect to Transmission with current settings and return raw data for each torrent:
    labels_raw (what the API returns), labels_parsed (what we use for tag matching), file_count, file_names.
    Use this to debug why torrents are not found or files appear empty.
    """
    s = load_settings()
    ok, message, torrents = transmission_diagnostic(s.transmission)
    if not ok:
        raise HTTPException(status_code=503, detail=message)
    return {"ok": True, "message": message, "torrents": torrents}


# --- Static UI ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def index():
        return {"message": "Static files not found. Mount /static or add index.html."}
