from __future__ import annotations

from unittest.mock import patch

import pytest

from repo_agent.llm import LLMError, chat_completion, get_base_endpoint, validate_chat_url


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_get_base_endpoint_allows_http_https():
    assert get_base_endpoint("http://127.0.0.1:8080") == "http://127.0.0.1:8080"
    assert get_base_endpoint("https://localhost:8443/") == "https://localhost:8443"


def test_get_base_endpoint_rejects_dangerous_scheme():
    with pytest.raises(LLMError):
        get_base_endpoint("file:///etc/passwd")
    with pytest.raises(LLMError):
        validate_chat_url("file:///etc/passwd")


def test_validate_chat_url_keeps_full_path():
    assert validate_chat_url("https://host/v1/chat/completions") == "https://host/v1/chat/completions"


def test_chat_completion_returns_content():
    payload = {"choices": [{"message": {"content": "ok"}}]}
    with patch("repo_agent.llm.requests.post", return_value=_FakeResponse(payload)) as mocked:
        result = chat_completion(
            url="http://127.0.0.1:8080/v1/chat/completions",
            model="qwen",
            messages=[{"role": "user", "content": "hola"}],
            max_tokens=100,
        )
    assert result == "ok"
    assert mocked.call_args.kwargs["json"]["max_tokens"] == 100


def test_chat_completion_rejects_bad_url():
    with pytest.raises(LLMError):
        chat_completion(url="ftp://host/v1", model="qwen", messages=[])


def test_scanner_llm_client_delegates_to_shared_client():
    from repo_scanner_mvp.config import LLMConfig
    from repo_scanner_mvp.llm_client import LLMClient
    from repo_scanner_mvp.models import BranchSummary, RepoScanResult

    config = LLMConfig(
        enabled=True,
        base_url="http://127.0.0.1:8080",
        chat_path="/v1/chat/completions",
        model="qwen",
        timeout_seconds=60,
        temperature=0.1,
        max_tokens=700,
    )
    repo = RepoScanResult(
        full_name="bi0punk/repo",
        name="repo",
        owner="bi0punk",
        private=False,
        archived=False,
        disabled=False,
        fork=False,
        language="Python",
        description=None,
        default_branch="main",
        branches=[BranchSummary(name="main", protected=False)],
        has_main=True,
        has_master=False,
        has_dev=False,
        has_develop=False,
        protected_main=False,
        protected_default_branch=False,
        primary_candidate_branch=None,
        repo_status="clean",
        risk_level="low",
        recommended_actions=[],
        html_url="https://github.com/bi0punk/repo",
        updated_at=None,
        pushed_at=None,
    )

    with patch(
        "repo_scanner_mvp.llm_client.chat_completion", return_value="SUMMARY: resumido\nCLASSIFICATION: normal"
    ) as mocked:
        client = LLMClient(config)
        summary, classification = client.enrich_repo(repo)
    assert summary == "resumido"
    assert classification == "normal"
    assert mocked.call_args.kwargs["url"] == "http://127.0.0.1:8080/v1/chat/completions"


def test_cli_rejects_unknown_subcommand():
    from repo_agent.cli import main

    with pytest.raises(SystemExit):
        main(["unknown"])
