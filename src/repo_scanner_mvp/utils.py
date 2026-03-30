from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def utc_timestamp_slug(override: str | None = None) -> str:
    if override:
        return override
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def csv_safe_join(values: list[str]) -> str:
    return " | ".join(values)


def counter_to_dict(counter: Counter) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))
