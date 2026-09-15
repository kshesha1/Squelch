"""Container boundary tests. These require a Docker daemon and are marked
`docker`; when Docker is absent they are SKIPPED — absence of Docker must
never masquerade as a passed sandbox test (spec §12).
"""

import pytest

from squelch.sandbox.envs import DockerEnv

pytestmark = pytest.mark.docker

IMAGE = "python:3.12-slim"

docker_required = pytest.mark.skipif(
    not DockerEnv.available(), reason="Docker daemon not available"
)


@docker_required
def test_runs_python_in_container(tmp_path):
    env = DockerEnv(IMAGE)
    result = env.run(["python", "-c", "print('hello from container')"],
                     workspace=tmp_path, timeout_seconds=60)
    assert result.ok, result.stderr
    assert "hello from container" in result.stdout


@docker_required
def test_network_is_disabled(tmp_path):
    env = DockerEnv(IMAGE)
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 80), timeout=3)\n"
        "    print('CONNECTED')\n"
        "except OSError:\n"
        "    print('NO_NETWORK')\n"
    )
    result = env.run(["python", "-c", code], workspace=tmp_path, timeout_seconds=60)
    assert "NO_NETWORK" in result.stdout


@docker_required
def test_root_filesystem_is_read_only(tmp_path):
    env = DockerEnv(IMAGE)
    code = (
        "try:\n"
        "    open('/etc/marker', 'w').write('x')\n"
        "    print('WROTE')\n"
        "except OSError:\n"
        "    print('READ_ONLY')\n"
    )
    result = env.run(["python", "-c", code], workspace=tmp_path, timeout_seconds=60)
    assert "READ_ONLY" in result.stdout


@docker_required
def test_readonly_workspace_mount(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    env = DockerEnv(IMAGE)
    code = (
        "try:\n"
        "    open('/workspace/g.txt', 'w').write('x')\n"
        "    print('WROTE')\n"
        "except OSError:\n"
        "    print('DENIED')\n"
    )
    result = env.run(["python", "-c", code], workspace=tmp_path,
                     timeout_seconds=60, readonly=True)
    assert "DENIED" in result.stdout
