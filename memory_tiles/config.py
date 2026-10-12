"""Tunable constants: window, grid, timing, input thresholds and colors (BGR)."""
WINDOW_W, WINDOW_H = 1200, 900
GRID_SIZE = 4
TILE_SIZE = 100
TILE_SPACING = 20
TILE_SHOW_DURATION = 0.8
PATTERN_PAUSE = 0.3
FEEDBACK_DURATION = 2.0
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
