"""Persistent user settings (best score, chosen camera) in ~/.memory_tiles.json."""
import json
from pathlib import Path

DEFAULT_PATH = Path.home() / ".memory_tiles.json"


def load(path: Path = DEFAULT_PATH) -> dict:
    """All saved settings, or {} if the file is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path: Path = DEFAULT_PATH, **updates):
    """Merge `updates` into the saved settings.

    Best-effort: a read-only home directory shouldn't crash the game.
    """
    data = load(path)
    data.update(updates)
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def load_best(path: Path = DEFAULT_PATH) -> int:
    try:
        return max(0, int(load(path).get("best", 0)))
    except (ValueError, TypeError):
        return 0


def save_best(best: int, path: Path = DEFAULT_PATH):
    save(path, best=best)
