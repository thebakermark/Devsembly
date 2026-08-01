import pytest
from pydantic import ValidationError

from devsembly.contracts import ProductRequest


def test_product_request_defaults() -> None:
    request = ProductRequest(
        title="Build a sample service",
        objective="Create a small tested API service for a fixture repository.",
        repository_url="https://github.com/thebakermark/Devsembly",
    )
    assert request.base_branch == "main"
    assert request.max_repair_attempts == 2
    assert "pytest -q" in request.validation_commands


@pytest.mark.parametrize("path", ["../secrets", "/etc/passwd", ""])
def test_product_request_rejects_unsafe_allowed_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        ProductRequest(
            title="Build a sample service",
            objective="Create a small tested API service for a fixture repository.",
            repository_url="https://github.com/example/fixture",
            allowed_paths=[path],
        )
