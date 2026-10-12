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
    left, right = hand("Left", OPEN, x=900), hand("Right", OPEN, x=300)
    assert assign_hands([right, left]) == {"Left": left, "Right": right}


def test_assign_hands_falls_back_to_position_on_duplicate_labels():
    a, b = hand("Right", OPEN, x=300), hand("Right", OPEN, x=900)
    assert assign_hands([b, a]) == {"Left": a, "Right": b}


def test_assign_hands_keeps_two_most_confident():
    a, b = hand("Left", OPEN, score=0.9), hand("Right", OPEN, score=0.8)
    junk = hand("Right", OPEN, score=0.1)
    assert assign_hands([junk, a, b]) == {"Left": a, "Right": b}


def test_press_release_edges():
    g = Gestures()
    assert g.update([hand("Right", PINCH)]).hands["Right"].pressed
    held = g.update([hand("Right", PINCH)]).hands["Right"]
    assert held.pinching and not held.pressed
    rel = g.update([hand("Right", OPEN)]).hands["Right"]
    assert rel.released and not rel.lost


def test_hand_lost_mid_pinch_is_not_a_release():
    g = Gestures()
    g.update([hand("Right", PINCH)])
    lost = g.update([]).hands["Right"]
    assert lost.lost and not lost.released
    back = g.update([hand("Right", OPEN)]).hands["Right"]   # returns open: no stale release
    assert not back.released and not back.pressed


def test_hands_are_independent():
    g = Gestures()
    inp = g.update([hand("Left", PINCH, x=300), hand("Right", OPEN, x=900)])
    assert inp.hands["Left"].pressed and not inp.hands["Right"].pinching
    assert inp.any_pinching
    assert [h.cursor for h in inp.visible] == [(300, 410), (900, 410)]


def test_no_hands():
    inp = Gestures().update([])
    assert not inp.any_pinching and inp.visible == []
