from __future__ import annotations

from typing import Iterable

from repo_scanner_mvp.models import BranchSummary


PREFERRED_BRANCH_ORDER = ["dev", "develop", "main", "master"]


def choose_primary_candidate_branch(default_branch: str | None, branch_names: Iterable[str]) -> str | None:
    names = {name.strip() for name in branch_names}
    if default_branch and default_branch in names:
        return default_branch
    for candidate in PREFERRED_BRANCH_ORDER:
        if candidate in names:
            return candidate
    return sorted(names)[0] if names else None


def evaluate_repo_status(
    *,
    archived: bool,
    default_branch: str | None,
    branches: list[BranchSummary],
) -> tuple[str, str, list[str]]:
    branch_names = {branch.name for branch in branches}
    has_main = "main" in branch_names
    has_master = "master" in branch_names
    has_dev = "dev" in branch_names
    has_develop = "develop" in branch_names
    protected_main = any(branch.name == "main" and branch.protected for branch in branches)
    protected_default = any(branch.name == default_branch and branch.protected for branch in branches)

    if archived:
        return ("archived", "low", ["skip_changes_archived_repo"])

    actions: list[str] = []
    risk = "low"

    if not has_dev:
        actions.append("create_dev_from_primary_candidate")
        risk = "medium"

    if not has_main and has_master:
        actions.append("plan_main_creation_or_master_migration")
        risk = "high"
    elif not has_main:
        actions.append("create_main_after_dev_validation")
        risk = "high"

    if has_main and not protected_main:
        actions.append("protect_main_branch")
        risk = "high"

    if default_branch not in {"main", "dev", "master", "develop"}:
        actions.append("review_default_branch_alignment")
        risk = "medium" if risk == "low" else risk

    if has_dev and has_main and protected_main:
        if default_branch in {"main", "dev"}:
            return ("nearly_ready", risk, actions or ["validate_dev_then_pr_to_main"])

    if has_master and not has_main:
        return ("legacy_master_layout", risk, actions)

    if has_dev and not has_main:
        return ("dev_without_main", risk, actions)

    if has_main and not has_dev:
        return ("main_only", risk, actions)

    return ("needs_normalization", risk, actions or ["manual_review"])
