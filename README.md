# Untickarr

[![License: MIT](https://img.shields.io/github/license/HairyDuck/untickarr)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/HairyDuck/untickarr?style=flat)](https://github.com/HairyDuck/untickarr/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/HairyDuck/untickarr)](https://github.com/HairyDuck/untickarr/issues)
[![GitHub release](https://img.shields.io/github/v/release/HairyDuck/untickarr?include_prereleases&sort=semver)](https://github.com/HairyDuck/untickarr/releases)
[![GHCR](https://img.shields.io/badge/ghcr.io-hairyduck%2Funtickarr-blue?logo=docker)](https://github.com/HairyDuck/untickarr/pkgs/container/untickarr)

Open source (MIT). Skip junk files inside Transmission torrents before they land in your library.

Untickarr is a Docker app for the Servarr stack. It watches torrents with *arr labels (for example `tv-sonarr`, `tv-radarr`, `whisparr`), **unticks** blacklisted files (`.nfo`, `.exe`, images), and if a torrent is *only* junk it can **remove** it, **blocklist** the release in Sonarr or Radarr, and notify you.

It is part of the same HairyDuck companion set as [Giveuparr](https://github.com/HairyDuck/giveuparr) (fair try on missing Wanted items, then unmonitor). It is **not** [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr). Cleanuparr handles stalled, slow, and failed-import queues. Untickarr handles file selection inside Transmission. They work well together.

| Companion | Job |
| --- | --- |
| **Untickarr** | Skip junk files inside Transmission torrents |
| [Giveuparr](https://github.com/HairyDuck/giveuparr) | Fair try on missing Wanted items, then unmonitor |
| [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr) | Stalled, failed import, and malware queue cleanup |

> [!IMPORTANT]
> **Features**
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
2. **Container Manager** â†’ **Project** â†’ create from that folder.
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
- **When unwanted:** remove only / blocklist only / blocklist and search; keep files on disk; optional whitelist (`mkv`, `mp4`) so â€œall junkâ€ removal only runs if a wanted extension was expected.
- **Sonarr / Radarr:** base URL and API key. Tag containing `sonarr` â†’ Sonarr; `radarr` â†’ Radarr.
- **Pushover:** optional notifications.
- **Schedule:** interval, pause scheduler, Run now cooldown.
- **Backup:** export/import JSON.

## API

- `GET` / `POST` `/api/settings` â€“ read or save settings
- `GET` `/api/settings/export` â€“ export JSON
- `POST` `/api/settings/import` â€“ import JSON
- `POST` `/api/run` â€“ run once (429 if cooldown)
- `POST` `/api/preview` â€“ dry-run
- `GET` `/api/status` â€“ last run and scheduler
- `GET` `/api/logs` â€“ history
- `GET` `/api/logs/export?format=txt|csv`
- `GET` `/health` or `/api/health` â€“ Transmission check (200 or 503)
- `GET` `/api/test?service=...` â€“ Transmission, Sonarr, Radarr, or Pushover

Settings persist in `/data/settings.json`. Mount `/data` so they survive restarts.

## Contributing

Untickarr is free and open source under the [MIT License](LICENSE). Issues, pull requests, and discussion are welcome.

- [Contributing guide](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Report a bug](https://github.com/HairyDuck/untickarr/issues/new?template=bug.yml)
- [Request a feature](https://github.com/HairyDuck/untickarr/issues/new?template=feature.yml)

## License

Copyright (c) 2026 HairyDuck. Released under the [MIT License](LICENSE). You may use, copy, modify, and distribute this software, including commercially, provided the licence notice is kept.
