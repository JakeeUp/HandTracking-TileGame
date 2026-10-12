import random

import pytest

from memory_tiles.config import (
    DUAL_PINCH_HOLD_S, FEEDBACK_DURATION, PATTERN_PAUSE, PINCH_COOLDOWN_S,
    TILE_SHOW_DURATION,
)
from memory_tiles.game import Game, GameState

STEP = TILE_SHOW_DURATION + PATTERN_PAUSE


@pytest.fixture
def game():
    return Game(tile_count=16, rng=random.Random(1234))


def play_pattern(game, now):
    """Advance through SHOWING_PATTERN and return the time input starts."""
    for _ in game.pattern:
        now += STEP
        game.update(now)
    assert game.state is GameState.PLAYER_INPUT
    return now


def tap(game, tile, now):
    game.pinch_started(tile)
    game.pinch_ended(now)


def enter(game, tiles, now):
    for t in tiles:
        now += PINCH_COOLDOWN_S
        tap(game, t, now)
    return now


def test_dual_pinch_requires_full_hold(game):
    game.update_dual_pinch(True, 0.0)
    game.update_dual_pinch(True, DUAL_PINCH_HOLD_S - 0.01)
    assert game.state is GameState.START_SCREEN
    assert 0.9 < game.dual_pinch_progress(DUAL_PINCH_HOLD_S - 0.01) < 1.0
    game.update_dual_pinch(True, DUAL_PINCH_HOLD_S)
    assert game.state is GameState.SHOWING_PATTERN


def test_dual_pinch_resets_on_release(game):
    game.update_dual_pinch(True, 0.0)
    game.update_dual_pinch(False, 0.5)
    assert game.dual_pinch_progress(0.5) == 0.0
    game.update_dual_pinch(True, 0.6)
    game.update_dual_pinch(True, 0.6 + DUAL_PINCH_HOLD_S - 0.01)
    assert game.state is GameState.START_SCREEN


def test_start_generates_level_one_pattern(game):
    game.start(0.0)
    assert game.state is GameState.SHOWING_PATTERN
    assert len(game.pattern) == 1
    assert all(0 <= t < 16 for t in game.pattern)


def test_pattern_tile_lit_then_paused(game):
    game.start(0.0)
    assert game.highlighted_tile(0.0) == game.pattern[0]
    assert game.highlighted_tile(TILE_SHOW_DURATION + 0.01) is None


def test_showing_pattern_advances_on_schedule(game):
    game.start(0.0)
    game.update(STEP - 0.01)
    assert game.state is GameState.SHOWING_PATTERN
    game.update(STEP)
    assert game.state is GameState.PLAYER_INPUT


def test_correct_input_levels_up(game):
    game.start(0.0)
    now = enter(game, game.pattern, play_pattern(game, 0.0))
    game.update(now)
    assert game.state is GameState.LEVEL_SUCCESS
    game.update(now + FEEDBACK_DURATION + 0.01)
    assert game.level == 2
    assert len(game.pattern) == 2
    assert game.state is GameState.SHOWING_PATTERN


def test_input_ignored_outside_player_input(game):
    game.start(0.0)
    tap(game, 3, 0.1)
    assert game.player_input == []


def test_input_ignored_during_cooldown(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    game.level = 3
    game.pattern = [1, 2, 3]
    tap(game, 1, now)
    tap(game, 2, now + PINCH_COOLDOWN_S / 2)
    assert game.player_input == [1]
    tap(game, 2, now + PINCH_COOLDOWN_S)
    assert game.player_input == [1, 2]


def test_pinch_on_no_tile_commits_nothing(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    tap(game, None, now)
    assert game.player_input == []
    assert game.armed_tile is None


def test_restart_clears_transient_state(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    game.pinch_started(5)
    game.cooldown_until = now + 10
    game.restart()
    assert game.state is GameState.START_SCREEN
    assert (game.level, game.pattern, game.player_input) == (1, [], [])
    assert game.armed_tile is None
    assert game.cooldown_until == 0.0
