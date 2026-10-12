"""Game rules and state transitions.

Every method that depends on time takes `now` (seconds from a monotonic
clock) instead of reading the clock itself, so the rules can be driven
from tests without a camera or real waiting.
"""
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from .config import (
    DUAL_PINCH_HOLD_S, FEEDBACK_DURATION, PATTERN_PAUSE, PINCH_COOLDOWN_S,
    TILE_SHOW_DURATION,
)


class GameState(Enum):
    START_SCREEN = auto()
    SHOWING_PATTERN = auto()
    PLAYER_INPUT = auto()
    LEVEL_SUCCESS = auto()
    LEVEL_FAILED = auto()


@dataclass
class Game:
    tile_count: int
    rng: random.Random = field(default_factory=random.Random)

    state: GameState = GameState.START_SCREEN
    level: int = 1
    pattern: List[int] = field(default_factory=list)
    player_input: List[int] = field(default_factory=list)
    show_idx: int = 0
    phase_start: float = 0.0          # when the current state/pattern step began
    armed_tile: Optional[int] = None  # tile locked in by the current pinch
    cooldown_until: float = 0.0
    dual_pinch_since: Optional[float] = None

    # --- lifecycle -------------------------------------------------------

    def restart(self):
        """Back to the start screen with all transient state cleared."""
        self.state = GameState.START_SCREEN
        self.level = 1
        self.pattern.clear()
        self.player_input.clear()
        self.show_idx = 0
        self.armed_tile = None
        self.cooldown_until = 0.0
        self.dual_pinch_since = None

    def start(self, now: float):
        self.level = 1
        self._new_pattern(now)

    def _new_pattern(self, now: float):
        self.pattern = [self.rng.randrange(self.tile_count) for _ in range(self.level)]
        self.player_input.clear()
        self.show_idx = 0
        self.state = GameState.SHOWING_PATTERN
        self.phase_start = now

    # --- per-frame update ------------------------------------------------

    def update_dual_pinch(self, both_pinching: bool, now: float):
        """Start the game once both hands have pinched for DUAL_PINCH_HOLD_S."""
        if not both_pinching:
            self.dual_pinch_since = None
            return
        if self.dual_pinch_since is None:
            self.dual_pinch_since = now
        if (self.state is GameState.START_SCREEN
                and now - self.dual_pinch_since >= DUAL_PINCH_HOLD_S):
            self.start(now)

    def dual_pinch_progress(self, now: float) -> float:
        """0..1 progress of the dual-pinch hold on the start screen."""
        if self.dual_pinch_since is None:
            return 0.0
        return min(1.0, (now - self.dual_pinch_since) / DUAL_PINCH_HOLD_S)

    def update(self, now: float):
        if self.state is GameState.SHOWING_PATTERN:
            if now - self.phase_start >= TILE_SHOW_DURATION + PATTERN_PAUSE:
                self.show_idx += 1
                self.phase_start = now
                if self.show_idx >= len(self.pattern):
                    self.state = GameState.PLAYER_INPUT

        elif self.state is GameState.PLAYER_INPUT:
            if self.pattern and len(self.player_input) == len(self.pattern):
                self.state = (GameState.LEVEL_SUCCESS if self.player_input == self.pattern
                              else GameState.LEVEL_FAILED)
                self.phase_start = now

        elif self.state is GameState.LEVEL_SUCCESS:
            if now - self.phase_start > FEEDBACK_DURATION:
                self.level += 1
                self._new_pattern(now)

        elif self.state is GameState.LEVEL_FAILED:
            if now - self.phase_start > FEEDBACK_DURATION:
                self._new_pattern(now)

    def highlighted_tile(self, now: float) -> Optional[int]:
        """Tile currently lit while the pattern is being shown, if any."""
        if (self.state is GameState.SHOWING_PATTERN
                and self.show_idx < len(self.pattern)
                and now - self.phase_start < TILE_SHOW_DURATION):
            return self.pattern[self.show_idx]
        return None

    # --- input -----------------------------------------------------------

    def pinch_started(self, tile: Optional[int]):
        """Right-hand pinch begins: lock the tile under the cursor (may be None).

        Only arms during PLAYER_INPUT, so a pinch that began on the start
        screen or while the pattern was showing can't become an answer.
        """
        self.armed_tile = tile if self.state is GameState.PLAYER_INPUT else None

    def pinch_cancelled(self):
        """The hand was lost mid-pinch: drop the armed tile without committing."""
        self.armed_tile = None

    def pinch_ended(self, now: float):
        """Right-hand pinch ends: commit at most one selection (the armed tile)."""
        tile, self.armed_tile = self.armed_tile, None
        if self.state is not GameState.PLAYER_INPUT or now < self.cooldown_until:
            return
        if tile is not None:
            self.player_input.append(tile)
            self.cooldown_until = now + PINCH_COOLDOWN_S
