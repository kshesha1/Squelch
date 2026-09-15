"""Canonical hashing for Squelch artifacts.

Two regimes, per the spec (§4):

- Structured records hash as canonical UTF-8 JSON: sorted keys, no
  non-finite floats, compact separators.
- Source files hash as exact bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

SHA256_PREFIX = "sha256:"


def _reject_non_finite(obj: Any) -> Any:
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"non-finite float {obj!r} is not permitted in canonical JSON")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(f"non-string key {k!r} is not permitted in canonical JSON")
            _reject_non_finite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _reject_non_finite(v)
    return obj


def canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON: sorted keys, compact, finite floats only."""
    _reject_non_finite(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_json(obj: Any) -> str:
    """SHA-256 of the canonical JSON serialization, with sha256: prefix."""
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return SHA256_PREFIX + digest


def hash_bytes(data: bytes) -> str:
    return SHA256_PREFIX + hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: Path) -> str:
    """SHA-256 of a file's exact bytes."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return SHA256_PREFIX + h.hexdigest()


def hash_tree(root: Path, *, relative_paths: list[str] | None = None) -> str:
    """Hash a directory tree: mapping of relative POSIX path -> file hash.

    Symlinks are refused: tree identity must not depend on content outside
    the tree root.
    """
    root = root.resolve()
    if relative_paths is None:
        files = sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() or p.is_symlink()
        )
    else:
        files = sorted(relative_paths)
    mapping: dict[str, str] = {}
    for rel in files:
        p = root / rel
        if p.is_symlink():
            raise ValueError(f"symlink not permitted in hashed tree: {rel}")
        mapping[rel] = hash_file(p)
    return hash_json(mapping)
