import json
import re
import threading
from dataclasses import dataclass


import requests

API_LOCK = threading.Lock()

_SEASON_PATTERN = re.compile(
    r'\s+(?:\d+(?:st|nd|rd|th)\s+Season|Season\s+\d+|Part\s+\d+|S\d+|Cour\s+\d+|Second\s+Season|Third\s+Season|Fourth\s+Season)\s*$',
    re.IGNORECASE
)

_THUMBNAIL_QUERY_HASH = "a24c500a1b765c68ae1d8dd85174931f661c71369c89b92b88b75a725afc471c"
_ALLANIME_API = "https://api.allanime.day/api"


def normalize_name(name: str) -> str:
    return _SEASON_PATTERN.sub('', name).strip()

def extract_season_label(full_name: str, normalized: str) -> str:
    suffix = full_name[len(normalized):].strip()
    if not suffix:
        return "Season 1"
    return suffix

@dataclass
class SeriesEntry:
    name: str
    seasons: list[tuple[str, str]]
    primary_id: str
    image: str = ""


def _season_sort_key(label: str) -> int:
    import re
    m = re.search(r'(\d+)', label)
    return int(m.group(1)) if m else 0


def _search_with_thumbnails(query: str) -> list[dict]:
    edges = []
    page = 1
    session = requests.Session()
    session.headers.update({"Referer": "https://allmanga.to/"})

    while True:
        payload = {
            "variables": {
                "search": {"query": query} if query else {},
                "limit": 50,
                "page": page,
                "translationType": "sub",
                "countryOrigin": "ALL",
            },
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": _THUMBNAIL_QUERY_HASH,
                }
            }),
        }
        resp = session.post(
            _ALLANIME_API,
            json=payload,
            timeout=15,
        )
        data = resp.json()
        batch = data.get("data", {}).get("shows", {}).get("edges", [])
        if not batch:
            break
        edges.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    return edges


def search_with_images(query: str) -> list[SeriesEntry]:
    raw = _search_with_thumbnails(query)
    groups: dict[str, SeriesEntry] = {}
    for item in raw:
        name = item.get("name", "")
        identifier = item.get("_id", "")
        thumbnail = item.get("thumbnail") or ""
        if not name or not identifier:
            continue
        norm = normalize_name(name)
        label = extract_season_label(name, norm)
        if norm in groups:
            groups[norm].seasons.append((identifier, label))
        else:
            groups[norm] = SeriesEntry(
                name=norm,
                seasons=[(identifier, label)],
                primary_id=identifier,
                image=thumbnail,
            )
    for entry in groups.values():
        entry.seasons.sort(key=lambda x: _season_sort_key(x[1]))
    return list(groups.values())


def group_search_results(results: list) -> list[SeriesEntry]:
    groups: dict[str, SeriesEntry] = {}
    for r in results:
        norm = normalize_name(r.name)
        label = extract_season_label(r.name, norm)
        if norm in groups:
            groups[norm].seasons.append((r.identifier, label))
        else:
            groups[norm] = SeriesEntry(
                name=norm,
                seasons=[(r.identifier, label)],
                primary_id=r.identifier,
            )
    for entry in groups.values():
        entry.seasons.sort(key=lambda x: _season_sort_key(x[1]))
    return list(groups.values())

def group_history_entries(entries: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for e in entries:
        norm = normalize_name(e.get("anime_title", ""))
        if norm not in groups:
            groups[norm] = []
        groups[norm].append(e)

    result = []
    for norm, items in groups.items():
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        latest = dict(items[0])
        latest["anime_title"] = norm
        latest["all_seasons"] = [(e["anime_id"], f"Season {e.get('season', 1)}") for e in items]
        result.append(latest)

    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return result
