# hand_tracking.py
import cv2, mediapipe as mp, time
from utils import dist
from config import PINCH_THRESHOLD, DUAL_PINCH_HOLD_S

class HandTracker:
    def __init__(self, win_w, win_h):
        self.win_w, self.win_h = win_w, win_h
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,              
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.draw = mp.solutions.drawing_utils

    def process(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return self.hands.process(rgb)

    def detect_pinch(self, lm, label):
        thumb = lm[4]; index = lm[8]
        tx, ty = int(thumb.x*self.win_w), int(thumb.y*self.win_h)
        ix, iy = int(index.x*self.win_w), int(index.y*self.win_h)
        d = dist((tx,ty), (ix,iy))
        pinch = (d / self.win_w) < PINCH_THRESHOLD
        cx, cy = (tx+ix)//2, (ty+iy)//2
        return pinch, (cx,cy), (tx,ty), (ix,iy), label

    def update_dual_pinch(self, model):
        now = time.time()
        if model.hands.left_pinching and model.hands.right_pinching:
            if model.hands.both_start_time == 0:
                model.hands.both_start_time = now
            elif now - model.hands.both_start_time >= DUAL_PINCH_HOLD_S:
                # signal start
                if model.state.name == "START_SCREEN":
                    return True
        else:
            model.hands.both_start_time = 0
        return False
