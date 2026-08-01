from pathlib import Path

import pytest

from devsembly.workspace import changed_paths, enforce_allowed_paths, validate_repository_url


def test_repository_url_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        validate_repository_url("ssh://git@example.com/repository.git")


def test_repository_url_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="Credentials"):
        validate_repository_url("https://token@example.com/repository.git")


def test_allowed_paths_accept_bounded_changes() -> None:
    enforce_allowed_paths(["src/app.py", "tests/test_app.py"], ["src/", "tests/"])


def test_allowed_paths_rejects_escape() -> None:
    with pytest.raises(PermissionError, match="outside"):
        enforce_allowed_paths(["src/app.py", ".github/workflows/release.yml"], ["src/"])


def test_allowed_paths_rejects_sibling_prefix_bypass() -> None:
    with pytest.raises(PermissionError, match="outside"):
        enforce_allowed_paths(["src-private/leak.txt"], ["src"])


@pytest.mark.asyncio
async def test_changed_paths_parses_spaces_and_renames(tmp_path: Path) -> None:
    import asyncio

    async def git(*args: str) -> None:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        assert process.returncode == 0, stderr.decode()

    await git("init")
    await git("config", "user.name", "Test")
    await git("config", "user.email", "test@example.com")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "old name.py").write_text("old\n")
    await git("add", ".")
    await git("commit", "-m", "fixture")
    (tmp_path / "src" / "old name.py").rename(tmp_path / "src" / "new name.py")
    await git("add", "-A")

    assert await changed_paths(tmp_path) == ["src/new name.py"]


def test_path_examples_are_relative() -> None:
    assert not Path("src/app.py").is_absolute()
