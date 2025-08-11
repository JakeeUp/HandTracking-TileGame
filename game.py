# game.py
import random, time
from state import GameModel, GameState
from config import TILE_SHOW_DURATION, PATTERN_PAUSE, FEEDBACK_DURATION, PINCH_COOLDOWN_S

def new_model(win_w, win_h, grid, tile, spacing, start_x, start_y):
    return GameModel(
        win_w=win_w, win_h=win_h, grid=grid, tile_size=tile, spacing=spacing,
        start_x=start_x, start_y=start_y
    )

def generate_pattern(model: GameModel):
    model.pattern = [random.randint(0, model.grid*model.grid - 1) for _ in range(model.level)]
    model.player_input.clear()
    model.show_idx = 0
    model.state = GameState.SHOWING_PATTERN
    model.last_mark = time.time()

def start_game(model: GameModel):
    model.level = 1
    generate_pattern(model)

def restart(model: GameModel):
    model.level = 1
    model.state = GameState.START_SCREEN
    model.hands.both_start_time = 0
    model.hands.left_pinching = False
    model.hands.right_pinching = False
    model.cursor.was_pinching = False
    model.armed_tile = -1
    model.player_input.clear()
    model.pattern.clear()

def update_state(model: GameModel):
    now = time.time()
    if model.state == GameState.SHOWING_PATTERN:
        if now - model.last_mark >= TILE_SHOW_DURATION + PATTERN_PAUSE:
            model.show_idx += 1
            model.last_mark = now
            if model.show_idx >= len(model.pattern):
                model.state = GameState.PLAYER_INPUT

    elif model.state == GameState.PLAYER_INPUT:
        if len(model.player_input) == len(model.pattern) and model.pattern:
            model.state = GameState.LEVEL_SUCCESS if model.player_input == model.pattern else GameState.LEVEL_FAILED
            model.last_mark = now

    elif model.state == GameState.LEVEL_SUCCESS:
        if now - model.last_mark > FEEDBACK_DURATION:
            model.level += 1
            generate_pattern(model)

    elif model.state == GameState.LEVEL_FAILED:
        if now - model.last_mark > FEEDBACK_DURATION:
            generate_pattern(model)

    if model.pinch_cooldown > 0:
        model.pinch_cooldown = max(0.0, model.pinch_cooldown - 1/30.0)

def start_pinch(model: GameModel, tile_idx: int):
    """Right-hand pinch begins: lock the tile under cursor (may be -1)."""
    model.armed_tile = tile_idx

def end_pinch(model: GameModel):
    """Right-hand pinch ends: commit exactly one selection (the armed tile)."""
    if model.state != GameState.PLAYER_INPUT:
        model.armed_tile = -1
        return
    if model.pinch_cooldown > 0:
        model.armed_tile = -1
        return
    if model.armed_tile != -1:
        model.player_input.append(model.armed_tile)
        model.pinch_cooldown = PINCH_COOLDOWN_S
    model.armed_tile = -1
