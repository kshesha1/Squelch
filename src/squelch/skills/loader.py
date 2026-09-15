"""Skill package ingestion (ticket P1.2).

Parses the Agent Skills package shape: a directory containing ``SKILL.md``
with YAML frontmatter (``name``, ``description``, optional extras) and any
referenced resource files. Produces a :class:`SkillSnapshot` whose identity
covers every file — editing a reference file changes package identity even
when SKILL.md is untouched.

Validation:
- reject symlinks and paths escaping the package root
- reject files larger than the declared limit
- unknown optional metadata is preserved as data, never as execution authority
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from squelch.hashing import hash_file, hash_json
from squelch.schemas import SkillSnapshot

DEFAULT_MAX_FILE_BYTES = 1_048_576  # 1 MiB per file
DEFAULT_MAX_TOTAL_BYTES = 8_388_608  # 8 MiB per package

KNOWN_METADATA_KEYS = {"name", "description", "license", "source_url"}


class SkillValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SkillPackage:
    snapshot: SkillSnapshot
    root: Path
    body: str  # SKILL.md content after frontmatter

    def read_resource(self, relative_path: str) -> str:
        """Read a resource file, re-validating the path boundary."""
        target = _resolve_inside(self.root, relative_path)
        rel = target.relative_to(self.root).as_posix()
        if rel not in self.snapshot.files:
            raise SkillValidationError(f"resource not in package snapshot: {relative_path}")
        return target.read_text(encoding="utf-8")


def _resolve_inside(root: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise SkillValidationError(f"absolute path not permitted: {relative_path}")
    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise SkillValidationError(f"path escapes package root: {relative_path}")
    return candidate


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillValidationError("SKILL.md must begin with YAML frontmatter (---)")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillValidationError("SKILL.md frontmatter is not terminated with ---")
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        raise SkillValidationError("SKILL.md frontmatter must be a YAML mapping")
    return meta, parts[2].lstrip("\n")


def load_skill_package(
    root: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> SkillPackage:
    root = Path(root)
    if not root.is_dir():
        raise SkillValidationError(f"skill package root is not a directory: {root}")
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        raise SkillValidationError(f"missing SKILL.md in {root}")

    files: dict[str, str] = {}
    total = 0
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            if p.is_symlink():
                raise SkillValidationError(f"symlinked directory not permitted: {p}")
            continue
        if p.is_symlink():
            raise SkillValidationError(f"symlink not permitted in skill package: {p}")
        rel = p.relative_to(root).as_posix()
        size = p.stat().st_size
        if size > max_file_bytes:
            raise SkillValidationError(f"file exceeds {max_file_bytes} bytes: {rel} ({size})")
        total += size
        if total > max_total_bytes:
            raise SkillValidationError(f"package exceeds {max_total_bytes} total bytes")
        files[rel] = hash_file(p)

    meta, body = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    name = meta.get("name")
    description = meta.get("description")
    if not isinstance(name, str) or not name.strip():
        raise SkillValidationError("frontmatter 'name' is required and must be a string")
    if not isinstance(description, str) or not description.strip():
        raise SkillValidationError("frontmatter 'description' is required and must be a string")

    extra = {k: v for k, v in meta.items() if k not in KNOWN_METADATA_KEYS}
    package_hash = hash_json({"files": files})

    snapshot = SkillSnapshot(
        skill_id=root.name,
        package_hash=package_hash,
        name=name.strip(),
        description=description.strip(),
        files=files,
        source_url=meta.get("source_url"),
        license=meta.get("license"),
        extra_metadata=extra,
    )
    return SkillPackage(snapshot=snapshot, root=root, body=body)


def load_inventory(skills_dir: Path) -> dict[str, SkillPackage]:
    """Load every skill package under a directory, keyed by skill_id."""
    inventory: dict[str, SkillPackage] = {}
    for child in sorted(Path(skills_dir).iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            pkg = load_skill_package(child)
            inventory[pkg.snapshot.skill_id] = pkg
    return inventory
