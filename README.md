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

## How to play

- **Start:** pinch with **both hands** and hold for a second.
- **Select a tile:** point your right hand at it and pinch (thumb + index).
  The tile under your cursor is outlined; the selection is made when you
  release the pinch.
- A wrong tile costs a life and the same sequence replays. Lose all 3
  lives and it's game over; pinch with both hands to play again.
- Your best score is saved to `~/.memory_tiles.json`.

| Key | Action |
| --- | --- |
| `C` | Back to camera settings |
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
| `memory_tiles/settings.py` | Saved settings: best score, chosen camera |
| `memory_tiles/config.py` | Tunable constants |

`requirements.txt` pins `mediapipe==0.10.21`, the last release with the
legacy `mp.solutions` API this project uses.
