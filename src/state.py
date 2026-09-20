"""Persist closed-PR keys and per-repo blocklist."""
import json
from datetime import date


def load_state(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("closed_prs", [])
    data.setdefault("blocklisted", {})
    return data


def save_state(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _today_iso(today: str | None) -> str:
    return today or date.today().isoformat()


def is_blocklisted(state: dict, repo_full: str, today: str | None = None) -> bool:
    until = state.get("blocklisted", {}).get(repo_full)
    if not until:
        return False
    return _today_iso(today) <= until


def _key(branch: str, title: str) -> str:
    return f"{branch}||{title}"


def record_closed(state: dict, branch: str, title: str) -> None:
    key = _key(branch, title)
    if key not in state.setdefault("closed_prs", []):
        state["closed_prs"].append(key)


def already_tried(state: dict, branch: str, title: str) -> bool:
    return _key(branch, title) in state.get("closed_prs", [])
