"""Tunable constants: window, grid, timing, input thresholds and colors (BGR)."""
WINDOW_W, WINDOW_H = 1200, 900
CAMERA_INDEX = 0
MAX_FAILED_READS = 30   # consecutive dropped frames before giving up
GRID_SIZE = 4
TILE_SIZE = 100
TILE_SPACING = 20
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
DUAL_PINCH_HOLD_S = 1.0

# colors (BGR)
CLR_DEFAULT = (60, 60, 60)
CLR_BORDER = (200, 200, 200)
CLR_HILITE = (0, 200, 255)
CLR_SELECTED = (255, 150, 0)
CLR_SUCCESS = (0, 255, 0)
CLR_FAIL = (0, 0, 255)
CLR_TEXT = (255, 255, 255)
