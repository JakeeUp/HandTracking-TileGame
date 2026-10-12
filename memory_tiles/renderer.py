"""OpenCV drawing for the game screens, HUD and debug window.

Hershey fonts only cover ASCII, so all on-screen text must be ASCII.
"""
import cv2
import numpy as np

from .config import (
    CLR_ACCENT,
    CLR_BAR_BG,
    CLR_BAR_BORDER,
    CLR_BAR_FILL,
    CLR_BORDER,
    CLR_CURSOR,
    CLR_DEFAULT,
    CLR_FAIL,
    CLR_HILITE,
    CLR_HOVER,
    CLR_MUTED,
    CLR_OUTLINE,
    CLR_PINCH,
    CLR_SELECTED,
    CLR_SUCCESS,
    CLR_TEXT,
    PICK_FLASH_S,
)
from .game import GameState

FONT = cv2.FONT_HERSHEY_SIMPLEX
TITLE_FONT = cv2.FONT_HERSHEY_DUPLEX

HINTS = {
    GameState.READY: ("GET READY...", CLR_ACCENT),
    GameState.SHOWING_PATTERN: ("MEMORIZE THE PATTERN", CLR_ACCENT),
    GameState.PLAYER_INPUT: ("PINCH THE TILES IN ORDER", CLR_SUCCESS),
    GameState.LEVEL_SUCCESS: ("PERFECT!", CLR_SUCCESS),
    GameState.LEVEL_FAILED: ("WRONG TILE! WATCH AGAIN", CLR_FAIL),
}

CONTROLS = [
    "Controls:",
    "  Both hands pinch (hold) = Start",
    "  Right pinch = Select tile",
    "  D Debug | F Fullscreen | R Restart | Q Quit",
]


# --- primitives --------------------------------------------------------------

def text(frame, s, org, scale, color, thick=2, font=FONT, outline=False):
    """Anti-aliased text; `outline` adds a dark stroke for bright backgrounds."""
    org = (int(org[0]), int(org[1]))
    if outline:
        cv2.putText(frame, s, org, font, scale, CLR_OUTLINE, thick + 3, cv2.LINE_AA)
    cv2.putText(frame, s, org, font, scale, color, thick, cv2.LINE_AA)


def text_size(s, scale, thick=2, font=FONT):
    return cv2.getTextSize(s, font, scale, thick)[0]


