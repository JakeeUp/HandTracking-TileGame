import numpy as np

from memory_tiles import text


def test_bundled_fonts_load():
    for weight, name in text.WEIGHTS.items():
        assert (text.FONT_DIR / name).exists()
        assert "Poppins" in text.font(20, weight).getname()[0]


def test_draw_text_anchors_and_clips():
    f = np.zeros((100, 300, 3), np.uint8)
    text.draw_text(f, "Hello", (150, 50), 30, (255, 255, 255), anchor="mm")
    ys, xs = np.nonzero(f[..., 0] > 128)
    w, h = text.text_size("Hello", 30)
    assert abs((xs.min() + xs.max()) / 2 - 150) <= 3
    assert abs(xs.max() - xs.min() - w) <= 6          # anti-aliased edges fall under the threshold
    text.draw_text(f, "Clipped", (-50, -20), 40, (255, 255, 255))     # off the edge: no error


def test_empty_string_is_noop():
    f = np.zeros((10, 10, 3), np.uint8)
    text.draw_text(f, "", (5, 5), 12, (255, 255, 255))
    assert not f.any()
