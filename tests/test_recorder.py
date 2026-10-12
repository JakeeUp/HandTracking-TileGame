import cv2
import numpy as np
from PIL import Image

from memory_tiles.gif import main as gif_main
from memory_tiles.gif import mp4_to_gif, stabilize
from memory_tiles.recorder import Recorder, default_path


def frame(value, size=(160, 120)):
    return np.full((size[1], size[0], 3), value, np.uint8)


def frame_count(path):
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return n


def test_records_at_real_time_speed(tmp_path):
    path = tmp_path / "sub" / "clip.mp4"            # parent dirs are created
    rec = Recorder(fps=30)
    assert rec.start(path, (160, 120), now=10.0)
    rec.write(frame(0), 10.0)
    rec.write(frame(100), 11.0)                      # a slow 1 s frame is repeated
    assert rec.elapsed(11.0) == 1.0
    assert rec.stop() == path and not rec.active
    assert frame_count(path) == 31


def test_inactive_recorder_is_a_noop(tmp_path):
    rec = Recorder()
    rec.write(frame(0), 0.0)
    assert rec.stop() is None and rec.elapsed(5.0) == 0.0


def test_default_path_is_timestamped_mp4():
    p = default_path()
    assert p.suffix == ".mp4" and p.parent.name == "MemoryTiles"


def make_clip(path, seconds=2, fps=30):
    rec = Recorder(fps=fps)
    rec.start(path, (320, 240), 0.0)
    for k in range(seconds * fps):
        f = frame(0, (320, 240))
        cv2.circle(f, (40 + k * 4, 120), 20, (0, 200, 255), -1)
        rec.write(f, k / fps)
    rec.stop()


def test_mp4_to_gif_trims_resamples_and_resizes(tmp_path):
    src, dst = tmp_path / "clip.mp4", tmp_path / "clip.gif"
    make_clip(src)
    n = mp4_to_gif(str(src), str(dst), start=0.5, end=1.5, width=160, fps=10)
    assert 10 <= n <= 11
    with Image.open(dst) as im:
        assert im.size == (160, 120)
        assert im.n_frames == n


def test_gif_cli_reports_errors(tmp_path, capsys):
    assert gif_main([str(tmp_path / "missing.mp4"), str(tmp_path / "x.gif")]) == 1
    assert "error" in capsys.readouterr().err


def test_stabilize_holds_small_changes_only():
    base = np.full((4, 4, 3), 100, np.uint8)
    noisy, moved = base.copy(), base.copy()
    noisy[0, 0] = 105                      # sensor noise: held
    moved[1, 1] = 200                      # real change: kept
    out = [np.asarray(im) for im in stabilize(
        [Image.fromarray(base), Image.fromarray(noisy), Image.fromarray(moved)], 12)]
    assert out[1][0, 0, 0] == 100
    assert out[2][1, 1, 0] == 200 and out[2][0, 0, 0] == 100
    assert stabilize([Image.fromarray(noisy)], 0)[0] is not None
