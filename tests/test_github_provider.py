from __future__ import annotations

import httpx
import pytest

from devsembly.github_provider import (
    GitHubProviderError,
    GitHubProviderRateLimited,
    GitHubProviderUnavailable,
    GitHubSnapshotClient,
    _next_link,
)


def test_next_link_selects_only_next_relation() -> None:
    value = (
        '<https://api.github.com/page/1>; rel="prev", <https://api.github.com/page/3>; rel="next"'
    )
    assert _next_link(value) == "https://api.github.com/page/3"
    assert _next_link(None) is None


async def test_client_authenticates_and_follows_provider_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    async def get(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        del client
        seen.update(url=url, headers=kwargs["headers"])
        return httpx.Response(
            200,
            json=[{"node_id": "I_1"}],
            headers={"link": '<https://api.github.com/repos/o/r/issues?page=2>; rel="next"'},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    page = await GitHubSnapshotClient("token-value").page("o/r", "issue")
    assert page.entities == [{"node_id": "I_1"}]
    assert page.next_url is not None and page.next_url.endswith("page=2")
    assert seen["url"] == "https://api.github.com/repos/o/r/issues?state=all&per_page=100"
    assert isinstance(seen["headers"], dict)
    assert seen["headers"]["Authorization"] == "Bearer token-value"


async def test_client_normalizes_rate_limit_and_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            httpx.Response(
                403,
                headers={"x-ratelimit-remaining": "0"},
                request=httpx.Request("GET", "https://api.github.com/x"),
            ),
            httpx.Response(503, request=httpx.Request("GET", "https://api.github.com/x")),
        ]
    )

    async def get(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        del client, url, kwargs
        return next(responses)

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    client = GitHubSnapshotClient("token-value")
    with pytest.raises(GitHubProviderRateLimited):
        await client.page("o/r", "issue")
    with pytest.raises(GitHubProviderUnavailable):
        await client.page("o/r", "issue")


async def test_client_rejects_cross_origin_pagination() -> None:
    client = GitHubSnapshotClient("token-value")
    with pytest.raises(GitHubProviderError, match="changed origin"):
        await client.page("o/r", "issue", "https://evil.example/page")
