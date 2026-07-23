import json
import time
from pathlib import Path

from animaru.utils.config import CONFIG_DIR

HISTORY_FILE = CONFIG_DIR / "history.json"

DEFAULT = {
    "continue_watching": [],
    "completed": [],
    "watchlist": [],
}


def _load() -> dict:
    if not HISTORY_FILE.exists():
        save(DEFAULT)
        return dict(DEFAULT)
    try:
        return {**DEFAULT, **json.loads(HISTORY_FILE.read_text())}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT)


def save(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data, indent=2, default=str))


def get_continue_watching():
    data = _load()
    cw = data.get("continue_watching", [])
    cw.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return cw


def get_completed():
    data = _load()
    c = data.get("completed", [])
    c.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    return c


def get_watchlist():
    return _load().get("watchlist", [])


def update_episode_progress(
    anime_id: str,
    anime_title: str,
    season: int,
    episode: int,
    total_episodes: int,
    poster_url: str = "",
    progress: float = 0.0,
):
    data = _load()
    cw = data["continue_watching"]

    entry = {
        "anime_id": anime_id,
        "anime_title": anime_title,
        "season": season,
        "episode": episode,
        "progress": progress,
        "total_episodes": total_episodes,
        "poster_url": poster_url,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    existing = [i for i, e in enumerate(cw) if e["anime_id"] == anime_id]
    if existing:
        cw[existing[0]] = entry
    else:
        cw.append(entry)

    data["continue_watching"] = cw
    save(data)


def mark_episode_watched(
    anime_id: str,
    anime_title: str,
    season: int,
    episode: int,
    total_episodes: int,
    poster_url: str = "",
):
    data = _load()
    cw = data["continue_watching"]

    cw = [e for e in cw if e["anime_id"] != anime_id]
    data["continue_watching"] = cw

    is_complete = episode >= total_episodes
    if is_complete:
        completed = data["completed"]
        completed_entry = {
            "anime_id": anime_id,
            "anime_title": anime_title,
            "season": season,
            "total_episodes": total_episodes,
            "poster_url": poster_url,
            "completed_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
        }
        existing = [
            i for i, e in enumerate(completed) if e["anime_id"] == anime_id
        ]
        if existing:
            completed[existing[0]] = completed_entry
        else:
            completed.append(completed_entry)
        data["completed"] = completed
    else:
        update_episode_progress(
            anime_id, anime_title, season, episode + 1, total_episodes, poster_url
        )

    save(data)


def toggle_watchlist(anime_id: str):
    data = _load()
    wl = data["watchlist"]
    if anime_id in wl:
        wl.remove(anime_id)
    else:
        wl.append(anime_id)
    data["watchlist"] = wl
    save(data)
    return anime_id in wl


def in_watchlist(anime_id: str) -> bool:
    return anime_id in _load().get("watchlist", [])


def get_progress(anime_id: str) -> dict | None:
    for entry in _load().get("continue_watching", []):
        if entry["anime_id"] == anime_id:
            return entry
    return None


def get_series_progress(season_ids: list[str]) -> dict | None:
    entries = _load().get("continue_watching", [])
    matches = [e for e in entries if e["anime_id"] in season_ids]
    if not matches:
        return None
    matches.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return matches[0]
