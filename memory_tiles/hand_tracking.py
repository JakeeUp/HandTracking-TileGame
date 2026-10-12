"""MediaPipe hand tracking and pinch detection."""
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import mediapipe as mp

from .geometry import dist

Point = Tuple[int, int]
WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9

# Bones between MediaPipe's 21 hand landmarks, for drawing the skeleton.
HAND_BONES = (
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # pinky and palm edge
)


@dataclass
class HandReading:
    """One detected hand, in window pixel coordinates."""
    label: str                 # "Left" / "Right" from the player's point of view
    score: float               # handedness confidence
    thumb: Point
    index: Point
    pinch_ratio: float         # thumb-index distance / palm length
    points: Tuple[Point, ...] = ()   # all 21 landmarks, for drawing

    @property
    def cursor(self) -> Point:
        """Midpoint between thumb and index tips."""
        return ((self.thumb[0] + self.index[0]) // 2,
                (self.thumb[1] + self.index[1]) // 2)


class HandTracker:
    def __init__(self, win_w, win_h):
        self.win_w, self.win_h = win_w, win_h
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )

    def process(self, frame_bgr) -> List[HandReading]:
        """Detect hands in a (mirrored) BGR frame."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        res = self._hands.process(rgb)
        if not (res.multi_hand_landmarks and res.multi_handedness):
            return []
        readings = []
        for lm, handed in zip(res.multi_hand_landmarks, res.multi_handedness):
            cls = handed.classification[0]
            readings.append(self._reading(lm.landmark, cls.label, cls.score))
        return readings

    def _reading(self, lm, label, score) -> HandReading:
        pts = tuple((int(p.x * self.win_w), int(p.y * self.win_h)) for p in lm)
        thumb, index = pts[THUMB_TIP], pts[INDEX_TIP]
        palm = max(dist(pts[WRIST], pts[MIDDLE_MCP]), 1.0)
        return HandReading(label, score, thumb, index, dist(thumb, index) / palm, pts)

    def close(self):
        self._hands.close()
