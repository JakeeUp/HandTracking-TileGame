"""Turn a recording into a README-friendly GIF.

    python -m memory_tiles.gif demo.mp4 demo.gif --start 3 --end 12

Uses one palette for the whole clip (sampled from frames across it), which
avoids the color flicker of per-frame palettes and keeps the file small.
"""
import argparse
import sys
from typing import List, Optional

import cv2
from PIL import Image

PALETTE_SAMPLES = 12


def read_frames(src: str, start: float = 0.0, end: Optional[float] = None,
                width: int = 640, fps: float = 15) -> List[Image.Image]:
    """RGB frames from `src` between start and end seconds, resampled to fps."""
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise OSError(f"can't open video: {src}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames, index, next_t = [], 0, start
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = index / src_fps
            index += 1
            if end is not None and t > end:
                break
            if t + 1e-9 < next_t:
                continue
            next_t += 1.0 / fps
            h, w = frame.shape[:2]
            if w > width:
                frame = cv2.resize(frame, (width, round(h * width / w)),
                                   interpolation=cv2.INTER_AREA)
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    finally:
        cap.release()
    return frames


def shared_palette(frames: List[Image.Image]) -> Image.Image:
    """A 256-color palette built from frames sampled across the whole clip."""
    step = max(1, len(frames) // PALETTE_SAMPLES)
    samples = frames[::step][:PALETTE_SAMPLES]
    w, h = samples[0].size
    sheet = Image.new("RGB", (w, h * len(samples)))
    for k, im in enumerate(samples):
        sheet.paste(im, (0, k * h))
    return sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT)


def mp4_to_gif(src: str, dst: str, start: float = 0.0, end: Optional[float] = None,
               width: int = 640, fps: float = 15) -> int:
    """Write `dst` and return the number of frames in it."""
    frames = read_frames(src, start, end, width, fps)
    if not frames:
        raise ValueError("no frames in that time range")
    palette = shared_palette(frames)
    gif = [im.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for im in frames]
    gif[0].save(dst, save_all=True, append_images=gif[1:], duration=round(1000 / fps),
                loop=0, optimize=True)
    return len(gif)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m memory_tiles.gif", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", help="input video (e.g. a Memory Tiles recording)")
    p.add_argument("dst", help="output .gif")
    p.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    p.add_argument("--end", type=float, help="end time in seconds (default: end of video)")
    p.add_argument("--width", type=int, default=640, help="output width in pixels")
    p.add_argument("--fps", type=float, default=15, help="output frame rate")
    args = p.parse_args(argv)
    try:
        n = mp4_to_gif(args.src, args.dst, args.start, args.end, args.width, args.fps)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {args.dst} ({n} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
