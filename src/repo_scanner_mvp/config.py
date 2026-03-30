from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from repo_scanner_mvp.utils import bool_env


@dataclass(slots=True)
class GitHubConfig:
    token: str
    scan_mode: str
    owner: str | None
    include_archived: bool
    include_forks: bool
    per_page: int
    max_repos: int
    api_version: str
    api_base_url: str
    repo_allowlist: list[str]


@dataclass(slots=True)
class LLMConfig:
    enabled: bool
    base_url: str
    chat_path: str
    model: str
    timeout_seconds: int
    temperature: float
    max_tokens: int


@dataclass(slots=True)
class AppConfig:
    github: GitHubConfig
    llm: LLMConfig
    output_dir: str
    report_timestamp_override: str | None
    project_root: Path


def load_config(env_file: str | None = None) -> AppConfig:
    load_dotenv(dotenv_path=env_file)

    token = os.getenv("GITHUB_TOKEN", "").strip()
    scan_mode = os.getenv("GITHUB_SCAN_MODE", "authenticated").strip().lower()
    owner = os.getenv("GITHUB_OWNER", "").strip() or None

    repo_allowlist_raw = os.getenv("GITHUB_REPO_ALLOWLIST", "").strip()
    repo_allowlist = [part.strip() for part in repo_allowlist_raw.split(",") if part.strip()]

    github = GitHubConfig(
        token=token,
        scan_mode=scan_mode,
        owner=owner,
        include_archived=bool_env(os.getenv("GITHUB_INCLUDE_ARCHIVED"), default=False),
        include_forks=bool_env(os.getenv("GITHUB_INCLUDE_FORKS"), default=True),
        per_page=int(os.getenv("GITHUB_PER_PAGE", "100")),
        max_repos=int(os.getenv("GITHUB_MAX_REPOS", "0")),
        api_version=os.getenv("GITHUB_API_VERSION", "2026-03-10").strip(),
        api_base_url=os.getenv("GITHUB_API_BASE_URL", "https://api.github.com").rstrip("/"),
        repo_allowlist=repo_allowlist,
    )

    llm = LLMConfig(
        enabled=bool_env(os.getenv("LLM_ENABLED"), default=True),
        base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        chat_path=os.getenv("LLM_CHAT_PATH", "/v1/chat/completions").strip(),
        model=os.getenv("LLM_MODEL", "local-model").strip(),
        timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "700")),
    )

    return AppConfig(
        github=github,
        llm=llm,
        output_dir=os.getenv("OUTPUT_DIR", "./outputs").strip(),
        report_timestamp_override=os.getenv("REPORT_TIMESTAMP_OVERRIDE", "").strip() or None,
        project_root=Path.cwd(),
    )


def validate_config(config: AppConfig) -> None:
    if config.github.scan_mode not in {"authenticated", "org", "user"}:
        raise ValueError("GITHUB_SCAN_MODE must be one of: authenticated, org, user")

    if config.github.scan_mode in {"org", "user"} and not config.github.owner:
        raise ValueError("GITHUB_OWNER is required when GITHUB_SCAN_MODE is org or user")

    if not config.github.token:
        raise ValueError("GITHUB_TOKEN is required")

    if config.github.per_page <= 0 or config.github.per_page > 100:
        raise ValueError("GITHUB_PER_PAGE must be between 1 and 100")

    if config.github.max_repos < 0:
        raise ValueError("GITHUB_MAX_REPOS must be >= 0")
