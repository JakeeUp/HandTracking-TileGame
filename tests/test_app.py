import numpy as np
import pytest

from memory_tiles.app import fit_frame


@pytest.mark.parametrize("src", [(720, 1280), (480, 640), (1080, 1080), (900, 1200)])
def test_fit_frame_outputs_window_size(src):
    frame = np.zeros((*src, 3), dtype=np.uint8)
    assert fit_frame(frame, 1200, 900).shape == (900, 1200, 3)


def test_fit_frame_crops_wide_frames_instead_of_stretching():
    # 16:9 frame with a marker column at each edge; a 4:3 crop must drop them.
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :10] = 255
    frame[:, -10:] = 255
    out = fit_frame(frame, 1200, 900)
    assert not out[:, :5].any() and not out[:, -5:].any()


@pytest.mark.parametrize("readings, expected", [
    ([-1.0, -1.0, -1.0], [False, False, False]),   # backend doesn't support the property
    ([1.0, 1.0, 0.0], [False, False, True]),       # shown, then closed with X
    ([0.0, 1.0, 0.0], [False, False, True]),       # not yet shown on the first check
])
def test_close_watcher(monkeypatch, readings, expected):
    import memory_tiles.app as app
    values = iter(readings)
    monkeypatch.setattr(app.cv2, "getWindowProperty", lambda *_: next(values))
    watcher = app.CloseWatcher("w")
    assert [watcher.closed() for _ in readings] == expected
