from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from temporalio import activity

from devsembly.github_sync import GitHubSynchronizationService, normalize_snapshot_entity


class GitHubProviderError(RuntimeError):
    pass


class GitHubProviderUnavailable(GitHubProviderError):
    pass


class GitHubProviderRateLimited(GitHubProviderError):
    pass


@dataclass(frozen=True, slots=True)
class GitHubPage:
    entities: list[dict[str, object]]
    next_url: str | None


def _next_link(value: str | None) -> str | None:
    if value is None:
        return None
    for part in value.split(","):
        section = part.strip().split(";")
        if len(section) >= 2 and any(item.strip() == 'rel="next"' for item in section[1:]):
            return section[0].strip().removeprefix("<").removesuffix(">")
    return None


class GitHubSnapshotClient:
    def __init__(self, token: str, *, api_url: str = "https://api.github.com") -> None:
        if not token:
            raise GitHubProviderError("GitHub provider token is not configured")
        self._token = token
        self._api_url = api_url.rstrip("/")

    async def page(self, repository: str, kind: str, next_url: str | None = None) -> GitHubPage:
        paths = {
            "issue": "issues?state=all&per_page=100",
            "pull_request": "pulls?state=all&per_page=100",
            "milestone": "milestones?state=all&per_page=100",
            "branch": "branches?per_page=100",
            "commit": "commits?per_page=100",
            "workflow_run": "actions/runs?per_page=100",
        }
        if kind not in paths:
            raise GitHubProviderError(f"unsupported GitHub snapshot kind: {kind}")
        url = next_url or f"{self._api_url}/repos/{repository}/{paths[kind]}"
        if not url.startswith(f"{self._api_url}/"):
            raise GitHubProviderError("GitHub pagination URL changed origin")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise GitHubProviderUnavailable("GitHub request failed") from exc
        if (
            response.status_code in {429, 403}
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubProviderRateLimited("GitHub rate limit exhausted")
        if response.status_code >= 500:
            raise GitHubProviderUnavailable("GitHub is unavailable")
        if response.status_code in {401, 403, 404}:
            raise GitHubProviderError(f"GitHub request rejected with status {response.status_code}")
        response.raise_for_status()
        payload: Any = response.json()
        if kind == "workflow_run" and isinstance(payload, dict):
            payload = payload.get("workflow_runs")
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise GitHubProviderError("GitHub snapshot page has an invalid shape")
        if kind == "issue":
            payload = [item for item in payload if "pull_request" not in item]
        return GitHubPage(entities=payload, next_url=_next_link(response.headers.get("link")))


@activity.defn
async def reconcile_github_page(request: dict[str, object]) -> dict[str, object]:
    client = GitHubSnapshotClient(
        os.getenv("DEVSEMBLY_GITHUB_TOKEN", ""),
        api_url=os.getenv("DEVSEMBLY_GITHUB_API_URL", "https://api.github.com"),
    )
    repository_id = str(request["repository_id"])
    kind = str(request["kind"])
    raw_next_url = request.get("next_url")
    page = await client.page(
        str(request["repository"]), kind, None if raw_next_url is None else str(raw_next_url)
    )
    events = [normalize_snapshot_entity(repository_id, kind, item) for item in page.entities]
    result = await GitHubSynchronizationService().reconcile_snapshot(
        uuid.UUID(str(request["project_id"])), repository_id, events
    )
    return {
        "processed": result.processed,
        "duplicates": result.duplicates,
        "conflicts": result.conflicts,
        "out_of_order": result.out_of_order,
        "next_url": page.next_url,
    }
