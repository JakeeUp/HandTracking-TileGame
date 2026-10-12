import json

from memory_tiles.settings import load, load_best, save, save_best


def test_best_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    save_best(12, path)
    assert load_best(path) == 12


def test_missing_or_corrupt_file_is_empty(tmp_path):
    path = tmp_path / "settings.json"
    assert load(path) == {} and load_best(path) == 0
    path.write_text("not json")
    assert load(path) == {} and load_best(path) == 0
    path.write_text("[1, 2]")
    assert load(path) == {}
    path.write_text('{"best": "x"}')
    assert load_best(path) == 0


def test_save_merges_keys(tmp_path):
    path = tmp_path / "settings.json"
    save_best(5, path)
    save(path, camera="Cam Link 4K")
    assert json.loads(path.read_text()) == {"best": 5, "camera": "Cam Link 4K"}


def test_reads_old_best_only_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"best": 7}')
    assert load_best(path) == 7


def test_save_to_unwritable_path_does_not_raise(tmp_path):
    save_best(3, tmp_path / "missing-dir" / "settings.json")
