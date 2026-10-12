"""Anti-aliased TrueType text for OpenCV frames.

OpenCV's Hershey fonts are ASCII-only and look dated. Text here is
rasterised once with Pillow (Poppins, bundled under the SIL OFL) into a
cached sprite with a soft drop shadow, then alpha-blended into the frame,
so the per-frame cost is a small blend.
"""
from functools import cache, lru_cache
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
WEIGHTS = {
    "regular": "Poppins-Regular.ttf",
    "semibold": "Poppins-SemiBold.ttf",
    "bold": "Poppins-Bold.ttf",
}
SHADOW_BLUR = 3
PAD = SHADOW_BLUR * 3          # room around the glyphs for the shadow


@cache
def font(size: int, weight: str = "regular"):
    try:
        return ImageFont.truetype(str(FONT_DIR / WEIGHTS[weight]), size)
    except OSError:              # font missing (e.g. bad packaging): degrade, don't crash
        return ImageFont.load_default(size)


def text_size(s: str, size: int, weight: str = "regular") -> Tuple[int, int]:
    """(width, height) of the inked text."""
    left, top, right, bottom = font(size, weight).getbbox(s)
    return right - left, bottom - top


@lru_cache(maxsize=1024)
def _sprite(s: str, size: int, color: Tuple[int, int, int], weight: str, shadow: bool):
    """BGR image and 0..1 alpha for `s`, padded by PAD on every side."""
    f = font(size, weight)
    left, top, right, bottom = f.getbbox(s)
    w, h = right - left + 2 * PAD, bottom - top + 2 * PAD
    origin = (PAD - left, PAD - top)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((origin[0], origin[1] + 2), s, font=f, fill=(0, 0, 0, 170))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)))
    # Channels are filled in BGR order directly, matching OpenCV frames.
    fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(fg).text(origin, s, font=f, fill=(*color, 255))
    img = Image.alpha_composite(img, fg)

    arr = np.asarray(img, dtype=np.float32)
    return arr[..., :3], arr[..., 3:] / 255.0


def draw_text(frame, s: str, pos, size: int, color, weight: str = "regular",
              anchor: str = "lt", alpha: float = 1.0, shadow: bool = True):
    """Draw `s` with its ink box anchored at `pos`.

    anchor is two letters: horizontal l/m/r then vertical t/m/b,
    e.g. "mm" centers the text on pos.
    """
    if not s:
        return
    bgr, a = _sprite(s, size, tuple(int(c) for c in color), weight, shadow)
    tw, th = text_size(s, size, weight)
    fx = {"l": 0.0, "m": 0.5, "r": 1.0}[anchor[0]]
    fy = {"t": 0.0, "m": 0.5, "b": 1.0}[anchor[1]]
    x = int(round(pos[0] - fx * tw)) - PAD
    y = int(round(pos[1] - fy * th)) - PAD
    blend(frame, bgr, a * alpha, x, y)


def blend(frame, src_bgr, src_alpha, x: int, y: int):
    """Alpha-blend a float BGR image (with HxWx1 alpha in 0..1) at (x, y), clipped."""
    fh, fw = frame.shape[:2]
    h, w = src_bgr.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, fw), min(y + h, fh)
    if x0 >= x1 or y0 >= y1:
        return
    sx, sy = x0 - x, y0 - y
    src = src_bgr[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    a = src_alpha[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    roi = frame[y0:y1, x0:x1]
    roi[:] = (roi * (1.0 - a) + src * a).astype(np.uint8)
