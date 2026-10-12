"""MediaPipe hand tracking and pinch detection."""
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import mediapipe as mp

from .geometry import dist

WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9


@dataclass
class HandReading:
    """One detected hand, in window pixel coordinates."""
    label: str                 # "Left" / "Right" from the player's point of view
    score: float               # handedness confidence
    thumb: Tuple[int, int]
    index: Tuple[int, int]
    pinch_ratio: float         # thumb-index distance / palm length

    @property
    def cursor(self) -> Tuple[int, int]:
        """Midpoint between thumb and index tips."""
        return ((self.thumb[0] + self.index[0]) // 2,
                (self.thumb[1] + self.index[1]) // 2)


class HandTracker:
    def __init__(self, win_w, win_h):
        self.win_w, self.win_h = win_w, win_h
        self._mp_hands = mp.solutions.hands
        self._draw = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self._last = None

    def process(self, frame_bgr) -> List[HandReading]:
        """Detect hands in a (mirrored) BGR frame."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        self._last = res = self._hands.process(rgb)
        if not (res.multi_hand_landmarks and res.multi_handedness):
            return []
        readings = []
        for lm, handed in zip(res.multi_hand_landmarks, res.multi_handedness):
            cls = handed.classification[0]
            readings.append(self._reading(lm.landmark, cls.label, cls.score))
        return readings

    def _px(self, p):
        return int(p.x * self.win_w), int(p.y * self.win_h)

    def _reading(self, lm, label, score) -> HandReading:
        thumb, index = self._px(lm[THUMB_TIP]), self._px(lm[INDEX_TIP])
        palm = max(dist(self._px(lm[WRIST]), self._px(lm[MIDDLE_MCP])), 1.0)
        return HandReading(label, score, thumb, index, dist(thumb, index) / palm)

    def draw_landmarks(self, frame):
        """Overlay the skeletons from the last processed frame."""
        if self._last and self._last.multi_hand_landmarks:
            for lm in self._last.multi_hand_landmarks:
                self._draw.draw_landmarks(frame, lm, self._mp_hands.HAND_CONNECTIONS)
