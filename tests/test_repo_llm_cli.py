from pathlib import Path

from repo_agent.llm import build_llm_context_bundle, build_llm_project_brief, maybe_generate_llm_summary
from repo_agent.models import Finding, RepoFacts


def _facts() -> RepoFacts:
    return RepoFacts(
        root_path="/tmp/proj",
        total_files=2,
        technologies=["Python", "Flask"],
        frameworks=["Flask"],
        package_managers=["pip"],
        ci_systems=["GitHub Actions"],
        project_type="webapp",
        project_summary="Aplicación Flask",
        main_languages=["Python"],
        has_readme=True,
        readme_status="standard",
        has_tests=True,
        has_env_example=True,
        notable_entrypoints=["app.py"],
    )


def _findings() -> list[Finding]:
    return [Finding(id="F1", title="Secretos hardcodeados", category="security", description="Token en código")]


def test_build_llm_project_brief():
    brief = build_llm_project_brief(_facts(), _findings())
    assert brief["repo"]["technologies"] == ["Python", "Flask"]
    assert "Flask" in brief["llm_prompt"]
    assert len(brief["top_findings"]) == 1


def test_build_llm_context_bundle(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")
    (root / "templates").mkdir()
    (root / "templates" / "base.html").write_text("<html></html>", encoding="utf-8")
    files = [root / "app.py", root / "templates" / "base.html"]

    bundle = build_llm_context_bundle(_facts(), _findings(), files, root)
    assert bundle["primary_file"]["path"] == "app.py"
    assert bundle["primary_file"]["included_mode"] == "full"
    assert "llm_context_prompt" in bundle
    assert bundle["budget"]["max_input_tokens"] == 24000


def test_maybe_generate_llm_summary_requires_env(monkeypatch):
    monkeypatch.delenv("REPO_AGENT_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("REPO_AGENT_LLM_MODEL", raising=False)
    assert maybe_generate_llm_summary(_facts(), _findings()) is None


def test_maybe_generate_llm_summary_on_error(monkeypatch):
    monkeypatch.setenv("REPO_AGENT_LLM_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setenv("REPO_AGENT_LLM_MODEL", "qwen")
    result = maybe_generate_llm_summary(_facts(), _findings())
    assert result is not None
    assert "no disponible" in result or "[LLM no disponible]" in result


def test_cli_builds_report(tmp_path: Path, capsys):
    from repo_agent.cli import main

    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef h(): return 'x'\n", encoding="utf-8")
    (root / "README.md").write_text("# Proyecto\n", encoding="utf-8")
    output = tmp_path / "out"
    code = main([
        str(root),
        "--output-dir",
        str(output),
        "--no-json",
    ])
    assert code == 0
    assert (output / "repo_diagnostic.md").exists()
    captured = capsys.readouterr()
    assert "[OK] Reporte generado" in captured.out