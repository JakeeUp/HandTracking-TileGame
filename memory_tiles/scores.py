"""Best-score persistence in a small JSON file in the user's home directory."""
import json
from pathlib import Path

DEFAULT_PATH = Path.home() / ".memory_tiles.json"


def load_best(path: Path = DEFAULT_PATH) -> int:
    """Saved best score, or 0 if there is none or the file is unreadable."""
    try:
        return max(0, int(json.loads(path.read_text(encoding="utf-8"))["best"]))
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_best(best: int, path: Path = DEFAULT_PATH):
    """Best-effort save; a read-only home directory shouldn't crash the game."""
    try:
        path.write_text(json.dumps({"best": best}), encoding="utf-8")
    except OSError:
        pass
