from pathlib import Path

from repo_agent.analyzers import RepoAnalyzer
from repo_agent.models import RepoFacts
from repo_agent.scanner import is_test_file


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    return root


def test_is_test_file_detects_root_test_script():
    assert is_test_file(Path("test_utils.py"))
    assert is_test_file(Path("utils_test.py"))
    assert is_test_file(Path("component.spec.ts"))
    assert is_test_file(Path("components/button.spec.js"))
    assert is_test_file(Path("tests/test_x.py"))
    assert not is_test_file(Path("app.py"))
    assert not is_test_file(Path("readme.md"))


def test_has_tests_true_with_root_test_file(tmp_path: Path):
    from repo_agent.cli import build_repo_facts

    root = _make_repo(tmp_path)
    (root / "test_utils.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    facts, _ = build_repo_facts(root)
    assert facts.has_tests is True


def test_has_tests_false_without_test_files(tmp_path: Path):
    from repo_agent.cli import build_repo_facts

    root = _make_repo(tmp_path)
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    facts, _ = build_repo_facts(root)
    assert facts.has_tests is False


def test_readme_path_prefers_root(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "docs").mkdir()
    (root / "README.md").write_text("# raíz\n", encoding="utf-8")
    (root / "docs" / "README.md").write_text("# anidado\n", encoding="utf-8")
    facts = RepoFacts(root_path=str(root))
    analyzer = RepoAnalyzer(root=root, all_files=[root / "README.md", root / "docs" / "README.md"], facts=facts)
    assert analyzer._readme_path() == root / "README.md"


def test_readme_path_falls_back_to_nested(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# anidado\n", encoding="utf-8")
    facts = RepoFacts(root_path=str(root))
    analyzer = RepoAnalyzer(root=root, all_files=[root / "docs" / "README.md"], facts=facts)
    assert analyzer._readme_path() == root / "docs" / "README.md"


def test_entrypoint_findings_detect_large_main(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "main.py").write_text("import flask\n" + ("print('line')\n" * 450), encoding="utf-8")
    facts = RepoFacts(
        root_path=str(root),
        notable_entrypoints=["main.py"],
        readme_status="missing",
    )
    analyzer = RepoAnalyzer(root=root, all_files=[root / "main.py"], facts=facts)
    findings = {f.id: f for f in analyzer._entrypoint_findings()}
    assert "entrypoint-app-py-large" in findings
    assert findings["entrypoint-app-py-large"].affected_files == ["main.py"]