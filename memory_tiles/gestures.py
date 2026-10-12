"""Turns per-frame hand readings into game input.

Pinch state uses hysteresis (separate press/release thresholds) so a
finger hovering near the threshold doesn't flicker, and a hand that
vanishes mid-pinch is reported as `lost` rather than as a release, so
the game can cancel instead of committing a stale selection. Each hand is
tracked independently and either one can select tiles.
"""
from dataclasses import dataclass, field
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


HANDS = ("Left", "Right")


@dataclass
class HandState:
    """One hand's input this frame. Either hand can select tiles."""
    label: str
    cursor: Optional[Tuple[int, int]] = None   # None when the hand isn't visible
    ratio: Optional[float] = None              # thumb-index / palm length, for tuning
    points: Tuple[Tuple[int, int], ...] = ()   # 21 landmarks, for drawing the skeleton
    pinching: bool = False
    pressed: bool = False                      # pinch started this frame
    released: bool = False                     # pinch ended this frame (hand visible)
    lost: bool = False                         # hand vanished while pinching


@dataclass
class HandsInput:
    hands: Dict[str, HandState] = field(
        default_factory=lambda: {label: HandState(label) for label in HANDS})

    @property
    def any_pinching(self) -> bool:
        return any(h.pinching for h in self.hands.values())

    @property
    def visible(self) -> List[HandState]:
        return [h for h in self.hands.values() if h.cursor is not None]


class Gestures:
    def __init__(self):
        self.switches = {label: PinchSwitch() for label in HANDS}

    def reset(self):
        for switch in self.switches.values():
            switch.pressed = False

    def update(self, readings: List[HandReading]) -> HandsInput:
        assigned = assign_hands(readings)
        out = HandsInput()
        for label, switch in self.switches.items():
            reading = assigned.get(label)
            was = switch.pressed
            now = switch.update(reading.pinch_ratio if reading else None)
            out.hands[label] = HandState(
                label=label,
                cursor=reading.cursor if reading else None,
                ratio=reading.pinch_ratio if reading else None,
                points=reading.points if reading else (),
                pinching=now,
                pressed=now and not was,
                released=was and not now and reading is not None,
                lost=was and reading is None,
            )
        return out
