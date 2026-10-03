"""Settings models and defaults."""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# When all files in a torrent are unwanted: remove only, blocklist only, or blocklist and search for replacement.
OnRemoveAllUnwanted = Literal["remove_only", "blocklist_only", "blocklist_and_search"]


class TransmissionSettings(BaseModel):
    enabled: bool = True
    host: str = "localhost"
    port: int = 9091
    path: str = "/transmission/rpc"
    use_ssl: bool = False
    username: Optional[str] = None
    password: Optional[str] = None


class SonarrSettings(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:8989"
    api_key: str = ""


class RadarrSettings(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:7878"
    api_key: str = ""


class PushoverSettings(BaseModel):
    enabled: bool = False
    user_key: str = ""
    api_token: str = ""
    # Which events to notify (only when enabled is True)
    notify_on_remove: bool = True   # When a torrent is removed (all files unwanted)
    notify_on_run_complete: bool = False  # Summary when a run finishes successfully
    notify_on_error: bool = True   # When a run fails


class AppSettings(BaseModel):
    """All app settings stored in /data/settings.json."""
    transmission: TransmissionSettings = Field(default_factory=TransmissionSettings)
    sonarr: SonarrSettings = Field(default_factory=SonarrSettings)
    radarr: RadarrSettings = Field(default_factory=RadarrSettings)
    pushover: PushoverSettings = Field(default_factory=PushoverSettings)
    # Tags to process (e.g. ["sonarr", "radarr"]). Only torrents with these labels are touched.
    managed_tags: List[str] = Field(default_factory=lambda: ["sonarr", "radarr"])
    # File extensions to untick / consider unwanted (lowercase, no leading dot in storage)
    blacklisted_extensions: List[str] = Field(
        default_factory=lambda: [
            "exe", "bat", "cmd", "com", "msi", "dll",
            "jpg", "jpeg", "png", "gif", "bmp", "webp", "ico", "svg",
            "nfo", "txt", "url", "html", "htm", "pdf", "doc", "docx",
            "sfv", "srr", "sample", "thumbs", "db",
        ]
    )
    # How often to run the cleaner (seconds). 0 = only manual.
    run_interval_seconds: int = 300
    # When all files are unwanted: remove_only | blocklist_only | blocklist_and_search
    on_remove_all_unwanted: OnRemoveAllUnwanted = "blocklist_only"
    # Safety: pause scheduled runs (manual Run now still works)
    scheduler_paused: bool = False
    # Ignore "Run now" for this many seconds after last run (0 = no cooldown)
    run_cooldown_seconds: int = 0
    # When removing a torrent: True = remove and delete data; False = remove from Transmission only (keep files)
    remove_delete_data: bool = True
    # If set: only consider "all unwanted -> remove" when torrent has at least one file with these extensions (e.g. mkv, mp4)
    whitelisted_extensions: List[str] = Field(default_factory=list)
    # Last run result for UI
    last_run_log: Optional[str] = None
    last_run_ok: Optional[bool] = None
    last_run_processed: Optional[int] = None
    last_run_removed: Optional[int] = None
