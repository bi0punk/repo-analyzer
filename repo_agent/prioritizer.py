from __future__ import annotations

from typing import List

from .models import Finding


PRIORITY_BUCKETS = [
    (4.2, "P0 - inmediato"),
    (3.6, "P1 - siguiente paso"),
    (3.0, "P2 - importante"),
    (0.0, "P3 - deuda técnica"),
]


def assign_bucket(score: float) -> str:
    for threshold, label in PRIORITY_BUCKETS:
        if score >= threshold:
            return label
    return "P3 - deuda técnica"


def top_findings(findings: List[Finding], limit: int = 12) -> List[Finding]:
    return findings[:limit]
