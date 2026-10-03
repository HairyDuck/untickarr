"""Persist settings to /data/settings.json."""
import json
import os
from pathlib import Path
from app.config import AppSettings

DATA_DIR = os.environ.get("DATA_DIR", "/data")
SETTINGS_PATH = Path(DATA_DIR) / "settings.json"


def load_settings() -> AppSettings:
    if not SETTINGS_PATH.exists():
        return AppSettings()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return AppSettings.model_validate(data)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        settings.model_dump_json(indent=2),
        encoding="utf-8",
    )
