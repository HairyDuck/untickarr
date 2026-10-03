"""
Core logic: for each managed-tag torrent, untick blacklisted files or remove torrent if all blacklisted.
"""
from app.config import AppSettings
from app.transmission_client import (
    make_client,
    get_torrents_with_tags,
    set_files_unwanted,
    remove_torrent,
)
from app.sonarr_client import (
    blocklist_release as sonarr_blocklist,
    find_episode_ids_from_queue as sonarr_find_episode_ids,
    trigger_episode_search as sonarr_trigger_search,
)
from app.radarr_client import (
    blocklist_release as radarr_blocklist,
    find_movie_id_from_queue as radarr_find_movie_id,
    trigger_movie_search as radarr_trigger_search,
)
from app.pushover_client import send as pushover_send


def _extension_set(extensions: list[str]) -> set[str]:
    """Normalize to set of lowercase extensions without leading dot."""
    out = set()
    for ext in extensions or []:
        e = (ext or "").strip().lstrip(".").lower()
        if e:
            out.add(e)
    return out


def _file_extension(name: str) -> str:
    """Get lowercase extension without dot from filename."""
    if not name or "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def _has_whitelisted_file(file_info: list, whitelist: set[str]) -> bool:
    """True if any file has an extension in whitelist."""
    if not whitelist:
        return True
    for _, fname, _ in file_info:
        if _file_extension(fname) in whitelist:
            return True
    return False


def _inc(d: dict, key: str, subkey: str, amount: int = 1) -> None:
    entry = d.setdefault(key, {"processed": 0, "removed": 0, "blocklisted": 0})
    entry[subkey] = entry.get(subkey, 0) + amount


