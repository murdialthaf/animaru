import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "animaru"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "provider": "allanime",
    "quality": "1080",
    "player": "mpv",
    "download_dir": str(Path.home() / "Downloads" / "Animaru"),
    "history_file": str(CONFIG_DIR / "history.json"),
    "mal_sync": True,
    "skip_intro": True,
}


def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))


def load_config() -> dict:
    ensure_config()
    with open(CONFIG_FILE) as f:
        return {**DEFAULT_CONFIG, **json.load(f)}


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = {**DEFAULT_CONFIG, **cfg}
    with open(CONFIG_FILE, "w") as f:
        json.dump(merged, f, indent=2)
