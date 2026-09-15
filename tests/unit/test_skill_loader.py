import pytest

from squelch.skills.loader import SkillValidationError, load_skill_package


def make_skill(root, name="demo-skill", body="Do good work.", extra_files=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A demo skill.\ncustom_key: preserved\n---\n{body}\n"
    )
    for rel, content in (extra_files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


def test_parses_metadata_and_body(tmp_path):
    pkg = load_skill_package(make_skill(tmp_path / "demo-skill"))
    assert pkg.snapshot.name == "demo-skill"
    assert pkg.snapshot.description == "A demo skill."
    assert pkg.body.strip() == "Do good work."
    assert "SKILL.md" in pkg.snapshot.files
    # Unknown metadata preserved as data, never as execution authority.
    assert pkg.snapshot.extra_metadata == {"custom_key": "preserved"}


def test_reference_file_edit_changes_package_identity(tmp_path):
    root = make_skill(tmp_path / "s", extra_files={"refs/notes.md": "v1"})
    h1 = load_skill_package(root).snapshot.package_hash
    (root / "refs/notes.md").write_text("v2")
    h2 = load_skill_package(root).snapshot.package_hash
    assert h1 != h2


def test_rejects_symlink(tmp_path):
    root = make_skill(tmp_path / "s")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (root / "leak.txt").symlink_to(outside)
    with pytest.raises(SkillValidationError, match="symlink"):
        load_skill_package(root)


def test_rejects_oversized_file(tmp_path):
    root = make_skill(tmp_path / "s", extra_files={"big.txt": "x" * 100})
    with pytest.raises(SkillValidationError, match="exceeds"):
        load_skill_package(root, max_file_bytes=50)


def test_rejects_missing_frontmatter(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "SKILL.md").write_text("no frontmatter here")
    with pytest.raises(SkillValidationError, match="frontmatter"):
        load_skill_package(root)


def test_rejects_missing_name(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "SKILL.md").write_text("---\ndescription: d\n---\nbody")
    with pytest.raises(SkillValidationError, match="name"):
        load_skill_package(root)


def test_read_resource_stays_inside_package(tmp_path):
    root = make_skill(tmp_path / "s", extra_files={"refs/a.md": "ok"})
    pkg = load_skill_package(root)
    assert pkg.read_resource("refs/a.md") == "ok"
    with pytest.raises(SkillValidationError):
        pkg.read_resource("../outside.txt")
    with pytest.raises(SkillValidationError):
        pkg.read_resource("/etc/passwd")
