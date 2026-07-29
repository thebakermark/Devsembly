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
