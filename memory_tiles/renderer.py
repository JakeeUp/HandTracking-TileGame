"""All drawing: background, tiles, HUD, hands and the menu screens.

Visual style: the camera feed is dimmed and the UI sits on top as
translucent "glass" cards and rounded tiles, each tile with its own hue.
Text uses the bundled Poppins font (see text.py). Everything is drawn
into the camera frame in place; masks and glows are cached by size so a
frame costs a handful of small blends.
"""
import math
from functools import cache, lru_cache

import cv2
import numpy as np

from .config import (
    BACKGROUND_DIM,
    CLR_ACCENT,
    CLR_FAIL,
    CLR_HAND,
    CLR_MUTED,
    CLR_PANEL,
    CLR_SUCCESS,
    CLR_TEXT,
    LIVES,
    PICK_FLASH_S,
    PINCH_OFF_RATIO,
    PINCH_ON_RATIO,
)
from .game import GameState
from .hand_tracking import HAND_BONES
from .text import blend, draw_text, text_size

TILE_RADIUS = 18
CARD_RADIUS = 18
CARD_EDGE = (90, 78, 70)
DARK_TEXT = (40, 30, 25)
CONTROLS_HINT = "V record    C camera    M mirror    D debug    F fullscreen    R restart    Q quit"

HINTS = {
    GameState.READY: ("Get ready...", CLR_ACCENT),
    GameState.SHOWING_PATTERN: ("Watch the pattern", CLR_ACCENT),
    GameState.PLAYER_INPUT: ("Your turn - pinch the tiles in order", CLR_SUCCESS),
    GameState.LEVEL_SUCCESS: ("Perfect!", CLR_SUCCESS),
    GameState.LEVEL_FAILED: ("Wrong tile - watch again", CLR_FAIL),
}


# --- small helpers -----------------------------------------------------------

def clamp01(t):
    return 0.0 if t < 0 else 1.0 if t > 1 else t


def ease_out(t):
    return 1 - (1 - clamp01(t)) ** 3


def scale_color(color, k):
    return tuple(min(255, int(c * k)) for c in color)


@cache
def tile_colors(n):
    """A distinct, evenly spaced hue for each tile (BGR)."""
    hsv = np.array([[(int(180 * i / n), 190, 255) for i in range(n)]], dtype=np.uint8)
    return [tuple(int(c) for c in px) for px in cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0]]


# --- shapes --------------------------------------------------------------------

