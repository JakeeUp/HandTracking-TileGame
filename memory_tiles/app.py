"""Main loop: camera capture, hand tracking, game update and rendering."""
import sys
import time

import cv2
import numpy as np

from .config import (
    CAMERA_INDEX,
    GRID_SIZE,
    MAX_FAILED_READS,
    TILE_SIZE,
    TILE_SPACING,
    WINDOW_H,
    WINDOW_W,
)
from .game import Game, GameState
from .geometry import Layout
from .gestures import Gestures
from .hand_tracking import HandTracker
from .renderer import (
    draw_cursor,
    draw_game_over,
    draw_hud,
    draw_message,
    draw_start,
    draw_tiles,
    show_debug_window,
)
from .scores import load_best, save_best

WINDOW = "Memory Tiles"
DEBUG_WINDOW = "Debug"
NO_CAMERA = ("Could not open the webcam.\n"
             "Check that it is connected, not in use by another app,\n"
             "and that this app has camera permission.")
LOST_CAMERA = "Lost the webcam feed."


def open_camera(index=CAMERA_INDEX):
    """Open the webcam, preferring DirectShow on Windows (faster to start there)."""
    if sys.platform == "win32":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(index)


def fit_frame(frame, w, h):
    """Center-crop `frame` to the w:h aspect ratio, then resize (no stretching)."""
    fh, fw = frame.shape[:2]
    if fw * h > fh * w:                 # too wide: trim the sides
        cw = fh * w // h
        x0 = (fw - cw) // 2
        frame = frame[:, x0:x0 + cw]
    elif fw * h < fh * w:               # too tall: trim top and bottom
        ch = fw * h // w
        y0 = (fh - ch) // 2
        frame = frame[y0:y0 + ch, :]
    return cv2.resize(frame, (w, h))


def window_closed(name):
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def show_fatal(message):
    """Show an error screen until a key is pressed or the window is closed.

    Packaged builds have no console, so printing to stderr alone would be invisible.
    """
    print(message, file=sys.stderr)
    frame = np.zeros((WINDOW_H, WINDOW_W, 3), dtype=np.uint8)
    draw_message(frame, message.splitlines() + ["", "Press any key to exit."])
    cv2.namedWindow(WINDOW, cv2.WINDOW_GUI_NORMAL)
    cv2.imshow(WINDOW, frame)
    while cv2.waitKey(100) == -1 and not window_closed(WINDOW):
        pass
    cv2.destroyAllWindows()


def main():
    cap = open_camera()
    if not cap.isOpened():
        show_fatal(NO_CAMERA)
        return 1

    tracker = HandTracker(WINDOW_W, WINDOW_H)
    try:
        error = run(cap, tracker)
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
    if error:
        show_fatal(error)
        return 1
    return 0


def run(cap, tracker):
    """Game loop. Returns an error message, or None when the player quits."""
    layout = Layout.centered(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING)
    game = Game(tile_count=layout.tile_count, best=load_best())
    saved_best = game.best
    gestures = Gestures()
    show_debug = False
    fullscreen = False
    failed_reads = 0

    cv2.namedWindow(WINDOW, cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_KEEPRATIO)
    print("Controls: Dual-pinch start | Right pinch select | "
          "D debug | F fullscreen | R restart | Q/Esc quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            failed_reads += 1
            if failed_reads >= MAX_FAILED_READS:
                return LOST_CAMERA
            cv2.waitKey(10)
            continue
        failed_reads = 0
        now = time.monotonic()

        frame = fit_frame(cv2.flip(frame, 1), WINDOW_W, WINDOW_H)

        inp = gestures.update(tracker.process(frame))
        tracker.draw_landmarks(frame)

        # Arm on press, commit on release; losing the hand cancels.
        if inp.right_pressed and inp.cursor:
            game.pinch_started(layout.tile_at(*inp.cursor))
        elif inp.right_released:
            game.pinch_ended(now)
        elif inp.right_lost:
            game.pinch_cancelled()

        game.update_dual_pinch(inp.left_pinching and inp.right_pinching, now)

        game.update(now)

        if game.state is GameState.START_SCREEN:
            draw_start(frame, layout, game.dual_pinch_progress(now),
                       inp.left_pinching, inp.right_pinching)
        elif game.state is GameState.GAME_OVER:
            draw_game_over(frame, game, layout, game.dual_pinch_progress(now))
        else:
            hover = layout.tile_at(*inp.cursor) if inp.cursor else None
            draw_tiles(frame, game, layout, now, hover)
            draw_hud(frame, game, layout, now)
        draw_cursor(frame, inp.cursor, inp.right_pinching)
        if game.best > saved_best:
            save_best(game.best)
            saved_best = game.best

        cv2.imshow(WINDOW, frame)
        if show_debug:
            show_debug_window(game, {
                "LEFT_PINCH": inp.left_pinching,
                "RIGHT_PINCH": inp.right_pinching,
                "CURSOR": inp.cursor,
                "PINCH_RATIO L/R": " / ".join("-" if r is None else f"{r:.2f}" for r in inp.ratios),
            })

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27) or window_closed(WINDOW):
            return None
        elif key == ord('r'):
            game.restart()
            gestures.reset()
        elif key == ord('d'):
            show_debug = not show_debug
            if not show_debug:
                try:
                    cv2.destroyWindow(DEBUG_WINDOW)
                except cv2.error:
                    pass  # already closed by the user
        elif key == ord('f'):
            fullscreen = not fullscreen
            cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
