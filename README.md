# Untickarr

_/ʌnˈtɪk.ər/ — like "unticker", someone who unticks the junk. Not "UnTickArr" or "UnTickarr"._

Untickarr is a Transmission companion for the Servarr ecosystem. It works with Sonarr and Radarr alongside Transmission. For torrents with managed tags (for example `tv-sonarr` or `tv-radarr`), it unticks blacklisted junk files so they are never downloaded, and can remove all-junk torrents, blocklist the release in the matching *arr app, optionally trigger a new search, and notify via Pushover.

Untickarr was created to stop wasteful downloads of `.nfo`, `.exe`, images, and similar junk that ride along with *arr grabs, and to clear torrents that contain nothing useful without sitting in Transmission until someone intervenes manually.

> [!IMPORTANT]
> **Features:**
> - Untick blacklisted file types inside managed-tag torrents (for example `.nfo`, `.exe`, images).
> - Remove torrents where **every** file is blacklisted (optionally only when a whitelisted media extension is also present).
> - Choose on remove: remove only, **blocklist** in Sonarr/Radarr, or blocklist and **search** again.
> - Optionally **keep files on disk** when removing a torrent from Transmission.
> - **Dry-run preview** before applying changes.
> - Scheduler with configurable interval, **pause**, and **run cooldown** for “Run now”.
> - Dashboard with last run result, processed/removed counts, Preview, and Run now.
> - Responsive UI with a mobile-friendly sidebar.
> - Health check endpoints for monitoring (tests Transmission).
> - Backup: export and import settings as JSON.
> - Run history logs as TXT or CSV (retention: last 10 runs always; last 20 runs that did something also kept).
> - Optional **Pushover** notifications on remove, run complete, or error.

## Supported Applications

### *Arr Applications
- **Sonarr** (optional; blocklist / search when a torrent is removed)
- **Radarr** (optional; blocklist / search when a torrent is removed)

### Download Clients
- **Transmission** (labels, group, or category required for managed-tag matching)

### Notifications
- **Pushover** (optional)

### Platforms
- **Docker**
- **Synology Container Manager**
- **Linux** (and any host that can run the image)

## Quick Start

Build and run from the project folder:

```bash
docker build -t untickarr .
docker run -d --name untickarr \
  --restart unless-stopped \
  -p 4444:4444 \
  -v /path/to/data:/data \
  -e TZ=Europe/London \
  untickarr
```

Or with Docker Compose:

```bash
docker-compose up -d
```

Settings are stored in `/data/settings.json` inside the container. Mount `/data` to a host path so they persist across restarts.

### Access the Web Interface

After installation, open your browser and navigate to:

```
http://localhost:4444
```

On Synology or another host, use `http://<host-ip>:4444`.

## Deploy on Synology NAS (Container Manager)

### Option A – Project from folder (recommended)

1. Copy the whole project folder to the NAS (e.g. via shared folder or File Station), e.g. to `docker/untickarr/` (so the NAS has `docker/untickarr/Dockerfile`, `docker-compose.yml`, `app/`, `static/`, etc.).
2. In **DSM** go to **Container Manager** → **Project** → **Create** → **Create from a project**.
3. Set **Project path** to the folder you copied (e.g. `/docker/untickarr` or the path Container Manager shows for your shared folder).
4. Give the project a name (e.g. `untickarr`) and click **Next** → **Done**. Container Manager will build the image and start the container.
5. Ensure the compose file’s **port** `4444:4444` and **volume** `./data:/data` are used (they are in the repo’s `docker-compose.yml`). The `data` folder will be created in the project path for persistent settings.
6. Open **http://&lt;nas-ip&gt;:4444** to use the UI.

### Option B – Build on PC, then import image on NAS

1. On your PC, build and save the image:
   ```bash
   docker build -t untickarr .
   docker save untickarr -o untickarr.tar
   ```
2. Copy `untickarr.tar` to the NAS (e.g. into a shared folder).
3. In **Container Manager** → **Image** → **Add** → **Add from file** → choose `untickarr.tar` and import.
4. **Create** a container from the imported image:
   - **Port**: local `4444` → container `4444`.
   - **Volume**: create or pick a folder (e.g. `docker/untickarr/data`) and mount it to `/data`.
   - **Environment** (optional): `TZ=Europe/London`.
   - **Restart**: set to “Unless stopped” if you want it to start after reboot.
5. Start the container and open **http://&lt;nas-ip&gt;:4444**.

## Examples

| Tag       | Contents               | Action                                                       |
|-----------|------------------------|--------------------------------------------------------------|
| tv-sonarr | episode.mkv, cover.jpg | Untick `cover.jpg`, keep `episode.mkv`                       |
| tv-sonarr | setup.exe only         | Remove torrent, blocklist in Sonarr, optionally notify Pushover |

## Configuration

### Prerequisites

- Transmission with **labels** (or **group** / **category**) set when Sonarr/Radarr add torrents. If your Transmission does not support labels, you may need a build that does (for example [transmission-with-labels](https://github.com/transmission/transmission) or similar).
- Sonarr/Radarr: optional, for blocklisting (and optional search) when a torrent is removed.
- Pushover: optional, for notifications.

### Settings (UI)

- **Transmission**: host, port, path (e.g. `/transmission/rpc`), SSL, username/password.
- **Managed tags**: comma-separated (e.g. `tv-sonarr, tv-radarr`). Only torrents with these labels are processed.
- **Blacklisted file types**: comma-separated extensions, no dots (e.g. `exe, jpg, png, nfo, txt`).
- **When unwanted**: action (remove only / blocklist only / blocklist and search); **keep files on disk** when removing; optional **whitelisted extensions** (e.g. `mkv, mp4`) so only torrents with at least one of these are removed.
- **Sonarr / Radarr**: base URL and API key; used to blocklist when a torrent is removed (tag containing `sonarr` → Sonarr, `radarr` → Radarr; e.g. `tv-sonarr`, `tv-radarr`).
- **Pushover**: user key and API token for notifications when a torrent is removed.
- **Schedule & safety**: run interval; **pause scheduler**; **run cooldown** (seconds) for “Run now”.
- **Backup**: export settings (JSON), import from file.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/settings` | Current settings |
| `POST` | `/api/settings` | Save settings (JSON body) |
| `GET` | `/api/settings/export` | Export settings as JSON |
| `POST` | `/api/settings/import` | Import settings (JSON body, full replace) |
| `POST` | `/api/run` | Run the cleaner once (429 if cooldown active) |
| `POST` | `/api/preview` | Dry-run; returns log and counts, no changes |
| `GET` | `/api/status` | Last run result, processed/removed, scheduler paused, interval |
| `GET` | `/api/logs` | Run history |
| `GET` | `/api/logs/export?format=txt\|csv` | Download logs as TXT or CSV |
| `GET` | `/health` or `/api/health` | Health check (Transmission); 200 OK or 503 |
| `GET` | `/api/test?service=...` | Test Transmission, Sonarr, Radarr, or Pushover |

## Credits

Special thanks for inspiration go to:

- [Cleanuparr](https://github.com/cleanuparr/cleanuparr)
- [Sonarr](https://github.com/Sonarr/Sonarr) & [Radarr](https://github.com/Radarr/Radarr)

## License

MIT License. See [LICENSE](LICENSE).
