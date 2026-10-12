"""Smoke tests: every screen draws onto a blank frame without raising."""
import numpy as np
import pytest

from memory_tiles import renderer
from memory_tiles.game import Game, GameState
from memory_tiles.geometry import Layout

LAYOUT = Layout.centered(1200, 900, grid=4, tile=100, spacing=20)


def blank():
    return np.zeros((LAYOUT.win_h, LAYOUT.win_w, 3), dtype=np.uint8)


def sample_game(state):
    game = Game(tile_count=LAYOUT.tile_count)
    game.start(0.0)
    game.pattern, game.player_input, game.state = [0, 5, 10, 5], [0, 6], state
    game.armed_tile, game.last_pick_at = 3, 0.0
    return game


@pytest.mark.parametrize("prog", [0.0, 0.5, 1.0])
def test_start_screen(prog):
    frame = blank()
    renderer.draw_start(frame, LAYOUT, prog, left_pinching=True, right_pinching=False)
    assert frame.any()


def test_game_over_screen():
    frame = blank()
    renderer.draw_game_over(frame, sample_game(GameState.GAME_OVER), LAYOUT, 0.5)
    assert frame.any()


@pytest.mark.parametrize("state", [s for s in GameState
                                   if s not in (GameState.START_SCREEN, GameState.GAME_OVER)])
def test_game_screens(state):
    game = sample_game(state)
    frame = blank()
    renderer.draw_tiles(frame, game, LAYOUT, 0.0, hover=7)
    renderer.draw_hud(frame, game, LAYOUT, 0.0)
    renderer.draw_cursor(frame, (600, 450), pinching=True)
    renderer.draw_cursor(frame, (600, 450), pinching=False)
    renderer.draw_cursor(frame, None, pinching=False)
    assert frame.any()


def test_message_screen():
    frame = blank()
    renderer.draw_message(frame, ["line one", "", "line three"])
    assert frame.any()


def test_shade_darkens_only_the_region_and_clips():
    frame = np.full((100, 100, 3), 200, np.uint8)
    renderer.shade(frame, 50, 50, 500, 500, alpha=0.5)   # extends past the edge
    assert frame[0, 0, 0] == 200
    assert frame[99, 99, 0] == 100


def test_order_labels_show_repeats():
    assert renderer._order_labels([3, 7, 3]) == {3: "1,3", 7: "2"}


def test_hud_text_is_ascii():
    texts = [s for s, _ in renderer.HINTS.values()] + renderer.CONTROLS
    assert all(s.isascii() for s in texts)
