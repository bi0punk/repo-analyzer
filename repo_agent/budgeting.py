from __future__ import annotations


def estimate_tokens_from_text(text: str) -> int:
    return max(1, int(len(text) / 4))


def compute_budget(max_input_tokens: int, ratio: float) -> int:
    safe_ratio = max(0.05, min(ratio, 0.90))
    return max(256, int(max_input_tokens * safe_ratio))


def fits_in_budget(text: str, budget_tokens: int) -> bool:
    return estimate_tokens_from_text(text) <= budget_tokens
