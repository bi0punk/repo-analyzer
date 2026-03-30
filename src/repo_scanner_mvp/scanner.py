from __future__ import annotations

from collections import Counter
from typing import Any

from repo_scanner_mvp.config import AppConfig
from repo_scanner_mvp.github_client import GitHubClient, GitHubApiError
from repo_scanner_mvp.llm_client import LLMClient
from repo_scanner_mvp.models import BranchProtectionSummary, BranchSummary, RepoScanResult, ScanSummary
from repo_scanner_mvp.rules import choose_primary_candidate_branch, evaluate_repo_status
from repo_scanner_mvp.utils import counter_to_dict, utc_timestamp_slug


class RepoScanner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.github = GitHubClient(config.github)
        self.llm = LLMClient(config.llm)

    def _parse_protection(self, payload: dict[str, Any] | None) -> BranchProtectionSummary | None:
        if payload is None:
            return None
        if "_error" in payload:
            return BranchProtectionSummary(enabled=False, error=str(payload.get("_error")))

        required_status_checks = payload.get("required_status_checks") or {}
        pr_reviews = payload.get("required_pull_request_reviews") or {}
        enforce_admins = payload.get("enforce_admins") or {}
        allow_force_pushes = payload.get("allow_force_pushes") or {}
        allow_deletions = payload.get("allow_deletions") or {}
        required_linear_history = payload.get("required_linear_history") or {}

        checks: list[str] = []
        check_contexts = required_status_checks.get("contexts")
        if isinstance(check_contexts, list):
            checks = [str(item) for item in check_contexts]

        return BranchProtectionSummary(
            enabled=True,
            required_pull_request_reviews=bool(pr_reviews),
            required_status_checks=bool(required_status_checks),
            enforce_admins=bool(enforce_admins.get("enabled", False)),
            allows_force_pushes=bool(allow_force_pushes.get("enabled", False)),
            allows_deletions=bool(allow_deletions.get("enabled", False)),
            requires_linear_history=bool(required_linear_history.get("enabled", False)),
            contexts=checks,
            error=None,
        )

    def _repo_matches_filters(self, repo: dict[str, Any]) -> bool:
        if not self.config.github.include_archived and repo.get("archived"):
            return False
        if not self.config.github.include_forks and repo.get("fork"):
            return False
        allowlist = self.config.github.repo_allowlist
        if allowlist and repo.get("name") not in allowlist:
            return False
        return True

    def scan(self) -> tuple[ScanSummary, list[RepoScanResult]]:
        timestamp = utc_timestamp_slug(self.config.report_timestamp_override)
        repo_payloads = self.github.list_repositories()
        filtered_repos = [repo for repo in repo_payloads if self._repo_matches_filters(repo)]

        results: list[RepoScanResult] = []
        status_counter: Counter[str] = Counter()
        risk_counter: Counter[str] = Counter()

        for repo in filtered_repos:
            owner = repo["owner"]["login"]
            name = repo["name"]
            errors: list[str] = []
            branches: list[BranchSummary] = []

            try:
                branch_payloads = self.github.list_branches(owner, name)
            except GitHubApiError as exc:
                errors.append(str(exc))
                branch_payloads = []

            for branch in branch_payloads:
                branch_name = branch.get("name")
                protected = bool(branch.get("protected", False))
                protection_payload = None
                if protected and branch_name:
                    protection_payload = self.github.get_branch_protection(owner, name, branch_name)
                protection = self._parse_protection(protection_payload)
                branches.append(
                    BranchSummary(
                        name=branch_name,
                        protected=protected,
                        last_sha=(branch.get("commit") or {}).get("sha"),
                        protection=protection,
                    )
                )

            default_branch = repo.get("default_branch")
            status, risk, actions = evaluate_repo_status(
                archived=bool(repo.get("archived", False)),
                default_branch=default_branch,
                branches=branches,
            )
            branch_names = [branch.name for branch in branches]
            primary_candidate_branch = choose_primary_candidate_branch(default_branch, branch_names)
            protected_main = any(branch.name == "main" and branch.protected for branch in branches)
            protected_default = any(branch.name == default_branch and branch.protected for branch in branches)

            scan_result = RepoScanResult(
                full_name=repo.get("full_name", f"{owner}/{name}"),
                name=name,
                owner=owner,
                private=bool(repo.get("private", False)),
                archived=bool(repo.get("archived", False)),
                disabled=bool(repo.get("disabled", False)),
                fork=bool(repo.get("fork", False)),
                language=repo.get("language"),
                description=repo.get("description"),
                default_branch=default_branch,
                branches=branches,
                has_main="main" in branch_names,
                has_master="master" in branch_names,
                has_dev="dev" in branch_names,
                has_develop="develop" in branch_names,
                protected_main=protected_main,
                protected_default_branch=protected_default,
                primary_candidate_branch=primary_candidate_branch,
                repo_status=status,
                risk_level=risk,
                recommended_actions=actions,
                html_url=repo.get("html_url", ""),
                updated_at=repo.get("updated_at"),
                pushed_at=repo.get("pushed_at"),
                scan_errors=errors,
            )

            if self.config.llm.enabled:
                summary, classification = self.llm.enrich_repo(scan_result)
                scan_result.llm_summary = summary
                scan_result.llm_policy_classification = classification
                if summary is None and classification and classification.startswith("llm_error:"):
                    scan_result.scan_errors.append(classification)
                    scan_result.llm_policy_classification = None

            results.append(scan_result)
            status_counter[scan_result.repo_status] += 1
            risk_counter[scan_result.risk_level] += 1

        summary = ScanSummary(
            timestamp=timestamp,
            scan_mode=self.config.github.scan_mode,
            owner=self.config.github.owner,
            total_repos=len(results),
            total_archived=sum(1 for repo in results if repo.archived),
            total_with_dev=sum(1 for repo in results if repo.has_dev),
            total_with_main=sum(1 for repo in results if repo.has_main),
            total_with_protected_main=sum(1 for repo in results if repo.protected_main),
            repo_status_counts=counter_to_dict(status_counter),
            risk_counts=counter_to_dict(risk_counter),
        )
        return summary, results
