"""Smoke tests: every screen draws onto a blank frame without raising."""
import numpy as np
import pytest

from memory_tiles import renderer
from memory_tiles.game import Game, GameState
from memory_tiles.geometry import Layout

LAYOUT = Layout.centered(1200, 900, grid=4, tile=100, spacing=20)


def blank():
    return np.zeros((LAYOUT.win_h, LAYOUT.win_w, 3), dtype=np.uint8)


@pytest.mark.parametrize("prog", [0.0, 0.5, 1.0])
def test_start_screen(prog):
    frame = blank()
    renderer.draw_start(frame, LAYOUT, prog)
    assert frame.any()


@pytest.mark.parametrize("state", [s for s in GameState if s is not GameState.START_SCREEN])
def test_game_screens(state):
    game = Game(tile_count=LAYOUT.tile_count)
    game.start(0.0)
    game.pattern, game.player_input, game.state = [0, 5, 5], [0, 6], state
    frame = blank()
    renderer.draw_tiles(frame, game, LAYOUT, 0.0)
    renderer.draw_game_ui(frame, game, LAYOUT)
    renderer.draw_cursor(frame, (600, 450), pinching=True)
    renderer.draw_cursor(frame, (600, 450), pinching=False)
    renderer.draw_cursor(frame, None, pinching=False)
    assert frame.any()


def test_message_screen():
    frame = blank()
    renderer.draw_message(frame, ["line one", "", "line three"])
    assert frame.any()
