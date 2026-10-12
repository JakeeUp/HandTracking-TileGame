"""Tunable constants: window, grid, timing, input thresholds and colors (BGR)."""
WINDOW_W, WINDOW_H = 1200, 900
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
START_HOLD_S = 1.0

PICK_FLASH_S = 0.25             # how long a picked tile flashes

# colors (BGR)
CLR_DEFAULT = (60, 60, 60)      # idle tile
CLR_BORDER = (200, 200, 200)
CLR_HILITE = (0, 200, 255)      # pattern tile being shown
CLR_HOVER = (255, 255, 0)       # outline of the tile under the cursor
CLR_SELECTED = (255, 150, 0)    # armed / just-picked tile
CLR_SUCCESS = (0, 255, 0)
CLR_FAIL = (0, 0, 255)
CLR_TEXT = (255, 255, 255)
CLR_MUTED = (210, 210, 210)
CLR_OUTLINE = (20, 20, 20)      # stroke behind text on bright fills
CLR_ACCENT = (0, 255, 255)      # titles, headings
CLR_BAR_BG = (50, 50, 50)
CLR_BAR_BORDER = (150, 150, 150)
CLR_BAR_FILL = (0, 255, 100)
CLR_CURSOR = (0, 255, 0)
CLR_PINCH = (255, 0, 255)
