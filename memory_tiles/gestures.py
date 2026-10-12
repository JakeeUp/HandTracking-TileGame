"""Turns per-frame hand readings into game input.

Pinch state uses hysteresis (separate press/release thresholds) so a
finger hovering near the threshold doesn't flicker, and a hand that
vanishes mid-pinch is reported as `lost` rather than as a release, so
the game can cancel instead of committing a stale selection.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import PINCH_OFF_RATIO, PINCH_ON_RATIO
from .hand_tracking import HandReading


class PinchSwitch:
    """Debounced pinch: presses below PINCH_ON_RATIO, releases above PINCH_OFF_RATIO."""

    def __init__(self, on=PINCH_ON_RATIO, off=PINCH_OFF_RATIO):
        assert on < off
        self.on, self.off = on, off
        self.pressed = False

    def update(self, ratio: Optional[float]) -> bool:
        """Feed the thumb-index ratio, or None when the hand isn't visible."""
        if ratio is None:
            self.pressed = False
        elif self.pressed:
            self.pressed = ratio < self.off
        else:
            self.pressed = ratio < self.on
        return self.pressed


def assign_hands(readings: List[HandReading]) -> Dict[str, HandReading]:
    """Map readings to "Left"/"Right".

    MediaPipe sometimes labels both hands the same. When that happens, fall
    back to screen position: in the mirrored frame the player's left hand is
    on the left.
    """
    if len(readings) >= 2:
        a, b = sorted(readings, key=lambda r: r.score, reverse=True)[:2]
        if a.label == b.label:
            a, b = sorted((a, b), key=lambda r: r.cursor[0])
            return {"Left": a, "Right": b}
        return {a.label: a, b.label: b}
    return {r.label: r for r in readings}


@dataclass
class HandsInput:
    left_pinching: bool = False
    right_pinching: bool = False
    cursor: Optional[Tuple[int, int]] = None   # right-hand cursor, if visible
    right_pressed: bool = False                # pinch started this frame
    right_released: bool = False               # pinch ended this frame (hand visible)
    right_lost: bool = False                   # hand vanished while pinching
    ratios: Tuple[Optional[float], Optional[float]] = (None, None)  # (left, right), for tuning


class Gestures:
    def __init__(self):
        self.left = PinchSwitch()
        self.right = PinchSwitch()

    def reset(self):
        self.left.pressed = self.right.pressed = False

    def update(self, readings: List[HandReading]) -> HandsInput:
        hands = assign_hands(readings)
        left, right = hands.get("Left"), hands.get("Right")

        was_right = self.right.pressed
        left_pinching = self.left.update(left.pinch_ratio if left else None)
        right_pinching = self.right.update(right.pinch_ratio if right else None)

        return HandsInput(
            left_pinching=left_pinching,
            right_pinching=right_pinching,
            cursor=right.cursor if right else None,
            right_pressed=right_pinching and not was_right,
            right_released=was_right and not right_pinching and right is not None,
            right_lost=was_right and right is None,
            ratios=(left.pinch_ratio if left else None, right.pinch_ratio if right else None),
        )
