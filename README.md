# Memory Tiles (Hand-Pinch)

A Simon-style webcam memory game using OpenCV + MediaPipe hand tracking.
Watch the tiles light up, then repeat the sequence by pinching tiles with
your right hand. Each level adds one tile to the sequence.

## Choosing a camera

A settings window opens first with a dropdown of your cameras (by name on
Windows and Linux) and a live preview. It warns if a camera only sends a
black picture (common with virtual cameras and capture cards with no
input) or can't be opened (usually because another app such as OBS is
using it). Your choice is remembered. Press `C` in-game to come back to
it, or skip it with `python main.py --camera 4`.

**Mirror image** (on by default) flips the camera so the screen acts like
a mirror. Turn it off if your source is already mirrored (OBS virtual
camera often is): the tell is that moving your hand right moves it left
on screen. Press `M` in-game to toggle it.

## How to play

- **Start:** pinch (thumb + index) with either hand and hold for a second.
- **Select a tile:** point either hand at it and pinch. Each hand has its
  own cursor, so you can alternate hands. The tile under a cursor is
  outlined; the selection is made when you release the pinch.
- A wrong tile costs a life and the same sequence replays. Lose all 3
  lives and it's game over; pinch and hold to play again.
- Your best score is saved to `~/.memory_tiles.json`.

| Key | Action |
| --- | --- |
| `V` | Start / stop recording a video |
| `C` | Back to camera settings |
| `M` | Toggle mirror image |
| `D` | Toggle debug window (shows live pinch ratios) |
| `F` | Toggle fullscreen |
| `R` | Restart to title screen |
| `Q` / `Esc` | Quit |

## Download

Builds for Windows and macOS are attached to each
[GitHub Release](../../releases).

### macOS notes
1) Download the .zip for your Mac (Apple Silicon = mac-arm, Intel = mac-intel).
2) Unzip → you'll get `MemoryTiles.app`.
3) First run: right-click the app → Open → Open (bypasses Gatekeeper since it's unsigned).
4) If camera prompt doesn't appear, enable it in System Settings → Privacy & Security → Camera.
(If macOS quarantines it, you can run: `xattr -dr com.apple.quarantine MemoryTiles.app`)

## Run from source

Requires Python 3.9 – 3.12 (MediaPipe has no wheels for newer versions)
and a webcam.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py          # or: python -m memory_tiles
```

## Recording a demo

Press `V` in-game to start and stop recording, or record from launch with
`python main.py --record demo.mp4`. Videos save what's on screen at real
playback speed (without the REC badge) to `Videos/MemoryTiles` (`Movies`
on macOS) unless you pass a path.

Turn a recording into a GIF for a README or post:

```bash
python -m memory_tiles.gif demo.mp4 demo.gif --start 3 --end 12 --width 640 --fps 15
```

`--start`/`--end` trim the clip (seconds). Aim for 5–10 seconds to keep
the GIF under ~10 MB.

## Tuning

All tunables are in [`memory_tiles/config.py`](memory_tiles/config.py):
timings, lives, grid size and colors. If pinches feel too hard or too
easy, open the debug window (`D`), watch `PINCH_RATIO` while you pinch and
release, and adjust `PINCH_ON_RATIO` / `PINCH_OFF_RATIO`.

## Development

```bash
pip install -r requirements-dev.txt
pytest          # game rules, input, geometry and renderer smoke tests
ruff check .    # lint
```

CI runs both on every push and pull request. Pushing a `v*` tag builds
the Windows exe and macOS apps and attaches them to a GitHub Release.

### Layout

| Module | Responsibility |
| --- | --- |
| `memory_tiles/app.py` | Entry point and game loop: window, keyboard; wires everything together |
| `memory_tiles/launcher.py` | Camera settings window (tkinter) with live preview |
| `memory_tiles/cameras.py` | Camera discovery (device names) and opening |
| `memory_tiles/game.py` | Game rules and state machine (pure, clock injected) |
| `memory_tiles/gestures.py` | Hand readings → pinch press/release/lost events (hysteresis) |
| `memory_tiles/hand_tracking.py` | MediaPipe wrapper producing `HandReading`s |
| `memory_tiles/geometry.py` | Grid layout and hit-testing |
| `memory_tiles/renderer.py` | All OpenCV drawing |
| `memory_tiles/recorder.py` | Records the rendered game to MP4 |
| `memory_tiles/gif.py` | MP4 → GIF converter for demos |
| `memory_tiles/text.py` | TrueType text rendering (bundled Poppins font) |
| `memory_tiles/settings.py` | Saved settings: best score, chosen camera |
| `memory_tiles/config.py` | Tunable constants |

`requirements.txt` pins `mediapipe==0.10.21`, the last release with the
legacy `mp.solutions` API this project uses.
