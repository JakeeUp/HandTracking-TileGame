from memory_tiles.scores import load_best, save_best


def test_roundtrip(tmp_path):
    path = tmp_path / "scores.json"
    save_best(12, path)
    assert load_best(path) == 12


def test_missing_or_corrupt_file_is_zero(tmp_path):
    path = tmp_path / "scores.json"
    assert load_best(path) == 0
    path.write_text("not json")
    assert load_best(path) == 0
    path.write_text('{"best": "x"}')
    assert load_best(path) == 0


def test_save_to_unwritable_path_does_not_raise(tmp_path):
    save_best(3, tmp_path / "missing-dir" / "scores.json")
