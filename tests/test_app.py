import numpy as np
import pytest

from memory_tiles.cameras import fit_frame


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


class FakeLauncher:
    """Stands in for the tkinter picker; returns queued choices in order."""
    choices = []
    errors = []
    mirrors = []

    def __init__(self, saved_camera, error, mirror):
        FakeLauncher.errors.append(error)
        FakeLauncher.mirrors.append(mirror)

    def run(self):
        return FakeLauncher.choices.pop(0)


@pytest.fixture
def flow(monkeypatch, tmp_path):
    import memory_tiles.app as app
    import memory_tiles.launcher as launcher
    from memory_tiles import settings
    path = tmp_path / "settings.json"
    monkeypatch.setattr(app, "load", lambda: settings.load(path))
    monkeypatch.setattr(app, "save", lambda **kw: settings.save(path, **kw))
    monkeypatch.setattr(launcher, "Launcher", FakeLauncher)
    FakeLauncher.choices, FakeLauncher.errors, FakeLauncher.mirrors = [], [], []
    played = []

    def set_outcomes(*outcomes):
        queue = list(outcomes)
        def fake_play(index, mirror, record=None):
            played.append((index, mirror))
            return queue.pop(0)
        monkeypatch.setattr(app, "play", fake_play)
    return app, set_outcomes, played, path


def test_closing_the_picker_exits(flow):
    app, set_outcomes, played, _ = flow
    FakeLauncher.choices = [None]
    assert app.main([]) == 0 and played == []


def test_camera_failure_returns_to_picker_with_error(flow):
    from memory_tiles.cameras import CameraInfo
    app, set_outcomes, played, path = flow
    FakeLauncher.choices = [(CameraInfo(0, "Black Cam"), True),
                            (CameraInfo(4, "OBS Virtual Camera"), False)]
    set_outcomes(None, app.Outcome.QUIT)            # first camera won't open
    assert app.main([]) == 0
    assert played == [(0, True), (4, False)]
    assert FakeLauncher.errors == [None, app.NO_CAMERA]
    saved = path.read_text()
    assert '"camera": "OBS Virtual Camera"' in saved and '"mirror": false' in saved


def test_c_key_reopens_picker_without_error(flow):
    from memory_tiles.cameras import CameraInfo
    app, set_outcomes, played, _ = flow
    FakeLauncher.choices = [(CameraInfo(1, "A"), True), None]
    set_outcomes(app.Outcome.SETTINGS)
    assert app.main([]) == 0
    assert FakeLauncher.errors == [None, None]


def test_camera_flag_skips_picker(flow, monkeypatch):
    app, set_outcomes, played, _ = flow
    set_outcomes(app.Outcome.QUIT)
    assert app.main(["--camera", "4"]) == 0
    assert played == [(4, True)] and FakeLauncher.errors == []


def test_mirror_setting_is_remembered(flow):
    from memory_tiles.cameras import CameraInfo
    app, set_outcomes, played, _ = flow
    FakeLauncher.choices = [(CameraInfo(4, "OBS"), False), None]
    set_outcomes(app.Outcome.SETTINGS)
    app.main([])
    assert FakeLauncher.mirrors == [True, False]   # default on, then the saved choice
