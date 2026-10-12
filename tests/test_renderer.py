"""Smoke tests: every screen draws onto a frame without raising."""
import numpy as np
import pytest

from memory_tiles import renderer
from memory_tiles.game import Game, GameState
from memory_tiles.geometry import Layout
from memory_tiles.gestures import Gestures
from memory_tiles.hand_tracking import HandReading

LAYOUT = Layout.centered(1200, 900, grid=4, tile=110, spacing=16)


def frame():
    return np.full((LAYOUT.win_h, LAYOUT.win_w, 3), 120, dtype=np.uint8)


def hands(*readings):
    return Gestures().update(list(readings))


def reading(label, x, ratio, points=True):
    pts = tuple((x + 3 * i, 500 - 10 * i) for i in range(21)) if points else ()
    return HandReading(label, 0.9, (x, 400), (x + 10, 405), ratio, pts)


def sample_game(state):
    game = Game(tile_count=LAYOUT.tile_count)
    game.start(0.0)
    game.pattern, game.player_input, game.state = [0, 5, 10, 5], [0, 6], state
    game.armed, game.last_pick_at, game.best = {"Left": 3}, 0.0, 4
    return game


@pytest.mark.parametrize("state", list(GameState))
@pytest.mark.parametrize("now", [0.0, 0.1, 0.3, 2.0])
def test_render_every_state(state, now):
    f = frame()
    inp = hands(reading("Left", 300, 0.1), reading("Right", 900, 0.8))
    renderer.render(f, sample_game(state), LAYOUT, inp, now)
    assert f.any()


def test_render_with_no_hands_and_empty_pattern():
    game = Game(tile_count=LAYOUT.tile_count)
    game.state = GameState.PLAYER_INPUT
    renderer.render(frame(), game, LAYOUT, hands(), 0.0)


def test_hands_near_edges_are_clipped():
    f = frame()
    inp = hands(reading("Left", -40, 0.1), reading("Right", 1195, 0.35, points=False))
    renderer.render(f, sample_game(GameState.START_SCREEN), LAYOUT, inp, 0.0)


def test_message_screen():
    f = np.zeros((LAYOUT.win_h, LAYOUT.win_w, 3), np.uint8)
    renderer.draw_message(f, ["line one", "", "line three"])
    assert f.any()


def test_fill_rounded_blends_only_inside_and_clips():
    f = np.zeros((100, 100, 3), np.uint8)
    renderer.fill_rounded(f, 50, 50, 500, 500, 10, (200, 200, 200), alpha=0.5)
    assert f[0, 0, 0] == 0
    assert 95 <= f[99, 99, 0] <= 105


def test_tile_colors_are_distinct():
    colors = renderer.tile_colors(16)
    assert len(set(colors)) == 16


def test_order_labels_show_repeats():
    assert renderer._order_labels([3, 7, 3]) == {3: "1,3", 7: "2"}


def test_pinch_closeness_range():
    assert renderer.pinch_closeness(None) == 0.0
    assert renderer.pinch_closeness(5.0) == 0.0
    assert renderer.pinch_closeness(0.0) == 1.0
