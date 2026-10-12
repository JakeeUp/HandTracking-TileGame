"""Camera discovery and opening.

OpenCV can't list devices or their names, so names come from the OS:
- Windows: DirectShow device list (via pygrabber), which uses the same
  order as OpenCV's CAP_DSHOW indices.
- Linux: /sys/class/video4linux.
- Elsewhere, or if that fails: probe indices and call them "Camera N".
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import cv2

MAX_PROBE = 6  # indices to try when the OS can't list devices


@dataclass(frozen=True)
class CameraInfo:
    index: int
    name: str

    def __str__(self):
        return f"{self.index}: {self.name}"


def open_camera(index: int):
    """Open camera `index`, preferring DirectShow on Windows (its indices match
    the names from list_cameras, and it starts faster there)."""
    if sys.platform == "win32":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(index)


def fit_frame(frame, w, h):
    """Center-crop `frame` to the w:h aspect ratio, then resize (no stretching)."""
    fh, fw = frame.shape[:2]
    if fw * h > fh * w:                 # too wide: trim the sides
        cw = fh * w // h
        x0 = (fw - cw) // 2
        frame = frame[:, x0:x0 + cw]
    elif fw * h < fh * w:               # too tall: trim top and bottom
        ch = fw * h // w
        y0 = (fh - ch) // 2
        frame = frame[y0:y0 + ch, :]
    return cv2.resize(frame, (w, h))


def list_cameras() -> List[CameraInfo]:
    if sys.platform == "win32":
        names = _dshow_names()
        if names:
            return [CameraInfo(i, n) for i, n in enumerate(names)]
    elif sys.platform.startswith("linux"):
        cams = _v4l2_cameras()
        if cams:
            return cams
    return _probe()


def _dshow_names() -> Optional[List[str]]:
    try:
        from pygrabber.dshow_graph import FilterGraph
        return list(FilterGraph().get_input_devices())
    except Exception:  # pygrabber missing or a COM failure: fall back to probing
        return None


def _v4l2_cameras(root: Path = Path("/sys/class/video4linux")) -> List[CameraInfo]:
    cams = []
    for dev in root.glob("video*"):
        num = dev.name[len("video"):]
        if not num.isdigit():
            continue
        try:
            # Each camera also exposes metadata nodes; the capture node has index 0.
            if (dev / "index").read_text().strip() not in ("", "0"):
                continue
        except OSError:
            pass
        try:
            name = (dev / "name").read_text().strip() or f"Camera {num}"
        except OSError:
            name = f"Camera {num}"
        cams.append(CameraInfo(int(num), name))
    return sorted(cams, key=lambda c: c.index)


def _probe() -> List[CameraInfo]:
    cams = []
    for i in range(MAX_PROBE):
        cap = open_camera(i)
        if cap.isOpened():
            cams.append(CameraInfo(i, f"Camera {i}"))
        cap.release()
    return cams


def pick_default(cameras: Sequence[CameraInfo], saved_name: Optional[str]) -> int:
    """Position in `cameras` of the saved camera (matched by name, since indices
    shift when devices are plugged in), else 0."""
    for pos, cam in enumerate(cameras):
        if cam.name == saved_name:
            return pos
    return 0
