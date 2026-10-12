"""Tunable constants: window, grid, timing, input thresholds and colors (BGR)."""
WINDOW_W, WINDOW_H = 1200, 900
MAX_FAILED_READS = 30   # consecutive dropped frames before giving up
GRID_SIZE = 4
TILE_SIZE = 110
TILE_SPACING = 16
TILE_SHOW_DURATION = 0.8        # how long each pattern tile is lit at level 1
MIN_TILE_SHOW_DURATION = 0.35
SHOW_SPEEDUP = 0.95             # tile show time multiplier per level
PATTERN_PAUSE = 0.3             # dark gap between pattern tiles
READY_DURATION = 0.8            # "get ready" beat before the pattern plays
SUCCESS_DURATION = 1.0
FAIL_DURATION = 1.8
LIVES = 3
# Pinch = thumb-tip/index-tip distance divided by palm length (wrist to
# middle-finger knuckle), so it doesn't depend on distance from the camera.
# Press below ON, release above OFF; the gap between them stops jitter.
PINCH_ON_RATIO = 0.30
PINCH_OFF_RATIO = 0.45
PINCH_COOLDOWN_S = 0.3
START_HOLD_S = 1.0

PICK_FLASH_S = 0.35             # how long a picked tile flashes / ripples
BACKGROUND_DIM = 0.45           # camera feed brightness multiplier behind the UI

# Theme colors (BGR). Each tile also gets its own hue (see renderer.tile_colors).
CLR_TEXT = (245, 245, 245)
CLR_MUTED = (190, 185, 180)
CLR_ACCENT = (255, 214, 64)     # cyan: titles, highlights, progress
CLR_SUCCESS = (120, 230, 90)
CLR_FAIL = (90, 80, 255)
CLR_PANEL = (34, 24, 18)        # dark navy glass behind HUD cards and tiles
CLR_HAND = {"Left": (255, 190, 60), "Right": (230, 100, 255)}   # blue / pink