def text_centered(frame, s, cx, y, scale, color, thick=2, font=FONT, outline=False):
    """Draw `s` horizontally centered on cx with its baseline at y."""
    w, _ = text_size(s, scale, thick, font)
    text(frame, s, (cx - w // 2, y), scale, color, thick, font, outline)


def shade(frame, x, y, w, h, alpha=0.35):
    """Darken a rectangle in place; only that region is touched."""
    fh, fw = frame.shape[:2]
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(fw, int(x + w)), min(fh, int(y + h))
    if x0 < x1 and y0 < y1:
        roi = frame[y0:y1, x0:x1]
        roi[:] = cv2.convertScaleAbs(roi, alpha=1 - alpha)


def bar(frame, x, y, w, h, frac, label=None):
    """Progress bar with an optional centered label."""
    cv2.rectangle(frame, (x, y), (x + w, y + h), CLR_BAR_BG, -1)
    if frac > 0:
        cv2.rectangle(frame, (x, y), (x + int(min(frac, 1.0) * w), y + h), CLR_BAR_FILL, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), CLR_BAR_BORDER, 2)
    if label:
        th = text_size(label, 0.6)[1]
        text_centered(frame, label, x + w // 2, y + (h + th) // 2, 0.6, CLR_TEXT, outline=True)


# --- screens -----------------------------------------------------------------

def draw_message(frame, lines):
    """Centered block of text lines, e.g. for error screens."""
    h, w = frame.shape[:2]
    line_h = 44
    y = (h - line_h * len(lines)) // 2 + line_h
    for s in lines:
        text_centered(frame, s, w // 2, y, 1.0, CLR_TEXT)
        y += line_h


def draw_start(frame, layout, prog, left_pinching, right_pinching):
    """Title screen with live L/R pinch indicators and the hold-to-start bar."""
    W, H = layout.win_w, layout.win_h
    shade(frame, 0, 0, W, H, 0.45)
    text_centered(frame, "MEMORY TILES", W // 2, int(H * 0.22), 3.0, CLR_ACCENT, 4, TITLE_FONT)
    text_centered(frame, "PINCH WITH BOTH HANDS AND HOLD TO START",
                  W // 2, int(H * 0.40), 1.0, CLR_TEXT)
    draw_hand_indicators(frame, W // 2, int(H * 0.52), left_pinching, right_pinching)
    if prog > 0:
        bar(frame, (W - 400) // 2, int(H * 0.62), 400, 22, prog)
    draw_controls(frame)


def draw_hand_indicators(frame, cx, cy, left, right):
    for label, on, dx in (("L", left, -70), ("R", right, 70)):
        color = CLR_SUCCESS if on else CLR_BAR_BORDER
        cv2.circle(frame, (cx + dx, cy), 34, CLR_BAR_BG, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx + dx, cy), 34, color, -1 if on else 3, cv2.LINE_AA)
        th = text_size(label, 1.2, 3)[1]
        text_centered(frame, label, cx + dx, cy + th // 2, 1.2,
                      CLR_BAR_BG if on else CLR_TEXT, 3)


def draw_game_over(frame, game, layout, prog):
    W, H = layout.win_w, layout.win_h
    shade(frame, 0, 0, W, H, 0.55)
    text_centered(frame, "GAME OVER", W // 2, int(H * 0.25), 3.0, CLR_FAIL, 4, TITLE_FONT)
    text_centered(frame, f"Score: {game.score}     Best: {game.best}",
                  W // 2, int(H * 0.38), 1.3, CLR_TEXT, 2)
    if game.score and game.score >= game.best:
        text_centered(frame, "NEW BEST!", W // 2, int(H * 0.46), 1.2, CLR_ACCENT, 3)
    text_centered(frame, "PINCH WITH BOTH HANDS TO PLAY AGAIN",
                  W // 2, int(H * 0.58), 1.0, CLR_TEXT)
    if prog > 0:
        bar(frame, (W - 400) // 2, int(H * 0.63), 400, 22, prog)
    draw_controls(frame)


# --- in-game -----------------------------------------------------------------

def _order_labels(seq):
    """tile -> "1,4" style 1-based positions where it appears in seq."""
    labels = {}
    for pos, tile in enumerate(seq, 1):
        labels[tile] = f"{labels[tile]},{pos}" if tile in labels else str(pos)
    return labels


def draw_tiles(frame, game, layout, now, hover=None):
    """The grid, colored for the current state. `hover` is the tile under the cursor."""
    state = game.state
    lit = game.highlighted_tile(now)
    flash = (game.player_input[-1] if game.player_input and game.last_pick_at is not None
             and now - game.last_pick_at < PICK_FLASH_S else None)

    if state is GameState.PLAYER_INPUT:
        labels = _order_labels(game.player_input)
    elif state in (GameState.LEVEL_SUCCESS, GameState.LEVEL_FAILED):
        labels = _order_labels(game.pattern)
    else:
        labels = {}

    wrong = None
    if state is GameState.LEVEL_FAILED and game.first_mistake is not None:
        wrong = game.player_input[game.first_mistake]

    t = layout.tile
    for i in range(layout.tile_count):
        x, y = layout.tile_xy(i)
        color, border, thick = CLR_DEFAULT, CLR_BORDER, 2

        if state is GameState.SHOWING_PATTERN and i == lit:
            color, thick = CLR_HILITE, 4
        elif state is GameState.PLAYER_INPUT:
            if i == flash or i == game.armed_tile:
                color = CLR_SELECTED
            if i == hover:
                border, thick = CLR_HOVER, 4
        elif state is GameState.LEVEL_SUCCESS and i in labels:
            color, thick = CLR_SUCCESS, 4
        elif state is GameState.LEVEL_FAILED:
            if i == wrong:
                color, thick = CLR_FAIL, 4
            elif i in labels:
                color, thick = CLR_HILITE, 4

        cv2.rectangle(frame, (x, y), (x + t, y + t), color, -1)
        cv2.rectangle(frame, (x, y), (x + t, y + t), border, thick)
        cv2.rectangle(frame, (x + 5, y + 5), (x + t - 5, y + t - 5), CLR_TEXT, 1)

        if i == wrong:
            m = t // 4
            cv2.line(frame, (x + m, y + m), (x + t - m, y + t - m), CLR_TEXT, 6, cv2.LINE_AA)
            cv2.line(frame, (x + t - m, y + m), (x + m, y + t - m), CLR_TEXT, 6, cv2.LINE_AA)
        elif i in labels:
            s = labels[i]
            scale = 1.2 if len(s) <= 2 else 0.8
            th = text_size(s, scale, 3)[1]
            text_centered(frame, s, x + t // 2, y + (t + th) // 2, scale, CLR_TEXT, 3, outline=True)


def draw_hud(frame, game, layout, now):
    W = layout.win_w
    shade(frame, 0, 0, W, 100)
    text(frame, f"LEVEL {game.level}", (30, 52), 1.5, CLR_TEXT, 3, TITLE_FONT)

    # Lives as dots, then score.
    for k in range(max(game.lives, 0)):
        cv2.circle(frame, (40 + k * 26, 76), 9, CLR_FAIL, -1, cv2.LINE_AA)
    text(frame, f"Score {game.score}   Best {game.best}", (40 + 3 * 26 + 10, 84), 0.7, CLR_MUTED)

    # Progress through the sequence.
    n = len(game.pattern)
    if game.state is GameState.SHOWING_PATTERN:
        done, label = game.show_idx + 1, f"Watch {min(game.show_idx + 1, n)}/{n}"
    elif game.state is GameState.PLAYER_INPUT:
        done, label = len(game.player_input), f"{len(game.player_input)}/{n}"
    else:
        done, label = 0, f"0/{n}"
    bar(frame, W - 330, 28, 300, 26, done / n if n else 0, label)

    if game.state in HINTS:
        s, color = HINTS[game.state]
        y = layout.origin_y - 40
        tw, th = text_size(s, 1.0)
        shade(frame, (W - tw) // 2 - 15, y - th - 12, tw + 30, th + 24, 0.45)
        text_centered(frame, s, W // 2, y, 1.0, color)

    draw_controls(frame)


def draw_controls(frame):
    """Control legend pinned to the bottom-left corner."""
    h = frame.shape[0]
    x, gap, pad = 18, 6, 10
    styles = [(0.7 if i == 0 else 0.55, 2 if i == 0 else 1) for i in range(len(CONTROLS))]
    sizes = [text_size(s, sc, th) for s, (sc, th) in zip(CONTROLS, styles)]
    block_h = sum(sh + gap for _, sh in sizes)
    block_w = max(sw for sw, _ in sizes)
    y = h - 18 - block_h

    shade(frame, x - pad, y - pad, block_w + 2 * pad, block_h + 2 * pad, 0.6)
    for i, (s, (sc, th), (_, sh)) in enumerate(zip(CONTROLS, styles, sizes)):
        y += sh
        text(frame, s, (x, y), sc, CLR_ACCENT if i == 0 else CLR_MUTED, th)
        y += gap


def draw_cursor(frame, cursor, pinching):
    if cursor is None:
        return
    x, y = cursor
    if pinching:
        cv2.circle(frame, (x, y), 15, CLR_PINCH, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 20, CLR_TEXT, 2, cv2.LINE_AA)
    else:
        s = 20
        cv2.line(frame, (x - s, y), (x + s, y), CLR_CURSOR, 2, cv2.LINE_AA)
        cv2.line(frame, (x, y - s), (x, y + s), CLR_CURSOR, 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 5, CLR_CURSOR, 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 2, CLR_TEXT, -1)


def show_debug_window(game, extra):
    """Separate debug window mirroring game state plus `extra` key/value pairs."""
    lines = [
        f"STATE: {game.state.name}",
        f"LEVEL: {game.level}  LIVES: {game.lives}  SCORE: {game.score}",
        f"PATTERN: {game.pattern}",
        f"PLAYER_INPUT: {game.player_input}",
        f"SHOW_IDX: {game.show_idx}",
        f"COOLDOWN_UNTIL: {game.cooldown_until:.2f}",
        f"ARMED_TILE: {game.armed_tile}",
    ] + [f"{k}: {v}" for k, v in extra.items()]
    w, pad = 560, 12
    img = np.zeros((26 + 22 * len(lines), w, 3), dtype=np.uint8)
    y = 26
    for i, s in enumerate(lines):
        text(img, s, (pad, y), 0.56, CLR_ACCENT if i == 0 else CLR_MUTED, 1)
        y += 22
    cv2.imshow("Debug", img)
