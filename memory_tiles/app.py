"""Entry point: camera settings window, then the game loop (capture, tracking,
game update, rendering)."""
import argparse
import sys
import time
from enum import Enum, auto

import cv2
import numpy as np

from .cameras import fit_frame, open_camera
from .config import (
    GRID_SIZE,
    MAX_FAILED_READS,
    TILE_SIZE,
    TILE_SPACING,
    WINDOW_H,
    WINDOW_W,
)
from .game import Game
from .geometry import Layout
from .gestures import Gestures
from .hand_tracking import HandTracker
from .renderer import draw_message, render, show_debug_window
from .settings import load, load_best, save, save_best

WINDOW = "Memory Tiles"
DEBUG_WINDOW = "Debug"
NO_CAMERA = ("Could not open that camera. Check that it is connected, not in use "
             "by another app, and that this app has camera permission.")
LOST_CAMERA = "Lost the camera feed. Pick a camera and try again."


class Outcome(Enum):
    QUIT = auto()
    SETTINGS = auto()      # player pressed C: back to the camera picker
    CAMERA_LOST = auto()


class CloseWatcher:
    """Detects the user closing a window with its X button.

    WND_PROP_VISIBLE reads 1 while shown and 0 once closed on Windows/GTK,
    but some backends always return -1 (unsupported). Only report "closed"
    after the window has been seen visible, so those backends don't quit
    on the first frame; Q/Esc still work there.
    """

    def __init__(self, name):
        self.name = name
        self.seen_visible = False

    def closed(self) -> bool:
        try:
            visible = cv2.getWindowProperty(self.name, cv2.WND_PROP_VISIBLE)
        except cv2.error:
            return self.seen_visible
        if visible >= 1:
            self.seen_visible = True
        return self.seen_visible and visible < 1


def show_fatal(message):
    """Show an error screen until a key is pressed or the window is closed.

    Packaged builds have no console, so printing to stderr alone would be invisible.
    """
    print(message, file=sys.stderr)
    frame = np.zeros((WINDOW_H, WINDOW_W, 3), dtype=np.uint8)
    draw_message(frame, message.splitlines() + ["", "Press any key to exit."])
    cv2.namedWindow(WINDOW, cv2.WINDOW_GUI_NORMAL)
    cv2.imshow(WINDOW, frame)
    watcher = CloseWatcher(WINDOW)
    while cv2.waitKey(100) == -1 and not watcher.closed():
        pass
    cv2.destroyAllWindows()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="memory_tiles", description="Memory Tiles")
    parser.add_argument("--camera", type=int, metavar="INDEX",
                        help="camera index to use; skips the camera settings window")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    error = None
    while True:
        if args.camera is not None:
            index = args.camera
        else:
            from .launcher import Launcher  # tkinter is only needed for the picker
            cam = Launcher(load().get("camera"), error).run()
            if cam is None:
                return 0
            save(camera=cam.name)
            index = cam.index

        outcome = play(index)
        if outcome is Outcome.QUIT:
            return 0
        error = None if outcome is Outcome.SETTINGS else (
            NO_CAMERA if outcome is None else LOST_CAMERA)
        if args.camera is not None and error:
            show_fatal(error)    # no picker to go back to
            return 1


def play(index):
    """Open camera `index` and run the game. Returns an Outcome, or None if the
    camera couldn't be opened."""
    cap = open_camera(index)
    if not cap.isOpened():
        cap.release()
        return None
    tracker = HandTracker(WINDOW_W, WINDOW_H)
    try:
        return run(cap, tracker)
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


def run(cap, tracker) -> Outcome:
    """The game loop."""
    layout = Layout.centered(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING)
    game = Game(tile_count=layout.tile_count, best=load_best())
    saved_best = game.best
    gestures = Gestures()
    show_debug = False
    fullscreen = False
    failed_reads = 0

    cv2.namedWindow(WINDOW, cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_KEEPRATIO)
    watcher = CloseWatcher(WINDOW)
    print("Controls: Pinch and hold to start | Pinch tiles with either hand | "
          "C camera | D debug | F fullscreen | R restart | Q/Esc quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            failed_reads += 1
            if failed_reads >= MAX_FAILED_READS:
                return Outcome.CAMERA_LOST
            cv2.waitKey(10)
            continue
        failed_reads = 0
        now = time.monotonic()

        frame = fit_frame(cv2.flip(frame, 1), WINDOW_W, WINDOW_H)

        inp = gestures.update(tracker.process(frame))

        # Either hand selects: arm on press, commit on release; losing the hand cancels.
        for hand in inp.hands.values():
            if hand.pressed and hand.cursor:
                game.pinch_started(hand.label, layout.tile_at(*hand.cursor), now)
            elif hand.released:
                game.pinch_ended(hand.label, now)
            elif hand.lost:
                game.pinch_cancelled(hand.label)

        game.update_start_hold(inp.any_pinching, now)
        game.update(now)
        render(frame, game, layout, inp, now)

        if game.best > saved_best:
            save_best(game.best)
            saved_best = game.best

        cv2.imshow(WINDOW, frame)
        if show_debug:
            show_debug_window(game, {
                **{f"{h.label.upper()}_HAND": (
                    "-" if h.cursor is None else
                    f"{h.cursor} ratio {h.ratio:.2f}{' PINCH' if h.pinching else ''}")
                   for h in inp.hands.values()},
            })

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27) or watcher.closed():
            return Outcome.QUIT
        elif key == ord('c'):
            return Outcome.SETTINGS
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
