"""Grid layout math: tile positions and hit-testing."""
import math
from dataclasses import dataclass
from typing import Optional, Tuple


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class Layout:
    """Pixel geometry of the window and the square tile grid."""
    win_w: int
    win_h: int
    grid: int
    tile: int
    spacing: int
    origin_x: int
    origin_y: int

    @classmethod
    def centered(cls, win_w, win_h, grid, tile, spacing, y_offset=60):
        """Center the grid horizontally, and vertically shifted down by y_offset."""
        span = grid * tile + (grid - 1) * spacing
        return cls(win_w, win_h, grid, tile, spacing,
                   (win_w - span) // 2, (win_h - span) // 2 + y_offset)

    @property
    def tile_count(self) -> int:
        return self.grid * self.grid

    @property
    def span(self) -> int:
        """Width (and height) of the whole grid in pixels."""
        return self.grid * self.tile + (self.grid - 1) * self.spacing

    def tile_xy(self, index: int) -> Tuple[int, int]:
        """Top-left pixel of tile `index` (row-major)."""
        r, c = divmod(index, self.grid)
        pitch = self.tile + self.spacing
        return self.origin_x + c * pitch, self.origin_y + r * pitch

    def tile_at(self, px, py) -> Optional[int]:
        """Index of the tile containing (px, py), edges inclusive, or None."""
        pitch = self.tile + self.spacing
        dx, dy = px - self.origin_x, py - self.origin_y
        if dx < 0 or dy < 0:
            return None
        c, off_x = divmod(dx, pitch)
        r, off_y = divmod(dy, pitch)
        if c >= self.grid or r >= self.grid or off_x > self.tile or off_y > self.tile:
            return None
        return int(r * self.grid + c)
