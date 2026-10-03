# Contributing to Untickarr

Issues and pull requests are welcome.

## Local development

Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 4444 --reload
```

Open http://127.0.0.1:4444. Settings are written to `DATA_DIR` (default `/data` in Docker, or set `DATA_DIR` to a local folder).

Do not commit `data/`, API keys, or live NAS credentials.

## Docker

```bash
docker compose build
docker compose up -d
```

## Pull requests

Keep changes focused. Match existing Python and UI style. UK English for user-facing copy.
