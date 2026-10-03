"""Transmission RPC client wrapper."""
import transmission_rpc
from app.config import TransmissionSettings


def _normalize_host(host: str) -> str:
    """Strip scheme and port from host so only hostname/IP is used (e.g. http://192.168.1.248:9091 -> 192.168.1.248)."""
    if not host or not host.strip():
        return "localhost"
    s = host.strip()
    for prefix in ("https://", "http://"):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :].lstrip()
            break
    if "/" in s:
        s = s.split("/", 1)[0]
    if ":" in s:
        s = s.rsplit(":", 1)[0]
    return s or "localhost"


def make_client(settings: TransmissionSettings) -> transmission_rpc.Client:
    path = (settings.path or "/transmission/rpc").strip().rstrip("/") or "/transmission/rpc"
    host = _normalize_host(settings.host)
    return transmission_rpc.Client(
        host=host,
        port=settings.port,
        path=path,
        protocol="https" if settings.use_ssl else "http",
        username=settings.username or None,
        password=settings.password or None,
    )


def _torrent_labels(t) -> list:
    """Get label/group/category for a torrent (vendor-dependent)."""
    for attr in ("labels", "group", "category"):
        val = getattr(t, attr, None)
        if val is None:
            continue
        if isinstance(val, str):
            return [val] if val else []
        if isinstance(val, list):
            return val
    return []


# Request these fields so we get label/group/category and file list.
# transmission_rpc.Torrent.get_files() requires "files", "priorities", and "wanted".
_TORRENT_FIELDS = ["id", "name", "labels", "group", "category", "files", "priorities", "wanted"]


def get_torrents_with_tags(client: transmission_rpc.Client, tags: list[str]):
    """Get all torrents whose label is in tags. Returns list of (torrent, file_list)."""
    if not tags:
        return []
    try:
        # Explicitly request label-related fields so we get them from the RPC (some builds need this)
        torrents = client.get_torrents(arguments=_TORRENT_FIELDS)
    except Exception:
        try:
            torrents = client.get_torrents()
        except Exception:
            return []
    out = []
    for t in torrents:
        labels = _torrent_labels(t)
        # Match if tag equals label, or either contains the other (e.g. tag "tv-sonarr" matches label "sonarr")
        tag_match = any(
            tag.lower() == l.lower()
            or tag.lower() in l.lower()
            or l.lower() in tag.lower()
            for tag in tags
            for l in labels
        )
        if not tag_match:
            continue
        try:
            file_list = t.get_files()
        except Exception:
            continue
        if not isinstance(file_list, list):
            file_list = list(file_list) if file_list else []
        out.append((t, file_list))
    return out


def set_files_unwanted(client: transmission_rpc.Client, torrent_id: int, file_ids: list[int]):
    """Untick (set unwanted) the given file IDs."""
    client.change_torrent(torrent_id, files_unwanted=file_ids)


def remove_torrent(client: transmission_rpc.Client, torrent_id: int, delete_data: bool = True):
    """Remove torrent and optionally delete local data."""
    client.remove_torrent(torrent_id, delete_data=delete_data)


def test_connection(settings: TransmissionSettings) -> tuple[bool, str]:
    """Test connection to Transmission. Returns (success, message)."""
    if not settings.enabled:
        return False, "Transmission is disabled in settings."
    try:
        client = make_client(settings)
        client.get_torrents()
        return True, "Connected successfully."
    except Exception as e:
        return False, str(e)


def get_diagnostic(settings: TransmissionSettings) -> tuple[bool, str, list | None]:
    """
    Fetch all torrents and return raw label/file info for debugging.
    Returns (success, message, list of {id, name, labels_raw, labels_parsed, file_count, file_names}).
    """
    if not settings.enabled:
        return False, "Transmission is disabled.", None
    try:
        client = make_client(settings)
        torrents = client.get_torrents(arguments=_TORRENT_FIELDS)
    except Exception as e:
        return False, str(e), None
    out = []
    for t in torrents:
        name = getattr(t, "name", None) or str(getattr(t, "id", "?"))
        labels_raw = {
            "labels": getattr(t, "labels", None),
            "group": getattr(t, "group", None),
            "category": getattr(t, "category", None),
        }
        labels_parsed = _torrent_labels(t)
        try:
            file_list = t.get_files()
            if not isinstance(file_list, list):
                file_list = list(file_list) if file_list else []
        except Exception:
            file_list = []
        file_names = [getattr(f, "name", "") or "" for f in file_list]
        out.append({
            "id": getattr(t, "id", None),
            "name": name,
            "labels_raw": labels_raw,
            "labels_parsed": labels_parsed,
            "file_count": len(file_list),
            "file_names": file_names,
        })
    return True, f"Found {len(out)} torrent(s).", out