@lru_cache(maxsize=128)
def _rounded_mask(h, w, r):
    """0..1 float mask (h, w, 1) of an anti-aliased rounded rectangle."""
    r = max(0, min(r, w // 2, h // 2))
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - 1 - r, h - 1), 255, -1)
    cv2.rectangle(m, (0, r), (w - 1, h - 1 - r), 255, -1)
    for cx, cy in ((r, r), (w - 1 - r, r), (r, h - 1 - r), (w - 1 - r, h - 1 - r)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return (m.astype(np.float32) / 255.0)[..., None]


@lru_cache(maxsize=128)
def _glow_mask(h, w, r, spread):
    pad = spread * 2
    m = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
    m[pad:pad + h, pad:pad + w] = _rounded_mask(h, w, r)[..., 0]
    return cv2.GaussianBlur(m, (0, 0), spread)[..., None]


def fill_rounded(frame, x, y, w, h, r, color, alpha=1.0):
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w <= 0 or h <= 0:
        return
    solid = np.broadcast_to(np.float32(color), (h, w, 3))
    blend(frame, solid, _rounded_mask(h, w, r) * alpha, x, y)


def stroke_rounded(frame, x, y, w, h, r, color, thickness=2):
    x, y, w, h = int(x), int(y), int(w), int(h)
    r = max(1, min(r, w // 2, h // 2))
    aa = cv2.LINE_AA
    cv2.line(frame, (x + r, y), (x + w - r, y), color, thickness, aa)
    cv2.line(frame, (x + r, y + h), (x + w - r, y + h), color, thickness, aa)
    cv2.line(frame, (x, y + r), (x, y + h - r), color, thickness, aa)
    cv2.line(frame, (x + w, y + r), (x + w, y + h - r), color, thickness, aa)
    for (cx, cy), start in (((x + r, y + r), 180), ((x + w - r, y + r), 270),
                            ((x + w - r, y + h - r), 0), ((x + r, y + h - r), 90)):
        cv2.ellipse(frame, (cx, cy), (r, r), 0, start, start + 90, color, thickness, aa)


def glow(frame, x, y, w, h, r, color, strength=0.8, spread=16):
    """Additive soft halo around a rounded rectangle."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    m = _glow_mask(h, w, r, spread)
    pad = spread * 2
    gx, gy = x - pad, y - pad
    fh, fw = frame.shape[:2]
    x0, y0 = max(gx, 0), max(gy, 0)
    x1, y1 = min(gx + m.shape[1], fw), min(gy + m.shape[0], fh)
    if x0 >= x1 or y0 >= y1:
        return
    sub = m[y0 - gy:y1 - gy, x0 - gx:x1 - gx]
    roi = frame[y0:y1, x0:x1]
    roi[:] = np.minimum(roi + sub * (np.float32(color) * strength), 255).astype(np.uint8)


def glass_card(frame, x, y, w, h, r=CARD_RADIUS, alpha=0.62, edge=CARD_EDGE):
    fill_rounded(frame, x, y, w, h, r, CLR_PANEL, alpha)
    stroke_rounded(frame, x, y, w, h, r, edge, 1)


def heart(frame, cx, cy, size, color, filled=True):
    t = np.linspace(0, 2 * np.pi, 40)
    xs = 16 * np.sin(t) ** 3
    ys = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    pts = np.stack([cx + xs * size / 16, cy + ys * size / 16], axis=1).astype(np.int32)
    if filled:
        cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)


def progress_track(frame, cx, y, w, frac, color=CLR_ACCENT):
    fill_rounded(frame, cx - w // 2, y, w, 8, 4, CLR_PANEL, 0.8)
    if frac > 0:
        fill_rounded(frame, cx - w // 2, y, max(8, int(w * clamp01(frac))), 8, 4, color)


def dim(frame, k):
    cv2.convertScaleAbs(frame, dst=frame, alpha=k)


# --- entry point ---------------------------------------------------------------

def render(frame, game, layout, inp, now):
    """Draw the whole UI for the current state onto the camera frame."""
    dim(frame, BACKGROUND_DIM)
    hold = game.start_hold_progress(now)
    if game.state is GameState.START_SCREEN:
        draw_start(frame, layout, hold, inp, game.best)
    elif game.state is GameState.GAME_OVER:
        draw_game_over(frame, game, layout, hold)
    else:
        hover = {layout.tile_at(*h.cursor) for h in inp.visible} - {None}
        draw_tiles(frame, game, layout, now, hover)
        draw_hud(frame, game, layout)
    for hand in inp.visible:
        draw_hand(frame, hand, hold if hand.pinching else 0.0)


def draw_message(frame, lines):
    """Centered block of text lines, e.g. for error screens."""
    h, w = frame.shape[:2]
    line_h = 46
    y = (h - line_h * len(lines)) // 2
    for s in lines:
        draw_text(frame, s, (w // 2, y), 28, CLR_TEXT, "semibold", anchor="mt")
        y += line_h


# --- menu screens --------------------------------------------------------------

def draw_title(frame, cx, y, size=92):
    first, second = "MEMORY ", "TILES"
    w1, _ = text_size(first, size, "bold")
    w2, _ = text_size(second, size, "bold")
    x = cx - (w1 + w2) // 2
    draw_text(frame, first, (x, y), size, CLR_TEXT, "bold", anchor="lm")
    draw_text(frame, second, (x + w1, y), size, CLR_ACCENT, "bold", anchor="lm")


def draw_hand_chips(frame, cx, cy, inp):
    labels = (("Left", "LEFT HAND"), ("Right", "RIGHT HAND"))
    gap, h = 20, 46
    widths = [text_size(t, 18, "semibold")[0] + 48 for _, t in labels]
    x = cx - (sum(widths) + gap) // 2
    for (key, text), w in zip(labels, widths):
        hand, color = inp.hands[key], CLR_HAND[key]
        if hand.pinching:
            fill_rounded(frame, x, cy - h // 2, w, h, h // 2, color, 0.9)
            fg = DARK_TEXT
        else:
            glass_card(frame, x, cy - h // 2, w, h, h // 2,
                       edge=color if hand.cursor else CARD_EDGE)
            fg = CLR_TEXT if hand.cursor else CLR_MUTED
        draw_text(frame, text, (x + w // 2, cy), 18, fg, "semibold", anchor="mm",
                  shadow=not hand.pinching)
        x += w + gap


def draw_start(frame, layout, hold, inp, best):
    W, H = layout.win_w, layout.win_h
    dim(frame, 0.75)
    draw_title(frame, W // 2, int(H * 0.27))
    draw_text(frame, "A hand-tracking memory game", (W // 2, int(H * 0.36)), 26,
              CLR_MUTED, anchor="mm")
    draw_hand_chips(frame, W // 2, int(H * 0.50), inp)
    draw_text(frame, "Pinch and hold with either hand to start", (W // 2, int(H * 0.62)),
              30, CLR_TEXT, "semibold", anchor="mm")
    progress_track(frame, W // 2, int(H * 0.67), 380, hold)
    if best:
        draw_text(frame, f"Best: {best}", (W // 2, int(H * 0.74)), 22, CLR_MUTED, anchor="mm")
    draw_footer(frame)


def draw_game_over(frame, game, layout, hold):
    W, H = layout.win_w, layout.win_h
    dim(frame, 0.7)
    cw, ch = 560, 380
    x, y = (W - cw) // 2, (H - ch) // 2 - 20
    glass_card(frame, x, y, cw, ch, 28, alpha=0.75)
    draw_text(frame, "GAME OVER", (W // 2, y + 70), 60, CLR_FAIL, "bold", anchor="mm")
    draw_text(frame, "SCORE", (W // 2 - 110, y + 140), 18, CLR_MUTED, "semibold", anchor="mm")
    draw_text(frame, "BEST", (W // 2 + 110, y + 140), 18, CLR_MUTED, "semibold", anchor="mm")
    draw_text(frame, str(game.score), (W // 2 - 110, y + 190), 56, CLR_TEXT, "bold",
              anchor="mm")
    draw_text(frame, str(game.best), (W // 2 + 110, y + 190), 56, CLR_TEXT, "bold",
              anchor="mm")
    if game.new_best:
        draw_text(frame, "NEW BEST!", (W // 2, y + 250), 28, CLR_ACCENT, "bold", anchor="mm")
    draw_text(frame, "Pinch and hold to play again", (W // 2, y + 305), 24, CLR_TEXT,
              anchor="mm")
    progress_track(frame, W // 2, y + 335, 320, hold)
    draw_footer(frame)


def draw_footer(frame):
    h, w = frame.shape[:2]
    draw_text(frame, CONTROLS_HINT, (w // 2, h - 20), 16, CLR_MUTED, anchor="mb", alpha=0.85)


# --- in-game -------------------------------------------------------------------

def _order_labels(seq):
    """tile -> "1,4" style 1-based positions where it appears in seq."""
    labels = {}
    for pos, tile in enumerate(seq, 1):
        labels[tile] = f"{labels[tile]},{pos}" if tile in labels else str(pos)
    return labels


def draw_tiles(frame, game, layout, now, hover=()):
    """The grid, styled for the current state. `hover`: tiles under a cursor."""
    state, t = game.state, layout.tile
    colors = tile_colors(layout.tile_count)
    lit = game.highlighted_tile(now)
    phase_age = now - game.phase_start
    pick_age = now - game.last_pick_at if game.last_pick_at is not None else math.inf
    last_pick = game.player_input[-1] if game.player_input else None
    armed = set(game.armed.values())

    if state is GameState.PLAYER_INPUT:
        labels = _order_labels(game.player_input)
    elif state in (GameState.LEVEL_SUCCESS, GameState.LEVEL_FAILED):
        labels = _order_labels(game.pattern)
    else:
        labels = {}
    wrong = None
    if state is GameState.LEVEL_FAILED and game.first_mistake is not None:
        wrong = game.player_input[game.first_mistake]

    for i in range(layout.tile_count):
        x, y = layout.tile_xy(i)
        hue, mode, grow, dx = colors[i], "idle", 0.0, 0.0

        if state is GameState.SHOWING_PATTERN and i == lit:
            mode, grow = "lit", 3 + 6 * (1 - ease_out(phase_age / 0.2))
        elif state is GameState.PLAYER_INPUT:
            if i in armed:
                mode, grow = "armed", -3
            elif i == last_pick and pick_age < PICK_FLASH_S:
                mode, grow = "lit", 5 * (1 - ease_out(pick_age / PICK_FLASH_S))
        elif state is GameState.LEVEL_SUCCESS and i in labels:
            order = game.pattern.index(i)
            if phase_age > order * 0.06:            # green wave in sequence order
                mode, grow = "success", 3
        elif state is GameState.LEVEL_FAILED:
            if i == wrong:
                mode = "fail"
                dx = math.sin(phase_age * 45) * 8 * max(0.0, 1 - phase_age / 0.5)
            elif i in labels:
                mode = "answer"

        hovered = state is GameState.PLAYER_INPUT and i in hover
        g = int(round(grow))
        draw_tile(frame, x - g + dx, y - g, t + 2 * g, hue, mode, hovered)

        cx, cy = int(x + t / 2 + dx), y + t // 2
        if i == wrong:
            m = t // 4
            for (ax, ay), (bx, by) in (((-m, -m), (m, m)), ((m, -m), (-m, m))):
                cv2.line(frame, (cx + ax, cy + ay), (cx + bx, cy + by), CLR_TEXT, 7, cv2.LINE_AA)
        elif i in labels:
            s = labels[i]
            draw_text(frame, s, (cx, cy), 40 if len(s) <= 2 else 26, CLR_TEXT, "bold",
                      anchor="mm")

    # Ripple out of the tile that was just picked.
    picking = (GameState.PLAYER_INPUT, GameState.LEVEL_SUCCESS, GameState.LEVEL_FAILED)
    if last_pick is not None and pick_age < 0.45 and state in picking:
        k = pick_age / 0.45
        px, py = layout.tile_xy(last_pick)
        radius = int(t * 0.55 + ease_out(k) * t * 0.9)
        cv2.circle(frame, (px + t // 2, py + t // 2), radius, colors[last_pick],
                   max(1, int(5 * (1 - k))), cv2.LINE_AA)


def draw_tile(frame, x, y, size, hue, mode="idle", hovered=False):
    r = TILE_RADIUS
    if mode == "idle":
        fill_rounded(frame, x, y, size, size, r, CLR_PANEL, 0.55)
        stroke_rounded(frame, x, y, size, size, r, scale_color(hue, 0.6), 2)
    elif mode == "lit":
        glow(frame, x, y, size, size, r, hue, 0.9)
        fill_rounded(frame, x, y, size, size, r, hue, 0.95)
        stroke_rounded(frame, x, y, size, size, r, CLR_TEXT, 2)
    elif mode == "armed":
        fill_rounded(frame, x, y, size, size, r, hue, 0.6)
        stroke_rounded(frame, x, y, size, size, r, hue, 3)
    elif mode == "success":
        glow(frame, x, y, size, size, r, CLR_SUCCESS, 0.7)
        fill_rounded(frame, x, y, size, size, r, CLR_SUCCESS, 0.9)
    elif mode == "fail":
        glow(frame, x, y, size, size, r, CLR_FAIL, 1.0)
        fill_rounded(frame, x, y, size, size, r, CLR_FAIL, 0.95)
    elif mode == "answer":
        fill_rounded(frame, x, y, size, size, r, hue, 0.8)
        stroke_rounded(frame, x, y, size, size, r, CLR_TEXT, 2)
    # Glassy sheen on the top half.
    fill_rounded(frame, x + 4, y + 4, size - 8, size // 2 - 4, r - 4, (255, 255, 255), 0.06)
    if hovered:
        stroke_rounded(frame, x - 5, y - 5, size + 10, size + 10, r + 5, CLR_TEXT, 3)


def draw_hud(frame, game, layout):
    W = layout.win_w

    # Level + lives.
    glass_card(frame, 20, 20, 270, 88)
    draw_text(frame, "LEVEL", (42, 36), 16, CLR_MUTED, "semibold")
    draw_text(frame, str(game.level), (42, 58), 36, CLR_TEXT, "bold")
    for k in range(LIVES):
        heart(frame, 150 + k * 40, 66, 15, CLR_FAIL if k < game.lives else CLR_MUTED,
              filled=k < game.lives)

    # Score + best.
    glass_card(frame, W - 290, 20, 270, 88)
    for label, value, x in (("SCORE", game.score, W - 268), ("BEST", game.best, W - 148)):
        draw_text(frame, label, (x, 36), 16, CLR_MUTED, "semibold")
        draw_text(frame, str(value), (x, 58), 36, CLR_TEXT, "bold")

    # State hint pill above the grid.
    if game.state in HINTS:
        s, color = HINTS[game.state]
        tw, _ = text_size(s, 26, "semibold")
        pw, ph = tw + 56, 52
        px, py = (W - pw) // 2, layout.origin_y - ph - 24
        glass_card(frame, px, py, pw, ph, ph // 2, alpha=0.7, edge=scale_color(color, 0.8))
        draw_text(frame, s, (W // 2, py + ph // 2), 26, color, "semibold", anchor="mm")

    draw_progress_dots(frame, game, W // 2, layout.origin_y + layout.span + 34)
    draw_footer(frame)


def draw_progress_dots(frame, game, cx, cy):
    """One dot per step of the sequence: filled = done, ring = current."""
    n = len(game.pattern)
    if not n:
        return
    state = game.state
    if state is GameState.SHOWING_PATTERN:
        done, current = game.show_idx, game.show_idx
    elif state is GameState.PLAYER_INPUT:
        done, current = len(game.player_input), len(game.player_input)
    elif state is GameState.LEVEL_SUCCESS:
        done, current = n, None
    else:
        done, current = 0, None
    wrong = game.first_mistake if state is GameState.LEVEL_FAILED else None

    step = min(26, 600 // n)
    r = max(3, min(7, step // 3))
    x = cx - step * (n - 1) // 2
    for k in range(n):
        p = (x + k * step, cy)
        if k == wrong:
            cv2.circle(frame, p, r + 1, CLR_FAIL, -1, cv2.LINE_AA)
        elif k < done:
            cv2.circle(frame, p, r, CLR_ACCENT, -1, cv2.LINE_AA)
        elif k == current:
            cv2.circle(frame, p, r + 1, CLR_ACCENT, 2, cv2.LINE_AA)
        else:
            cv2.circle(frame, p, r, CLR_MUTED, 1, cv2.LINE_AA)


# --- hands ---------------------------------------------------------------------

def pinch_closeness(ratio):
    """0 for an open hand up to 1 at the pinch threshold (for the cursor ring)."""
    if ratio is None:
        return 0.0
    open_ratio = PINCH_OFF_RATIO * 2
    return clamp01((open_ratio - ratio) / (open_ratio - PINCH_ON_RATIO))


def draw_hand(frame, hand, hold=0.0):
    """Skeleton in the hand's color plus a cursor between thumb and index."""
    color = CLR_HAND.get(hand.label, CLR_ACCENT)
    pts = hand.points
    if pts:
        bone = scale_color(color, 0.75)
        for a, b in HAND_BONES:
            cv2.line(frame, pts[a], pts[b], bone, 2, cv2.LINE_AA)
        for p in pts:
            cv2.circle(frame, p, 3, CLR_TEXT, -1, cv2.LINE_AA)
    draw_cursor(frame, hand.cursor, hand.pinching, color, pinch_closeness(hand.ratio), hold)


def draw_cursor(frame, cursor, pinching, color=CLR_ACCENT, closeness=0.0, hold=0.0):
    """Ring that fills as the fingers close; solid dot while pinching; outer arc
    shows start-hold progress."""
    if cursor is None:
        return
    x, y = cursor
    if pinching:
        cv2.circle(frame, (x, y), 14, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 19, CLR_TEXT, 2, cv2.LINE_AA)
    else:
        cv2.circle(frame, (x, y), 18, color, 2, cv2.LINE_AA)
        if closeness > 0:
            cv2.ellipse(frame, (x, y), (18, 18), -90, 0, 360 * closeness, color, 5,
                        cv2.LINE_AA)
        cv2.circle(frame, (x, y), 3, CLR_TEXT, -1, cv2.LINE_AA)
    if hold > 0:
        cv2.ellipse(frame, (x, y), (30, 30), -90, 0, 360 * hold, CLR_ACCENT, 5, cv2.LINE_AA)


# --- overlays (drawn after the frame is recorded) -------------------------------

def draw_rec_badge(frame, elapsed):
    """Blinking REC badge with the recording time, top center."""
    w = frame.shape[1]
    label = f"REC  {int(elapsed) // 60}:{int(elapsed) % 60:02d}"
    tw, _ = text_size(label, 18, "semibold")
    bw, bh = tw + 52, 38
    x, y = (w - bw) // 2, 20
    glass_card(frame, x, y, bw, bh, bh // 2, alpha=0.8, edge=CLR_FAIL)
    if int(elapsed * 2) % 2 == 0:
        cv2.circle(frame, (x + 20, y + bh // 2), 7, CLR_FAIL, -1, cv2.LINE_AA)
    draw_text(frame, label, (x + 34, y + bh // 2), 18, CLR_TEXT, "semibold", anchor="lm")


def draw_toast(frame, message):
    """Short status message near the bottom of the screen."""
    h, w = frame.shape[:2]
    tw, _ = text_size(message, 20, "semibold")
    bw, bh = min(tw + 48, w - 40), 46
    x, y = (w - bw) // 2, h - 110
    glass_card(frame, x, y, bw, bh, bh // 2, alpha=0.85)
    draw_text(frame, message, (w // 2, y + bh // 2), 20, CLR_TEXT, "semibold", anchor="mm")


# --- debug ---------------------------------------------------------------------

def show_debug_window(game, extra):
    """Separate debug window mirroring game state plus `extra` key/value pairs."""
    lines = [
        f"STATE: {game.state.name}",
        f"LEVEL: {game.level}  LIVES: {game.lives}  SCORE: {game.score}",
        f"PATTERN: {game.pattern}",
        f"PLAYER_INPUT: {game.player_input}",
        f"SHOW_IDX: {game.show_idx}",
        f"ARMED: {game.armed}",
    ] + [f"{k}: {v}" for k, v in extra.items()]
    img = np.zeros((26 + 22 * len(lines), 620, 3), dtype=np.uint8)
    for i, s in enumerate(lines):
        cv2.putText(img, s, (12, 26 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.56,
                    CLR_ACCENT if i == 0 else CLR_MUTED, 1, cv2.LINE_AA)
    cv2.imshow("Debug", img)
