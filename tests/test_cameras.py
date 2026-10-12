import pytest

from memory_tiles import cameras
from memory_tiles.cameras import CameraInfo, pick_default


def test_camera_label():
    assert str(CameraInfo(4, "OBS Virtual Camera")) == "4: OBS Virtual Camera"


def test_pick_default_matches_saved_name():
    cams = [CameraInfo(0, "Elgato HD60 X"), CameraInfo(1, "Cam Link 4K")]
    assert pick_default(cams, "Cam Link 4K") == 1
    assert pick_default(cams, "Unplugged Cam") == 0
    assert pick_default(cams, None) == 0


def test_v4l2_lists_capture_nodes_only(tmp_path):
    def node(n, name, index):
        d = tmp_path / f"video{n}"
        d.mkdir()
        (d / "name").write_text(name + "\n")
        (d / "index").write_text(f"{index}\n")
    node(2, "USB Cam", 0)
    node(3, "USB Cam", 1)          # metadata node of the same camera
    node(0, "Laptop Cam", 0)
    (tmp_path / "vbi0").mkdir()
    assert cameras._v4l2_cameras(tmp_path) == [CameraInfo(0, "Laptop Cam"),
                                               CameraInfo(2, "USB Cam")]


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_falls_back_to_probing(monkeypatch, platform):
    monkeypatch.setattr(cameras.sys, "platform", platform)
    monkeypatch.setattr(cameras, "_dshow_names", lambda: None)
    monkeypatch.setattr(cameras, "_probe", lambda: [CameraInfo(0, "Camera 0")])
    assert cameras.list_cameras() == [CameraInfo(0, "Camera 0")]


def test_windows_uses_directshow_names(monkeypatch):
    monkeypatch.setattr(cameras.sys, "platform", "win32")
    monkeypatch.setattr(cameras, "_dshow_names", lambda: ["A", "B"])
    assert cameras.list_cameras() == [CameraInfo(0, "A"), CameraInfo(1, "B")]
