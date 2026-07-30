from pathlib import Path

import pytest

from devsembly.workspace import enforce_allowed_paths, validate_repository_url


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


def test_path_examples_are_relative() -> None:
    assert not Path("src/app.py").is_absolute()
