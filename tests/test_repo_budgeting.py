from repo_agent.budgeting import compute_budget, estimate_tokens_from_text, fits_in_budget


def test_estimate_tokens_from_text():
    assert estimate_tokens_from_text("a" * 400) == 100
    assert estimate_tokens_from_text("") == 1


def test_compute_budget_clamps_ratio():
    assert compute_budget(max_input_tokens=24000, ratio=0.35) == 8400
    assert compute_budget(max_input_tokens=24000, ratio=0.99) == 21600
    assert compute_budget(max_input_tokens=24000, ratio=0.0) == 1200


def test_compute_budget_minimum():
    assert compute_budget(max_input_tokens=500, ratio=0.10) == 256


def test_compute_budget_never_exceeds_total():
    assert compute_budget(max_input_tokens=200, ratio=0.10) == 200
    assert compute_budget(max_input_tokens=300, ratio=0.90) == 270
    assert compute_budget(max_input_tokens=100, ratio=0.90) <= 100


def test_fits_in_budget():
    assert fits_in_budget("a" * 800, budget_tokens=200) is True
    assert fits_in_budget("a" * 1200, budget_tokens=200) is False