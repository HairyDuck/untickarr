# Contributing to Untickarr

Thanks for helping. Untickarr is MIT-licensed open source. By opening a pull request you agree that your contribution is licensed under the same [MIT License](LICENSE).

Please read the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- Report bugs with logs and a clear reproduction (no API keys or passwords).
- Suggest features that fit Transmission file-skipping for *arr stacks.
- Improve docs, Docker, or the UI.
- Submit focused pull requests.

## Local development

Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
set DATA_DIR=./data         # Windows PowerShell: $env:DATA_DIR = "./data"
uvicorn app.main:app --host 127.0.0.1 --port 4444 --reload
```

Open http://127.0.0.1:4444. Do not commit `data/`, API keys, or live credentials.

## Docker

```bash
docker compose build
docker compose up -d
```

## Pull requests

Keep changes focused. Match existing Python and UI style. UK English for user-facing copy. Link an issue when there is one.
