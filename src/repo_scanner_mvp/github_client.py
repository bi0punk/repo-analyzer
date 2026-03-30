from __future__ import annotations

from typing import Any

import requests

from repo_scanner_mvp.config import GitHubConfig


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, config: GitHubConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {config.token}",
                "X-GitHub-Api-Version": config.api_version,
                "User-Agent": "repo-scanner-mvp/0.1.0",
            }
        )

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = f"{self.config.api_base_url}{path}"
        response = self.session.request(method=method, url=url, params=params, timeout=60)
        if response.status_code >= 400:
            raise GitHubApiError(
                f"GitHub API error {response.status_code} for {path}: {response.text[:400]}"
            )
        return response

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            query = dict(params or {})
            query.setdefault("per_page", self.config.per_page)
            query["page"] = page
            response = self._request("GET", path, params=query)
            page_items = response.json()
            if not isinstance(page_items, list):
                raise GitHubApiError(f"Expected list response for {path}")
            items.extend(page_items)
            if len(page_items) < query["per_page"]:
                break
            if self.config.max_repos and len(items) >= self.config.max_repos:
                return items[: self.config.max_repos]
            page += 1
        if self.config.max_repos:
            return items[: self.config.max_repos]
        return items

    def list_repositories(self) -> list[dict[str, Any]]:
        if self.config.scan_mode == "authenticated":
            return self._paginate("/user/repos", params={"sort": "updated", "affiliation": "owner,collaborator,organization_member"})
        if self.config.scan_mode == "org":
            return self._paginate(f"/orgs/{self.config.owner}/repos", params={"type": "all", "sort": "updated"})
        return self._paginate(f"/users/{self.config.owner}/repos", params={"sort": "updated"})

    def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        return self._paginate(f"/repos/{owner}/{repo}/branches")

    def get_branch_protection(self, owner: str, repo: str, branch: str) -> dict[str, Any] | None:
        url = f"{self.config.api_base_url}/repos/{owner}/{repo}/branches/{branch}/protection"
        response = self.session.get(url, timeout=60)
        if response.status_code == 404:
            return None
        if response.status_code == 403:
            return {"_error": "forbidden"}
        if response.status_code >= 400:
            return {"_error": f"http_{response.status_code}", "_body": response.text[:200]}
        return response.json()
