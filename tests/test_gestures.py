from memory_tiles.config import PINCH_OFF_RATIO, PINCH_ON_RATIO
from memory_tiles.gestures import Gestures, PinchSwitch, assign_hands
from memory_tiles.hand_tracking import HandReading

OPEN, PINCH = 1.0, 0.1
BETWEEN = (PINCH_ON_RATIO + PINCH_OFF_RATIO) / 2


def hand(label, ratio, x=600, score=0.9):
    return HandReading(label, score, (x, 400), (x, 420), ratio)


def test_cursor_is_midpoint():
    assert hand("Right", OPEN).cursor == (600, 410)


def test_pinch_switch_hysteresis():
    s = PinchSwitch()
    assert not s.update(BETWEEN)           # not pressed until below ON
    assert s.update(PINCH)
    assert s.update(BETWEEN)               # stays pressed until above OFF
    assert not s.update(PINCH_OFF_RATIO + 0.01)


def test_pinch_switch_releases_when_hand_lost():
    s = PinchSwitch()
    s.update(PINCH)
    assert not s.update(None)


def test_assign_hands_uses_labels_when_distinct():
    l, r = hand("Left", OPEN, x=900), hand("Right", OPEN, x=300)
    assert assign_hands([r, l]) == {"Left": l, "Right": r}


def test_assign_hands_falls_back_to_position_on_duplicate_labels():
    a, b = hand("Right", OPEN, x=300), hand("Right", OPEN, x=900)
    assert assign_hands([b, a]) == {"Left": a, "Right": b}


def test_assign_hands_keeps_two_most_confident():
    a, b = hand("Left", OPEN, score=0.9), hand("Right", OPEN, score=0.8)
    junk = hand("Right", OPEN, score=0.1)
    assert assign_hands([junk, a, b]) == {"Left": a, "Right": b}


def test_press_release_edges():
    g = Gestures()
    assert g.update([hand("Right", PINCH)]).right_pressed
    held = g.update([hand("Right", PINCH)])
    assert held.right_pinching and not held.right_pressed
    rel = g.update([hand("Right", OPEN)])
    assert rel.right_released and not rel.right_lost


def test_hand_lost_mid_pinch_is_not_a_release():
    g = Gestures()
    g.update([hand("Right", PINCH)])
    lost = g.update([])
    assert lost.right_lost and not lost.right_released
    back = g.update([hand("Right", OPEN)])        # returns open: no stale release
    assert not back.right_released and not back.right_pressed


def test_both_hands_pinching():
    inp = Gestures().update([hand("Left", PINCH, x=300), hand("Right", PINCH, x=900)])
    assert inp.left_pinching and inp.right_pinching
    assert inp.cursor == (900, 410)
