from __future__ import annotations

from devsembly.provider_command import CommandCodingProvider


def test_provider_environment_excludes_source_control_token(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("DEVSEMBLY_SOURCE_CONTROL_TOKEN", "source-control-secret")
    monkeypatch.setenv("UNRELATED_SECRET", "unrelated-secret")

    environment = CommandCodingProvider._provider_environment()

    assert environment["ANTHROPIC_API_KEY"] == "anthropic-secret"
    assert "DEVSEMBLY_SOURCE_CONTROL_TOKEN" not in environment
    assert "UNRELATED_SECRET" not in environment