def run_cleaner(settings: AppSettings, dry_run: bool = False) -> tuple[bool, str, int, int, dict]:
    """
    Run one pass: process all torrents with managed tags.
    Returns (success, log_text, processed_count, removed_count, run_stats).
    run_stats: processed, removed, blocklisted, by_tag, by_extension (for all-time aggregation).
    When dry_run=True, no changes are made; log describes what would be done.
    """
    log_lines = []
    processed = 0
    removed = 0
    blocklisted = 0
    by_tag: dict[str, dict[str, int]] = {}
    by_extension: dict[str, dict[str, int]] = {}
    run_stats: dict = {"processed": 0, "removed": 0, "blocklisted": 0, "by_tag": by_tag, "by_extension": by_extension}
    if not settings.transmission.enabled:
        return True, "Transmission disabled in settings.", 0, 0, run_stats

    ext_blacklist = _extension_set(settings.blacklisted_extensions)
    if not ext_blacklist:
        log_lines.append("No blacklisted extensions configured; nothing to do.")
        return True, "\n".join(log_lines), 0, 0, run_stats

    ext_whitelist = _extension_set(getattr(settings, "whitelisted_extensions", None) or [])
    delete_data = getattr(settings, "remove_delete_data", True) if not dry_run else True

    try:
        client = make_client(settings.transmission)
    except Exception as e:
        log_lines.append(f"Failed to connect to Transmission: {e}")
        return False, "\n".join(log_lines), 0, 0, run_stats

    managed = [t.strip() for t in (settings.managed_tags or []) if t.strip()]
    if not managed:
        log_lines.append("No managed tags configured; nothing to do.")
        return True, "\n".join(log_lines), 0, 0, run_stats

    try:
        torrents_files = get_torrents_with_tags(client, managed)
    except Exception as e:
        log_lines.append(f"Failed to get torrents: {e}")
        return False, "\n".join(log_lines), 0, 0, run_stats

    prefix = "[DRY RUN] " if dry_run else ""
    log_lines.append(f"{prefix}Found {len(torrents_files)} torrent(s) with tags {managed}.")
    log_lines.append(f"Blacklisted extensions: {sorted(ext_blacklist)}.")

    for torrent, file_list in torrents_files:
        name = getattr(torrent, "name", None) or str(torrent.id)
        labels = getattr(torrent, "labels", None) or getattr(torrent, "group", []) or []
        if isinstance(labels, str):
            labels = [labels]
        tag = (labels[0] if labels else "").lower()

        # Build list of (file_id, name, is_blacklisted)
        file_info = []
        for f in file_list:
            fid = getattr(f, "id", None)
            fname = getattr(f, "name", "") or ""
            ext = _file_extension(fname)
            blacklisted = ext in ext_blacklist
            file_info.append((fid, fname, blacklisted))

        # If API returned no files (e.g. single-file torrent when "files" wasn't requested), treat torrent name as the single file
        if not file_info and name:
            ext = _file_extension(name)
            blacklisted = ext in ext_blacklist
            file_info.append((0, name, blacklisted))
            log_lines.append(f"  Torrent: {name} (using torrent name as single file; API returned no file list)")

        # Log every file: name, extension, and whether it matched the blacklist
        if not (log_lines and "using torrent name as single file" in log_lines[-1]):
            log_lines.append(f"  Torrent: {name}")
        for fid, fname, blacklisted in file_info:
            ext = _file_extension(fname)
            ext_display = f".{ext}" if ext else "(no extension)"
            match_status = "blacklisted" if blacklisted else "kept"
            log_lines.append(f"    - {fname}  ext={ext_display}  -> {match_status}")

        wanted = [(fid, n, b) for fid, n, b in file_info if not b]
        unwanted = [(fid, n, b) for fid, n, b in file_info if b]

        if not unwanted:
            log_lines.append(f"    (no blacklisted files; skipping)")
            continue

        processed += 1
        blacklisted_exts_here = {_file_extension(n) for (_, n, _) in unwanted if _file_extension(n)}
        _inc(by_tag, tag, "processed")
        for ext in blacklisted_exts_here:
            _inc(by_extension, ext, "processed")

        if not wanted:
            # All files unwanted -> remove (if whitelist allows)
            if not _has_whitelisted_file(file_info, ext_whitelist):
                log_lines.append(f"Skipped (no whitelisted extension): {name}")
                continue
            behavior = getattr(settings, "on_remove_all_unwanted", None) or "blocklist_only"
            log_lines.append(f"{prefix}Removing torrent (all unwanted): {name}" + (" (keep files)" if not delete_data else ""))
            if not dry_run:
                try:
                    remove_torrent(client, torrent.id, delete_data=delete_data)
                except Exception as e:
                    log_lines.append(f"  Error removing: {e}")
                    continue
            removed += 1
            _inc(by_tag, tag, "removed")
            for ext in blacklisted_exts_here:
                _inc(by_extension, ext, "removed")

            pushover_msg = f"All files unwanted; removed: {name}"
            if behavior == "remove_only":
                log_lines.append("  Remove only (no blocklist).")
                pushover_msg = f"Removed from download client (not blocklisted): {name}"
            else:
                # blocklist_only or blocklist_and_search (skip API calls in dry run)
                # Tags are typically "tv-sonarr" / "tv-radarr"; match any tag containing "sonarr" or "radarr"
                is_sonarr = "sonarr" in tag and settings.sonarr.enabled
                is_radarr = "radarr" in tag and settings.radarr.enabled
                if is_sonarr and not is_radarr:
                    if not dry_run:
                        ok, msg = sonarr_blocklist(settings.sonarr, name)
                        log_lines.append(f"  Sonarr blocklist: {msg}")
                        blocklisted += 1
                        _inc(by_tag, tag, "blocklisted")
                        for ext in blacklisted_exts_here:
                            _inc(by_extension, ext, "blocklisted")
                        if behavior == "blocklist_and_search":
                            episode_ids = sonarr_find_episode_ids(settings.sonarr, name)
                            if episode_ids:
                                sok, smsg = sonarr_trigger_search(settings.sonarr, episode_ids)
                                log_lines.append(f"  Sonarr search: {smsg}")
                            else:
                                log_lines.append("  Sonarr search: no episode IDs found in queue")
                    else:
                        log_lines.append("  Would blocklist in Sonarr" + (" and trigger search" if behavior == "blocklist_and_search" else "") + ".")
                    pushover_msg = f"Removed and blocklisted: {name}" if behavior == "blocklist_only" else f"Removed, blocklisted, and search triggered: {name}"
                elif is_radarr:
                    if not dry_run:
                        ok, msg = radarr_blocklist(settings.radarr, name)
                        log_lines.append(f"  Radarr blocklist: {msg}")
                        blocklisted += 1
                        _inc(by_tag, tag, "blocklisted")
                        for ext in blacklisted_exts_here:
                            _inc(by_extension, ext, "blocklisted")
                        if behavior == "blocklist_and_search":
                            movie_id = radarr_find_movie_id(settings.radarr, name)
                            if movie_id:
                                rok, rmsg = radarr_trigger_search(settings.radarr, [movie_id])
                                log_lines.append(f"  Radarr search: {rmsg}")
                            else:
                                log_lines.append("  Radarr search: movie ID not found in queue")
                    else:
                        log_lines.append("  Would blocklist in Radarr" + (" and trigger search" if behavior == "blocklist_and_search" else "") + ".")
                    pushover_msg = f"Removed and blocklisted: {name}" if behavior == "blocklist_only" else f"Removed, blocklisted, and search triggered: {name}"
                else:
                    log_lines.append("  No Sonarr/Radarr blocklist (tag does not match sonarr/radarr).")
                    pushover_msg = f"Removed from Transmission: {name} (tag '{tag}' not linked to Sonarr/Radarr)"

            if not dry_run and settings.pushover.enabled and getattr(settings.pushover, "notify_on_remove", True):
                pushover_send(
                    settings.pushover,
                    title="Untickarr: Torrent removed",
                    message=pushover_msg,
                )
            continue

        # Some wanted, some unwanted -> untick unwanted
        unwanted_ids = [fid for fid, _, _ in unwanted]
        if not dry_run:
            try:
                set_files_unwanted(client, torrent.id, unwanted_ids)
            except Exception as e:
                log_lines.append(f"  Error unticking in {name}: {e}")
                continue
        names = ", ".join(n for _, n, _ in unwanted[:5])
        if len(unwanted) > 5:
            names += f" (+{len(unwanted) - 5} more)"
        log_lines.append(f"{prefix}Unticked in '{name}': {names}")

    run_stats["processed"] = processed
    run_stats["removed"] = removed
    run_stats["blocklisted"] = blocklisted
    return True, "\n".join(log_lines) if log_lines else ("No changes needed." if not dry_run else "No changes would be made."), processed, removed, run_stats
