# state.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import time

class GameState(Enum):
    START_SCREEN = 0
    SHOWING_PATTERN = 1
    PLAYER_INPUT = 2
    LEVEL_SUCCESS = 3
    LEVEL_FAILED = 4

@dataclass
class HandFlags:
    left_pinching: bool = False
    right_pinching: bool = False
    both_start_time: float = 0.0

@dataclass
class CursorInfo:
    cursor: Optional[Tuple[int, int]] = None
    thumb: Optional[Tuple[int, int]] = None
    index: Optional[Tuple[int, int]] = None
    was_pinching: bool = False

@dataclass
class GameModel:
    win_w: int
    win_h: int
    grid: int
    tile_size: int
    spacing: int
    start_x: int
    start_y: int

    state: GameState = GameState.START_SCREEN
    level: int = 1
    pattern: List[int] = field(default_factory=list)
    player_input: List[int] = field(default_factory=list)
    show_idx: int = 0
    last_mark: float = field(default_factory=time.time)

    hands: HandFlags = field(default_factory=HandFlags)
    cursor: CursorInfo = field(default_factory=CursorInfo)

    pinch_cooldown: float = 0.0
    show_debug: bool = False

    armed_tile: int = -1
