import json
import urllib.parse
import urllib.request
from pathlib import Path

from animaru_app.utils.config import CONFIG_DIR

MAL_CACHE_FILE = CONFIG_DIR / "mal_id_cache.json"


def _load_mal_cache() -> dict:
    if MAL_CACHE_FILE.exists():
        try:
            return json.loads(MAL_CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_mal_cache(cache: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MAL_CACHE_FILE.write_text(json.dumps(cache, indent=2))


def search_mal_id(title: str) -> int | None:
    cache = _load_mal_cache()
    if title in cache:
        return cache[title]

    try:
        q = urllib.parse.quote(title)
        url = f"https://api.jikan.moe/v4/anime?q={q}&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Animaru/0.1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("data"):
            mal_id = data["data"][0]["mal_id"]
            cache[title] = mal_id
            _save_mal_cache(cache)
            return mal_id
    except Exception:
        return None
    return None


def fetch_skip_times(mal_id: int, episode: int) -> list[dict]:
    for ep_len in [1440, 720, 1800, 3600]:
        try:
            url = (
                f"https://api.aniskip.com/v2/skip-times/{mal_id}/{episode}"
                f"?types[]=op&types[]=ed&episodeLength={ep_len}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Animaru/0.1.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            if data.get("found") and data.get("results"):
                for r in data["results"]:
                    r["type"] = r.pop("skipType", r.get("type", "skip"))
                return data["results"]
        except urllib.error.HTTPError as e:
            if e.code == 400:
                continue
        except Exception:
            return []
    return []


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}.000"


def generate_chapters_file(skip_results: list[dict]) -> str | None:
    if not skip_results:
        return None

    lines = []
    idx = 1
    sorted_results = sorted(
        skip_results, key=lambda x: x.get("interval", {}).get("startTime", 0)
    )

    for result in sorted_results:
        interval = result.get("interval", {})
        start = interval.get("startTime", 0)
        end = interval.get("endTime", 0)
        stype = result.get("type", "skip")
        label = "Opening" if stype == "op" else ("Ending" if stype == "ed" else "Skip")
        lines.append(f"CHAPTER{idx:02d}={_format_time(start)}")
        lines.append(f"CHAPTER{idx:02d}NAME=Skip {label}")
        idx += 1
        lines.append(f"CHAPTER{idx:02d}={_format_time(end)}")
        lines.append(f"CHAPTER{idx:02d}NAME={label} End")
        idx += 1

    return "\n".join(lines)
