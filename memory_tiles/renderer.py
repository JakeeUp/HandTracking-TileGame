"""OpenCV drawing for the game screens, HUD and debug window."""
import cv2
import numpy as np
from .config import (
    CLR_DEFAULT, CLR_BORDER, CLR_HILITE, CLR_SELECTED,
    CLR_SUCCESS, CLR_FAIL, CLR_TEXT,
)
from .game import GameState

def draw_bg(frame, x, y, w, h, alpha=0.30):
    overlay = frame.copy()
    cv2.rectangle(overlay, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 0), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

def draw_message(frame, lines):
    """Centered block of text lines, e.g. for error screens."""
    h, w = frame.shape[:2]
    line_h = 44
    y = (h - line_h * len(lines)) // 2 + line_h
    for text in lines:
        size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        cv2.putText(frame, text, ((w - size[0]) // 2, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, CLR_TEXT, 2, cv2.LINE_AA)
        y += line_h


def draw_start(frame, layout, prog):
    """Title screen; `prog` is the 0..1 dual-pinch hold progress."""
    draw_bg(frame, 0, 0, layout.win_w, layout.win_h)
    # Title
    title = "MEMORY TILES"
    size, _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 3.0, 4)
    cv2.putText(frame, title, ((layout.win_w - size[0]) // 2, 200),
                cv2.FONT_HERSHEY_DUPLEX, 3.0, (0, 255, 255), 4)

    txt = "PINCH WITH BOTH HANDS TO START" + (f"… {int(prog * 100)}%" if prog > 0 else "")
    size, _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
    cv2.putText(frame, txt, ((layout.win_w - size[0]) // 2, 400),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    if prog > 0:
        w, h = 400, 20
        x = (layout.win_w - w) // 2
        y = 450
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (150, 150, 150), 2)
        cv2.rectangle(frame, (x, y), (x + int(prog * w), y + h), (0, 255, 0), -1)

    # Always show controls
    draw_controls_bottom_left(frame)

def draw_tiles(frame, game, layout, now):
    lit = game.highlighted_tile(now)
    for i in range(layout.tile_count):
        x, y = layout.tile_xy(i)
        color, border, thick = CLR_DEFAULT, CLR_BORDER, 2

        if game.state is GameState.SHOWING_PATTERN:
            if i == lit:
                color, thick = CLR_HILITE, 4

        elif game.state is GameState.PLAYER_INPUT:
            if i in game.player_input:
                color, thick = CLR_SELECTED, 3

        elif game.state is GameState.LEVEL_SUCCESS:
            if i in game.pattern:
                color, thick = CLR_SUCCESS, 4

        elif game.state is GameState.LEVEL_FAILED:
            if i in game.pattern:
                color, thick = CLR_FAIL, 4
            elif i in game.player_input:
                color = (100, 100, 100)

        cv2.rectangle(frame, (x, y), (x + layout.tile, y + layout.tile), color, -1)
        cv2.rectangle(frame, (x, y), (x + layout.tile, y + layout.tile), border, thick)
        cv2.rectangle(frame, (x + 5, y + 5),
                      (x + layout.tile - 5, y + layout.tile - 5), (255, 255, 255), 1)

def draw_game_ui(frame, game, layout):
    # top bar
    draw_bg(frame, 0, 0, layout.win_w, 100)
    cv2.putText(frame, f"LEVEL {game.level}", (30, 50),
                cv2.FONT_HERSHEY_DUPLEX, 1.5, CLR_TEXT, 3)
    cv2.putText(frame, f"Pattern Length: {len(game.pattern)}", (30, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

    # progress
    w, h = 300, 25
    x = layout.win_w - w - 30
    y = 25
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (150, 150, 150), 2)
    if game.state is GameState.PLAYER_INPUT and game.pattern:
        fill = int((len(game.player_input) / len(game.pattern)) * w)
        cv2.rectangle(frame, (x, y), (x + fill, y + h), (0, 255, 100), -1)
    text = f"{len(game.player_input) if game.state is GameState.PLAYER_INPUT else 0}/{len(game.pattern)}"
    sz, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(frame, text, (x + (w - sz[0]) // 2, y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, CLR_TEXT, 2)

    # state hint
    state_y = layout.origin_y - 50
    mapping = {
        GameState.SHOWING_PATTERN: ("MEMORIZE THE PATTERN", (0, 255, 255)),
        GameState.PLAYER_INPUT: ("PINCH TILES IN THE CORRECT ORDER", (0, 255, 0)),
        GameState.LEVEL_SUCCESS: ("PERFECT! LEVEL COMPLETE!", (0, 255, 0)),
        GameState.LEVEL_FAILED: ("WRONG PATTERN! TRY AGAIN", (0, 100, 255)),
    }
    if game.state in mapping:
        text, color = mapping[game.state]
        tsz, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        tx = (layout.win_w - tsz[0]) // 2
        draw_bg(frame, tx - 15, state_y - 35, tsz[0] + 30, 45, 0.35)
        cv2.putText(frame, text, (tx, state_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    # Always draw controls last
    draw_controls_bottom_left(frame)

def draw_controls_bottom_left(frame):
    """Pinned control legend in bottom-left corner."""
    h, w = frame.shape[:2]
    lines = [
        "Controls:",
        "  Dual pinch = Start",
        "  Right pinch = Select tile",
        "  D = Debug  |  R = Restart  |  Q = Quit",
    ]
    margin = 18
    x = 18
    # Measure block
    block_h = 0
    sizes = []
    for i, t in enumerate(lines):
        scale = 0.7 if i == 0 else 0.6
        thick = 2 if i == 0 else 1
        sz, _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        sizes.append((sz, scale, thick))
        block_h += sz[1] + 6
    y0 = h - margin - block_h

    # Background panel
    bg_pad = 10
    max_w = max(sz[0] for sz, *_ in sizes)
    cv2.rectangle(frame, (x - bg_pad, y0 - bg_pad),
                  (x + max_w + bg_pad, y0 + block_h + bg_pad),
                  (0, 0, 0), -1)
    cv2.rectangle(frame, (x - bg_pad, y0 - bg_pad),
                  (x + max_w + bg_pad, y0 + block_h + bg_pad),
                  (40, 40, 40), 1)

    # Text
    y = y0
    for i, text in enumerate(lines):
        sz, scale, thick = sizes[i]
        color = (0, 255, 255) if i == 0 else (220, 220, 220)
        cv2.putText(frame, text, (x, y + sz[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
        y += sz[1] + 6

def draw_cursor(frame, cursor, pinching):
    if cursor is None:
        return
    x, y = cursor
    if pinching:
        cv2.circle(frame, (x, y), 15, (255, 0, 255), -1)
        cv2.circle(frame, (x, y), 20, (255, 255, 255), 2)
        cv2.putText(frame, "PINCH!", (x + 25, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    else:
        s = 20
        t = 2
        cv2.line(frame, (x - s, y), (x + s, y), (0, 255, 0), t)
        cv2.line(frame, (x, y - s), (x, y + s), (0, 255, 0), t)
        cv2.circle(frame, (x, y), 5, (0, 255, 0), 2)
        cv2.circle(frame, (x, y), 2, (255, 255, 255), -1)

def show_debug_window(game, extra):
    """Separate debug window mirroring game state plus `extra` key/value pairs."""
    lines = [
        f"STATE: {game.state.name}",
        f"LEVEL: {game.level}",
        f"PATTERN: {game.pattern}",
        f"PLAYER_INPUT: {game.player_input}",
        f"SHOW_IDX: {game.show_idx}",
        f"COOLDOWN_UNTIL: {game.cooldown_until:.2f}",
        f"ARMED_TILE: {game.armed_tile}",
    ] + [f"{k}: {v}" for k, v in extra.items()]
    w, pad = 560, 12
    h = 26 + 22 * len(lines)
    img = np.zeros((h, w, 3), dtype=np.uint8)
    y = 26
    for i, s in enumerate(lines):
        col = (0, 255, 255) if i == 0 else (210, 210, 210)
        cv2.putText(img, s, (pad, y), cv2.FONT_HERSHEY_SIMPLEX, 0.56, col, 1, cv2.LINE_AA)
        y += 22
    cv2.imshow("Debug", img)
