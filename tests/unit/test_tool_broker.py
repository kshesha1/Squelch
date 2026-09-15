import pytest

from squelch.runner.tools import ToolBroker, ToolError
from squelch.sandbox.envs import LocalEnv
from squelch.schemas import CheckSpec, ResourceLimits


@pytest.fixture
def broker(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "hello.txt").write_text("hi")
    checks = [
        CheckSpec(check_id="echo", cmd=["python", "-c", "print('ran')"], public=True),
        CheckSpec(check_id="hidden", cmd=["python", "-c", "print('no')"], public=False),
    ]
    return ToolBroker(ws, env=LocalEnv(), checks=checks, limits=ResourceLimits())


def test_read_and_write(broker):
    assert broker.read_file("hello.txt") == "hi"
    broker.write_file("sub/new.txt", "content")
    assert broker.read_file("sub/new.txt") == "content"


def test_list_files(broker):
    assert "hello.txt" in broker.list_files()


@pytest.mark.parametrize("bad", ["/etc/passwd", "../escape.txt", "a/../../escape", "..", ""])
def test_path_escapes_rejected(broker, bad):
    with pytest.raises(ToolError):
        broker.read_file(bad)
    with pytest.raises(ToolError):
        broker.write_file(bad, "x")


def test_symlink_traversal_rejected(broker, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    (broker.workspace / "link").symlink_to(outside)
    with pytest.raises(ToolError, match="symlink"):
        broker.read_file("link/secret.txt")
    with pytest.raises(ToolError, match="symlink"):
        broker.write_file("link/evil.txt", "x")


def test_write_size_limit(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    broker = ToolBroker(ws, env=LocalEnv(), checks=[],
                        limits=ResourceLimits(max_file_bytes=10))
    with pytest.raises(ToolError, match="exceeds"):
        broker.write_file("f.txt", "x" * 11)


def test_run_checks_allowlist(broker):
    out = broker.run_checks("echo")
    assert "ran" in out and "exit=0" in out
    with pytest.raises(ToolError, match="unknown or non-public"):
        broker.run_checks("hidden")  # non-public checks are not agent-callable
    with pytest.raises(ToolError, match="unknown or non-public"):
        broker.run_checks("rm -rf /")  # never an arbitrary command


def test_dispatch_unknown_tool(broker):
    with pytest.raises(ToolError, match="unknown tool"):
        broker.dispatch("shell", {"cmd": "ls"})
