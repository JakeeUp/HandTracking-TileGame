"""Records the rendered game to an MP4 file, for demo videos and GIFs.

Frames are written against wall-clock time: if the game runs slower than
RECORD_FPS, frames are repeated so the video plays back at real speed.
"""
import sys
import time
from pathlib import Path
from typing import Optional

import cv2

RECORD_FPS = 30


def default_path() -> Path:
    """A timestamped file in the user's Videos (Movies on macOS) folder."""
    videos = Path.home() / ("Movies" if sys.platform == "darwin" else "Videos")
    return videos / "MemoryTiles" / time.strftime("memory_tiles_%Y%m%d_%H%M%S.mp4")


class Recorder:
    def __init__(self, fps: int = RECORD_FPS):
        self.fps = fps
        self.path: Optional[Path] = None
        self._writer = None
        self._t0 = 0.0
        self._written = 0

    @property
    def active(self) -> bool:
        return self._writer is not None

    def elapsed(self, now: float) -> float:
        return now - self._t0 if self.active else 0.0

    def start(self, path, size, now: float) -> bool:
        """Begin recording frames of `size` (w, h) to `path`. False if it can't."""
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), self.fps, size)
        if not writer.isOpened():
            writer.release()
            return False
        self._writer, self.path, self._t0, self._written = writer, path, now, 0
        return True

    def write(self, frame, now: float):
        if not self.active:
            return
        due = int((now - self._t0) * self.fps) + 1
        while self._written < due:
            self._writer.write(frame)
            self._written += 1

    def stop(self) -> Optional[Path]:
        """Finish the file and return its path (None if not recording)."""
        if not self.active:
            return None
        self._writer.release()
        self._writer = None
        return self.path
