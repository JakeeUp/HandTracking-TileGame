"""Game rules and state transitions.

Simon-style: each level appends one tile to the sequence. A wrong pick
fails the round immediately and costs a life; the same sequence is then
replayed. Losing every life ends the game.

Every method that depends on time takes `now` (seconds from a monotonic
clock) instead of reading the clock itself, so the rules can be driven
from tests without a camera or real waiting.
"""
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from .config import (
    DUAL_PINCH_HOLD_S,
    FAIL_DURATION,
    LIVES,
    MIN_TILE_SHOW_DURATION,
    PATTERN_PAUSE,
    PINCH_COOLDOWN_S,
    READY_DURATION,
    SHOW_SPEEDUP,
    SUCCESS_DURATION,
    TILE_SHOW_DURATION,
)


class GameState(Enum):
    START_SCREEN = auto()
    READY = auto()              # short beat before the pattern plays
    SHOWING_PATTERN = auto()
    PLAYER_INPUT = auto()
    LEVEL_SUCCESS = auto()
    LEVEL_FAILED = auto()
    GAME_OVER = auto()


@dataclass
class Game:
    tile_count: int
    rng: random.Random = field(default_factory=random.Random)
    best: int = 0                     # best score this session (seeded from disk by the app)

    state: GameState = GameState.START_SCREEN
    level: int = 1
    lives: int = LIVES
    score: int = 0                    # longest sequence completed this game
    pattern: List[int] = field(default_factory=list)
    player_input: List[int] = field(default_factory=list)
    show_idx: int = 0
    phase_start: float = 0.0          # when the current state/pattern step began
    armed_tile: Optional[int] = None  # tile locked in by the current pinch
    cooldown_until: float = 0.0
    last_pick_at: Optional[float] = None
    dual_pinch_since: Optional[float] = None

    # --- lifecycle -------------------------------------------------------

    def restart(self):
        """Back to the start screen with all transient state cleared."""
        self.state = GameState.START_SCREEN
        self.level = 1
        self.lives = LIVES
        self.score = 0
        self.pattern.clear()
        self.player_input.clear()
        self.show_idx = 0
        self.armed_tile = None
        self.cooldown_until = 0.0
        self.last_pick_at = None
        self.dual_pinch_since = None

    def start(self, now: float):
        self.restart()
        self._extend_pattern()
        self._begin_round(now)

    def _extend_pattern(self):
        """Append one tile, never the same as the previous one (it would be hard to see)."""
        choices = [t for t in range(self.tile_count) if not self.pattern or t != self.pattern[-1]]
        self.pattern.append(self.rng.choice(choices))

    def _begin_round(self, now: float):
        self.player_input.clear()
        self.show_idx = 0
        self._enter(GameState.READY, now)

    def _enter(self, state: GameState, now: float):
        self.state = state
        self.phase_start = now

    # --- timing ----------------------------------------------------------

    @property
    def tile_show_duration(self) -> float:
        """How long each pattern tile stays lit; shrinks a little every level."""
        return max(MIN_TILE_SHOW_DURATION, TILE_SHOW_DURATION * SHOW_SPEEDUP ** (self.level - 1))

    @property
    def step_duration(self) -> float:
        return self.tile_show_duration + PATTERN_PAUSE

    # --- per-frame update ------------------------------------------------

    def update_dual_pinch(self, both_pinching: bool, now: float):
        """Start (or restart after game over) once both hands pinch for DUAL_PINCH_HOLD_S."""
        # Only time the hold on screens that accept it; otherwise a pinch held
        # through the final LEVEL_FAILED would skip the game-over screen.
        if not both_pinching or self.state not in (GameState.START_SCREEN, GameState.GAME_OVER):
            self.dual_pinch_since = None
            return
        if self.dual_pinch_since is None:
            self.dual_pinch_since = now
        if now - self.dual_pinch_since >= DUAL_PINCH_HOLD_S:
            self.dual_pinch_since = None
            self.start(now)

    def dual_pinch_progress(self, now: float) -> float:
        """0..1 progress of the dual-pinch hold."""
        if self.dual_pinch_since is None:
            return 0.0
        return min(1.0, (now - self.dual_pinch_since) / DUAL_PINCH_HOLD_S)

    def update(self, now: float):
        elapsed = now - self.phase_start

        if self.state is GameState.READY:
            if elapsed >= READY_DURATION:
                self._enter(GameState.SHOWING_PATTERN, now)

        elif self.state is GameState.SHOWING_PATTERN:
            if elapsed >= self.step_duration:
                self.show_idx += 1
                self.phase_start = now
                if self.show_idx >= len(self.pattern):
                    self._enter(GameState.PLAYER_INPUT, now)

        elif self.state is GameState.LEVEL_SUCCESS:
            if elapsed >= SUCCESS_DURATION:
                self.level += 1
                self._extend_pattern()
                self._begin_round(now)

        elif self.state is GameState.LEVEL_FAILED:
            if elapsed >= FAIL_DURATION:
                if self.lives > 0:
                    self._begin_round(now)          # replay the same sequence
                else:
                    self._enter(GameState.GAME_OVER, now)

    def highlighted_tile(self, now: float) -> Optional[int]:
        """Tile currently lit while the pattern is being shown, if any."""
        if (self.state is GameState.SHOWING_PATTERN
                and self.show_idx < len(self.pattern)
                and now - self.phase_start < self.tile_show_duration):
            return self.pattern[self.show_idx]
        return None

    @property
    def first_mistake(self) -> Optional[int]:
        """Index into player_input of the first wrong pick, if any."""
        for i, (picked, expected) in enumerate(zip(self.player_input, self.pattern)):
            if picked != expected:
                return i
        return None

    # --- input -----------------------------------------------------------

    def pinch_started(self, tile: Optional[int], now: float):
        """Right-hand pinch begins: lock the tile under the cursor (may be None).

        Only arms during PLAYER_INPUT, so a pinch that began on the start
        screen or while the pattern was showing can't become an answer, and
        not during the cooldown, so a tile never lights up as armed and then
        silently fails to register on release.
        """
        accepting = self.state is GameState.PLAYER_INPUT and now >= self.cooldown_until
        self.armed_tile = tile if accepting else None

    def pinch_cancelled(self):
        """The hand was lost mid-pinch: drop the armed tile without committing."""
        self.armed_tile = None

    def pinch_ended(self, now: float):
        """Right-hand pinch ends: commit at most one selection (the armed tile)."""
        tile, self.armed_tile = self.armed_tile, None
        if self.state is not GameState.PLAYER_INPUT or tile is None:
            return
        self.player_input.append(tile)
        self.last_pick_at = now
        self.cooldown_until = now + PINCH_COOLDOWN_S

        if self.first_mistake is not None:
            self.lives -= 1
            self._enter(GameState.LEVEL_FAILED, now)
        elif len(self.player_input) == len(self.pattern):
            self.score = len(self.pattern)
            self.best = max(self.best, self.score)
            self._enter(GameState.LEVEL_SUCCESS, now)
