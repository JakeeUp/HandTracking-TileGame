import random

import pytest

from memory_tiles.config import (
    FAIL_DURATION,
    LIVES,
    MIN_TILE_SHOW_DURATION,
    PINCH_COOLDOWN_S,
    READY_DURATION,
    START_HOLD_S,
    SUCCESS_DURATION,
    TILE_SHOW_DURATION,
)
from memory_tiles.game import Game, GameState

EPS = 1e-6  # absorbs float drift when summing step durations


@pytest.fixture
def game():
    return Game(tile_count=16, rng=random.Random(1234))


def play_pattern(game, now):
    """Advance through READY and SHOWING_PATTERN; return the time input starts."""
    assert game.state is GameState.READY
    now += READY_DURATION + EPS
    game.update(now)
    for _ in game.pattern:
        now += game.step_duration + EPS
        game.update(now)
    assert game.state is GameState.PLAYER_INPUT
    return now


def tap(game, tile, now, hand="Right"):
    game.pinch_started(hand, tile, now)
    game.pinch_ended(hand, now)


def enter(game, tiles, now):
    for t in tiles:
        now += PINCH_COOLDOWN_S
        tap(game, t, now)
    return now


def wrong_tile(game, i):
    return (game.pattern[i] + 1) % game.tile_count


def clear_level(game, now):
    now = enter(game, game.pattern, play_pattern(game, now))
    assert game.state is GameState.LEVEL_SUCCESS
    now += SUCCESS_DURATION
    game.update(now)
    return now


# --- starting ----------------------------------------------------------------

def test_start_hold_requires_full_hold(game):
    game.update_start_hold(True, 0.0)
    game.update_start_hold(True, START_HOLD_S - 0.01)
    assert game.state is GameState.START_SCREEN
    assert 0.9 < game.start_hold_progress(START_HOLD_S - 0.01) < 1.0
    game.update_start_hold(True, START_HOLD_S)
    assert game.state is GameState.READY


def test_start_hold_resets_on_release(game):
    game.update_start_hold(True, 0.0)
    game.update_start_hold(False, 0.5)
    assert game.start_hold_progress(0.5) == 0.0
    game.update_start_hold(True, 0.6)
    game.update_start_hold(True, 0.6 + START_HOLD_S - 0.01)
    assert game.state is GameState.START_SCREEN


def test_start_hold_ignored_mid_game(game):
    game.start(0.0)
    pattern = list(game.pattern)
    game.update_start_hold(True, 1.0)
    game.update_start_hold(True, 1.0 + START_HOLD_S)
    assert game.state is GameState.READY and game.pattern == pattern


def test_pinch_held_through_last_failure_does_not_skip_game_over(game):
    game.start(0.0)
    game.lives = 1
    now = play_pattern(game, 0.0)
    tap(game, wrong_tile(game, 0), now)
    for t in (now, now + 1.0, now + FAIL_DURATION - 0.01):   # hold a pinch during feedback
        game.update_start_hold(True, t)
    now += FAIL_DURATION
    game.update(now)
    game.update_start_hold(True, now)
    assert game.state is GameState.GAME_OVER
    assert game.start_hold_progress(now) == 0.0
    game.update_start_hold(True, now + START_HOLD_S)    # a full fresh hold restarts
    assert game.state is GameState.READY


def test_start_resets_and_gives_one_tile(game):
    game.score, game.lives = 9, 0
    game.start(0.0)
    assert game.state is GameState.READY
    assert len(game.pattern) == 1 and 0 <= game.pattern[0] < 16
    assert (game.level, game.lives, game.score) == (1, LIVES, 0)


# --- showing the pattern -----------------------------------------------------

def test_ready_beat_before_pattern(game):
    game.start(0.0)
    assert game.highlighted_tile(0.0) is None
    game.update(READY_DURATION - 0.01)
    assert game.state is GameState.READY
    game.update(READY_DURATION)
    assert game.state is GameState.SHOWING_PATTERN


def test_pattern_tile_lit_then_paused(game):
    game.start(0.0)
    game.update(READY_DURATION)
    t = READY_DURATION
    assert game.highlighted_tile(t) == game.pattern[0]
    assert game.highlighted_tile(t + game.tile_show_duration + 0.01) is None


def test_showing_pattern_advances_on_schedule(game):
    game.start(0.0)
    game.update(READY_DURATION)
    game.update(READY_DURATION + game.step_duration - 0.01)
    assert game.state is GameState.SHOWING_PATTERN
    game.update(READY_DURATION + game.step_duration)
    assert game.state is GameState.PLAYER_INPUT


def test_show_duration_speeds_up_with_floor(game):
    assert game.tile_show_duration == TILE_SHOW_DURATION
    game.level = 5
    assert game.tile_show_duration < TILE_SHOW_DURATION
    game.level = 500
    assert game.tile_show_duration == MIN_TILE_SHOW_DURATION


