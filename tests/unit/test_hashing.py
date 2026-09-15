import math

import pytest

from squelch.hashing import canonical_json, hash_file, hash_json, hash_tree


def test_canonical_json_sorts_keys():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_json_rejects_non_finite():
    with pytest.raises(ValueError):
        canonical_json({"x": math.nan})
    with pytest.raises(ValueError):
        canonical_json([math.inf])


def test_canonical_json_rejects_non_string_keys():
    with pytest.raises(ValueError):
        canonical_json({1: "a"})


def test_hash_json_stable_under_key_order():
    assert hash_json({"a": 1, "b": [1, 2]}) == hash_json({"b": [1, 2], "a": 1})


def test_hash_file_exact_bytes(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"hello")
    h1 = hash_file(f)
    f.write_bytes(b"hello ")
    assert hash_file(f) != h1


def test_hash_tree_changes_with_any_file(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    h1 = hash_tree(tmp_path)
    (tmp_path / "sub" / "b.txt").write_text("changed")
    assert hash_tree(tmp_path) != h1


def test_hash_tree_rejects_symlink(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "link").symlink_to(tmp_path / "a.txt")
    with pytest.raises(ValueError, match="symlink"):
        hash_tree(tmp_path)
