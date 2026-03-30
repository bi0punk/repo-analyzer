from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class BranchProtectionSummary:
    enabled: bool = False
    required_pull_request_reviews: bool = False
    required_status_checks: bool = False
    enforce_admins: bool = False
    allows_force_pushes: bool = False
    allows_deletions: bool = False
    requires_linear_history: bool = False
    contexts: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BranchSummary:
    name: str
    protected: bool
    last_sha: str | None = None
    protection: BranchProtectionSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "protected": self.protected,
            "last_sha": self.last_sha,
            "protection": self.protection.to_dict() if self.protection else None,
        }


@dataclass(slots=True)
class RepoScanResult:
    full_name: str
    name: str
    owner: str
    private: bool
    archived: bool
    disabled: bool
    fork: bool
    language: str | None
    description: str | None
    default_branch: str | None
    branches: list[BranchSummary]
    has_main: bool
    has_master: bool
    has_dev: bool
    has_develop: bool
    protected_main: bool
    protected_default_branch: bool
    primary_candidate_branch: str | None
    repo_status: str
    risk_level: str
    recommended_actions: list[str]
    html_url: str
    updated_at: str | None
    pushed_at: str | None
    scan_errors: list[str] = field(default_factory=list)
    llm_summary: str | None = None
    llm_policy_classification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "name": self.name,
            "owner": self.owner,
            "private": self.private,
            "archived": self.archived,
            "disabled": self.disabled,
            "fork": self.fork,
            "language": self.language,
            "description": self.description,
            "default_branch": self.default_branch,
            "branches": [branch.to_dict() for branch in self.branches],
            "has_main": self.has_main,
            "has_master": self.has_master,
            "has_dev": self.has_dev,
            "has_develop": self.has_develop,
            "protected_main": self.protected_main,
            "protected_default_branch": self.protected_default_branch,
            "primary_candidate_branch": self.primary_candidate_branch,
            "repo_status": self.repo_status,
            "risk_level": self.risk_level,
            "recommended_actions": self.recommended_actions,
            "html_url": self.html_url,
            "updated_at": self.updated_at,
            "pushed_at": self.pushed_at,
            "scan_errors": self.scan_errors,
            "llm_summary": self.llm_summary,
            "llm_policy_classification": self.llm_policy_classification,
        }


@dataclass(slots=True)
class ScanSummary:
    timestamp: str
    scan_mode: str
    owner: str | None
    total_repos: int
    total_archived: int
    total_with_dev: int
    total_with_main: int
    total_with_protected_main: int
    repo_status_counts: dict[str, int]
    risk_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
