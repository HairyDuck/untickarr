# Untickarr

Skip junk files inside Transmission torrents before they land in your library.

Untickarr is a small Docker app for the Servarr stack. It watches torrents with *arr labels (for example `tv-sonarr`, `tv-radarr`, `whisparr`), **unticks** blacklisted files (`.nfo`, `.exe`, images), and if a torrent is *only* junk it can **remove** it, **blocklist** the release in Sonarr or Radarr, and notify you.

It is **not** [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr). Cleanuparr handles stalled, slow, and failed-import queues. Untickarr handles file selection inside Transmission. They work well together.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GHCR](https://img.shields.io/badge/ghcr.io-hairyduck%2Funtickarr-blue?logo=docker)](https://github.com/HairyDuck/untickarr/pkgs/container/untickarr)

> [!IMPORTANT]
> **What it does**
> - Untick blacklisted extensions on tagged Transmission torrents.
> - Optionally remove torrents that contain only unwanted files.
> - Blocklist the release in Sonarr or Radarr (by tag) and optionally search again.
> - Dry-run preview, scheduler pause, run cooldown, health check, settings backup.
> - Optional Pushover on remove, run complete, or error.

## Supported

- **Download client:** Transmission (labels / group / category)
- **\*arr:** Sonarr, Radarr (blocklist by tag; add a `whisparr` tag to process those torrents)
- **Platforms:** Docker, Synology Container Manager, any Linux host

## Quick start

```yaml
services:
  untickarr:
    image: ghcr.io/hairyduck/untickarr:latest
    container_name: untickarr
    ports:
      - "4444:4444"
    volumes:
      - ./data:/data
    environment:
      TZ: Europe/London
    restart: unless-stopped
```

```bash
docker compose up -d
```

Open http://localhost:4444 and enter Transmission (and optional Sonarr / Radarr / Pushover) in the UI.

Copy [`settings.example.json`](settings.example.json) into `data/settings.json` if you prefer files over the UI. Never commit a filled-in settings file.

To build from source instead of GHCR:

```bash
docker compose build
docker compose up -d
```

### Synology Container Manager

1. Copy this project to `docker/untickarr/` on the NAS.
2. **Container Manager** → **Project** → create from that folder.
3. Keep port `4444:4444` and volume `./data:/data`.
4. Open `http://<nas-ip>:4444`.

## How it behaves

| Tag | Contents | Action |
| --- | --- | --- |
| `tv-sonarr` | `episode.mkv`, `cover.jpg` | Untick `cover.jpg`, keep the episode |
| `tv-sonarr` | `setup.exe` only | Remove torrent, optionally delete data, blocklist in Sonarr |

Tags must match Transmission labels. Sonarr/Radarr custom formats and download-client categories usually set these (`tv-sonarr`, `tv-radarr`). Include every label you want processed, including `whisparr` if you use Whisparr.

**Requirements:** Transmission with labels (or group/category). Without labels, only torrents you can match another way are touched.

## Settings (UI)

- **Transmission:** host, port, path (`/transmission/rpc`), SSL, username/password.
- **Managed tags:** comma-separated labels to process.
- **Blacklisted file types:** extensions without dots (`exe`, `jpg`, `nfo`).
- **When unwanted:** remove only / blocklist only / blocklist and search; keep files on disk; optional whitelist (`mkv`, `mp4`) so “all junk” removal only runs if a wanted extension was expected.
- **Sonarr / Radarr:** base URL and API key. Tag containing `sonarr` → Sonarr; `radarr` → Radarr.
- **Pushover:** optional notifications.
- **Schedule:** interval, pause scheduler, Run now cooldown.
- **Backup:** export/import JSON.

## API

- `GET` / `POST` `/api/settings` – read or save settings
- `GET` `/api/settings/export` – export JSON
- `POST` `/api/settings/import` – import JSON
- `POST` `/api/run` – run once (429 if cooldown)
- `POST` `/api/preview` – dry-run
- `GET` `/api/status` – last run and scheduler
- `GET` `/api/logs` – history
- `GET` `/api/logs/export?format=txt|csv`
- `GET` `/health` or `/api/health` – Transmission check (200 or 503)
- `GET` `/api/test?service=...` – Transmission, Sonarr, Radarr, or Pushover

Settings persist in `/data/settings.json`. Mount `/data` so they survive restarts.

## Related

- Predecessor (archived): [transmission-cleanup-synology](https://github.com/HairyDuck/transmission-cleanup-synology)
- Queue cleaner: [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
