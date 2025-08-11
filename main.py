# main.py
import cv2
from config import WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING
from state import GameState
from geometry import grid_anchor, tile_at
from hand_tracking import HandTracker
from renderer import draw_start, draw_tiles, draw_game_ui, draw_cursor, show_debug_window
from game import (
    new_model, start_game, restart, update_state, generate_pattern,
    start_pinch, end_pinch
)

def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # more reliable on Windows
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)  # fallback

    # Prepare layout
    start_x, start_y = grid_anchor(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING)
    model = new_model(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING, start_x, start_y)
    tracker = HandTracker(WINDOW_W, WINDOW_H)

    # Consistent window
    cv2.namedWindow("Memory Tiles", cv2.WINDOW_GUI_NORMAL)
    print("Controls: Dual-pinch start • Right pinch select • D debug • R restart • Q quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (WINDOW_W, WINDOW_H))

        res = tracker.process(frame)

        # reset per-frame flags
        model.hands.left_pinching = False
        model.hands.right_pinching = False
        right_pinching = False
        model.cursor.cursor = model.cursor.thumb = model.cursor.index = None

        if res.multi_hand_landmarks and res.multi_handedness:
            for lm, handed in zip(res.multi_hand_landmarks, res.multi_handedness):
                label = handed.classification[0].label  # "Left"/"Right"
                tracker.draw.draw_landmarks(frame, lm, tracker.mp_hands.HAND_CONNECTIONS)
                pinch, (cx, cy), thumb, index, lbl = tracker.detect_pinch(lm.landmark, label)

                if lbl == "Left":
                    model.hands.left_pinching = pinch
                else:
                    # Right hand
                    prev = model.cursor.was_pinching
                    model.hands.right_pinching = pinch
                    right_pinching = pinch
                    model.cursor.cursor, model.cursor.thumb, model.cursor.index = (cx, cy), thumb, index

                    # Edge-detect pinch state
                    if pinch and not prev:
                        # Pinch START — lock the tile under cursor (may be -1)
                        start_pinch(
                            model,
                            tile_at(cx, cy, model.grid, model.start_x, model.start_y, model.tile_size, model.spacing)
                        )
                    elif not pinch and prev:
                        # Pinch END — commit the armed tile exactly once
                        end_pinch(model)

                    model.cursor.was_pinching = pinch

        # dual-pinch to start
        if tracker.update_dual_pinch(model):
            start_game(model)

        # draw/update
        if model.state == GameState.START_SCREEN:
            draw_start(frame, model)
        else:
            update_state(model)
            draw_tiles(frame, model)
            draw_game_ui(frame, model)
            draw_cursor(frame, model, right_pinching)

        # show main window
        cv2.imshow("Memory Tiles", frame)

        # Debug window toggle
        if model.show_debug:
            show_debug_window(model)
        else:
            try:
                cv2.destroyWindow("Debug")
            except cv2.error:
                pass

        # input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            restart(model)
        elif key == ord('d'):
            model.show_debug = not model.show_debug

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
