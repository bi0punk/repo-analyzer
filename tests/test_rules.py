from repo_scanner_mvp.models import BranchSummary
from repo_scanner_mvp.rules import choose_primary_candidate_branch, evaluate_repo_status


def test_choose_primary_candidate_branch_prefers_default() -> None:
    assert choose_primary_candidate_branch("release", ["dev", "release", "main"]) == "release"


def test_choose_primary_candidate_branch_falls_back_to_preferred() -> None:
    assert choose_primary_candidate_branch(None, ["master", "feature-x"]) == "master"


def test_evaluate_repo_status_main_only() -> None:
    status, risk, actions = evaluate_repo_status(
        archived=False,
        default_branch="main",
        branches=[BranchSummary(name="main", protected=False)],
    )
    assert status == "main_only"
    assert risk == "high"
    assert "create_dev_from_primary_candidate" in actions
    assert "protect_main_branch" in actions
