import pytest

from memory_tiles.geometry import Layout, dist

LAYOUT = Layout.centered(1200, 900, grid=4, tile=100, spacing=20)


def test_dist():
    assert dist((0, 0), (3, 4)) == 5


def test_centered_grid_has_symmetric_horizontal_margins():
    assert LAYOUT.span == 4 * 100 + 3 * 20
    assert LAYOUT.origin_x == 1200 - (LAYOUT.origin_x + LAYOUT.span)


def test_centered_grid_is_offset_down():
    assert LAYOUT.origin_y == (900 - LAYOUT.span) // 2 + 60


@pytest.mark.parametrize("i", range(16))
def test_tile_at_roundtrips_tile_xy(i):
    x, y = LAYOUT.tile_xy(i)
    assert LAYOUT.tile_at(x, y) == i                      # top-left corner
    assert LAYOUT.tile_at(x + 100, y + 100) == i          # bottom-right, inclusive
    assert LAYOUT.tile_at(x + 50, y + 50) == i


def test_tile_at_misses_gaps_and_outside():
    x, y = LAYOUT.tile_xy(0)
    assert LAYOUT.tile_at(x + 110, y + 50) is None        # in the spacing gap
    assert LAYOUT.tile_at(x - 1, y) is None
    assert LAYOUT.tile_at(x + LAYOUT.span + 1, y) is None
    assert LAYOUT.tile_at(x, y + LAYOUT.span + 1) is None
