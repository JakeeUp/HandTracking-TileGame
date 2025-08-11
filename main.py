# main.py
import cv2, time
from config import *
from state import GameState
from geometry import grid_anchor, tile_at
from hand_tracking import HandTracker
from renderer import draw_start, draw_tiles, draw_game_ui, draw_cursor
from game import new_model, start_game, restart, update_state, handle_right_pinch, generate_pattern

def main():
    cap = cv2.VideoCapture(0)
    ow = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    oh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    start_x, start_y = grid_anchor(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING)
    model = new_model(WINDOW_W, WINDOW_H, GRID_SIZE, TILE_SIZE, TILE_SPACING, start_x, start_y)

    tracker = HandTracker(WINDOW_W, WINDOW_H)
    print("Controls: Dual-pinch to start • R restart • D debug • Q quit")

    while True:
        ok, frame = cap.read()
        if not ok: break
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
                pinch, (cx,cy), thumb, index, lbl = tracker.detect_pinch(lm.landmark, label)

                if lbl == "Left":
                    model.hands.left_pinching = pinch
                else:
                    model.hands.right_pinching = pinch
                    right_pinching = pinch
                    model.cursor.cursor, model.cursor.thumb, model.cursor.index = (cx,cy), thumb, index

                    if pinch and not model.cursor.was_pinching:
                        handle_right_pinch(model, cx, cy,
                            lambda x,y: tile_at(x, y, model.grid, model.start_x, model.start_y, model.tile_size, model.spacing))
                    model.cursor.was_pinching = pinch

        # check dual pinch to start
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

        cv2.imshow("Memory Tiles", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'): break
        elif k == ord('r'): restart(model)
        elif k == ord('d'): model.show_debug = not model.show_debug

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        import mediapipe, numpy
    except ImportError as e:
        print(f"Missing library: {e}")
        print("pip install opencv-python mediapipe numpy")
        raise
    main()
