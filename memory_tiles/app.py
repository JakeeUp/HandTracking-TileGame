"""Main loop: camera capture, hand tracking, game update and rendering."""
import time

import cv2

from .config import GRID_SIZE, TILE_SIZE, TILE_SPACING, WINDOW_H, WINDOW_W
from .game import Game, GameState
from .geometry import Layout
from .gestures import Gestures
from .hand_tracking import HandTracker
from .renderer import draw_cursor, draw_game_ui, draw_start, draw_tiles, show_debug_window


def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # more reliable on Windows
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)  # fallback

    layout = Layout.centered(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING)
    game = Game(tile_count=layout.tile_count)
    tracker = HandTracker(WINDOW_W, WINDOW_H)
    gestures = Gestures()
    show_debug = False

    cv2.namedWindow("Memory Tiles", cv2.WINDOW_GUI_NORMAL)
    print("Controls: Dual-pinch start | Right pinch select | D debug | R restart | Q quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.monotonic()

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (WINDOW_W, WINDOW_H))

        inp = gestures.update(tracker.process(frame))
        tracker.draw_landmarks(frame)

        # Arm on press, commit on release; losing the hand cancels.
        if inp.right_pressed:
            game.pinch_started(layout.tile_at(*inp.cursor))
        elif inp.right_released:
            game.pinch_ended(now)
        elif inp.right_lost:
            game.pinch_cancelled()

        game.update_dual_pinch(inp.left_pinching and inp.right_pinching, now)

        if game.state is GameState.START_SCREEN:
            draw_start(frame, layout, game.dual_pinch_progress(now))
        else:
            game.update(now)
            draw_tiles(frame, game, layout, now)
            draw_game_ui(frame, game, layout)
            draw_cursor(frame, inp.cursor, inp.right_pinching)

        cv2.imshow("Memory Tiles", frame)

        if show_debug:
            show_debug_window(game, {
                "LEFT_PINCH": inp.left_pinching,
                "RIGHT_PINCH": inp.right_pinching,
                "CURSOR": inp.cursor,
                "PINCH_RATIO L/R": " / ".join("-" if r is None else f"{r:.2f}" for r in inp.ratios),
            })
        else:
            try:
                cv2.destroyWindow("Debug")
            except cv2.error:
                pass

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            game.restart()
            gestures.reset()
        elif key == ord('d'):
            show_debug = not show_debug

    cap.release()
    cv2.destroyAllWindows()