# --- progression -------------------------------------------------------------

def test_success_extends_the_same_pattern(game):
    game.start(0.0)
    first = list(game.pattern)
    clear_level(game, 0.0)
    assert game.level == 2
    assert game.pattern[:1] == first and len(game.pattern) == 2
    assert game.state is GameState.READY


def test_pattern_never_repeats_a_tile_back_to_back():
    game = Game(tile_count=2, rng=random.Random(0))
    game.start(0.0)
    for _ in range(50):
        game._extend_pattern()
    assert all(a != b for a, b in zip(game.pattern, game.pattern[1:]))


def test_score_and_best_track_cleared_length(game):
    game.start(0.0)
    now = clear_level(game, 0.0)
    now = clear_level(game, now)
    assert game.score == 2 and game.best == 2
    assert game.new_best
    game.start(now)
    assert game.score == 0 and game.best == 2
    now = clear_level(game, now)
    now = clear_level(game, now)
    assert game.score == 2 and not game.new_best     # tying isn't a new best


# --- failing -----------------------------------------------------------------

def test_wrong_tile_fails_immediately(game):
    game.start(0.0)
    now = clear_level(game, 0.0)
    now = play_pattern(game, now)
    tap(game, wrong_tile(game, 0), now)         # first of two picks is wrong
    assert game.state is GameState.LEVEL_FAILED
    assert game.lives == LIVES - 1
    assert game.first_mistake == 0


def test_failing_replays_the_same_pattern(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    pattern = list(game.pattern)
    tap(game, wrong_tile(game, 0), now)
    game.update(now + FAIL_DURATION)
    assert game.state is GameState.READY
    assert game.pattern == pattern and game.player_input == []


def test_losing_all_lives_is_game_over(game):
    game.start(0.0)
    now = 0.0
    for _ in range(LIVES):
        now = play_pattern(game, now) + PINCH_COOLDOWN_S
        tap(game, wrong_tile(game, 0), now)
        now += FAIL_DURATION
        game.update(now)
    assert game.state is GameState.GAME_OVER
    game.update_start_hold(True, now)
    game.update_start_hold(True, now + START_HOLD_S)
    assert game.state is GameState.READY and game.lives == LIVES


# --- input -------------------------------------------------------------------

def test_input_ignored_outside_player_input(game):
    game.start(0.0)
    tap(game, 3, 0.1)
    assert game.player_input == []


def test_input_ignored_during_cooldown(game):
    game.start(0.0)
    game.pattern = [1, 2, 3]
    now = play_pattern(game, 0.0)
    tap(game, 1, now)
    tap(game, 2, now + PINCH_COOLDOWN_S / 2)
    assert game.player_input == [1]
    game.pinch_started("Right", 2, now + PINCH_COOLDOWN_S / 2)
    assert game.armed == {}               # never shows as armed
    tap(game, 2, now + PINCH_COOLDOWN_S)
    assert game.player_input == [1, 2]


def test_pinch_on_no_tile_commits_nothing(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    tap(game, None, now)
    assert game.player_input == []
    assert game.armed == {}


def test_pinch_started_before_input_phase_is_not_committed(game):
    """The start gesture (or a pinch during the pattern) can't become an answer."""
    game.start(0.0)
    game.pinch_started("Right", game.pattern[0], 0.0)   # still READY
    now = play_pattern(game, 0.0)
    game.pinch_ended("Right", now)
    assert game.player_input == []


def test_cancelled_pinch_commits_nothing(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    game.pinch_started("Right", 4, now)
    game.pinch_cancelled("Right")
    game.pinch_ended("Right", now)
    assert game.player_input == []


def test_restart_clears_transient_state(game):
    game.start(0.0)
    now = play_pattern(game, 0.0)
    game.pinch_started("Right", 5, now)
    game.cooldown_until["Right"] = now + 10
    game.best = 7
    game.restart()
    assert game.state is GameState.START_SCREEN
    assert (game.level, game.pattern, game.player_input) == (1, [], [])
    assert (game.lives, game.score, game.best) == (LIVES, 0, 7)
    assert game.armed == {}
    assert game.cooldown_until == {}


def test_either_hand_can_pick(game):
    game.start(0.0)
    game.pattern = [1, 2]
    now = play_pattern(game, 0.0)
    tap(game, 1, now, hand="Left")
    tap(game, 2, now + 0.05, hand="Right")       # other hand isn't held up by the cooldown
    assert game.player_input == [1, 2]
    assert game.state is GameState.LEVEL_SUCCESS


def test_hands_arm_independently(game):
    game.start(0.0)
    game.pattern = [1, 2]
    now = play_pattern(game, 0.0)
    game.pinch_started("Left", 1, now)
    game.pinch_started("Right", 2, now)
    game.pinch_cancelled("Right")                # losing one hand keeps the other's pick
    game.pinch_ended("Left", now)
    assert game.player_input == [1]
