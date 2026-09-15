from pathlib import Path

from repo_agent.importance import score_file_importance, select_primary_file, select_supporting_files


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    return root


def test_score_priority_entrypoint(tmp_path: Path):
    root = _repo(tmp_path)
    app = root / "app.py"
    app.write_text("from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef h(): return 'x'\n", encoding="utf-8")
    score = score_file_importance(app, root)
    assert score > 100


def test_score_main_script(tmp_path: Path):
    root = _repo(tmp_path)
    app = root / "main.py"
    app.write_text("if __name__ == '__main__':\n    print('x')\n", encoding="utf-8")
    assert score_file_importance(app, root) > 0


def test_select_primary_file_picks_flask_app(tmp_path: Path):
    root = _repo(tmp_path)
    (root / "src" / "app.py").write_text(
        "from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef h(): return 'x'\n",
        encoding="utf-8",
    )
    (root / "src" / "helper.py").write_text("def f(): pass\n", encoding="utf-8")
    files = list((root / "src").iterdir())
    selected = select_primary_file(root, files)
    assert selected is not None
    assert selected["path"] == "src/app.py"


def test_select_primary_file_none_without_code(tmp_path: Path):
    root = _repo(tmp_path)
    (root / "notes.md").write_text("# notas\n", encoding="utf-8")
    assert select_primary_file(root, [root / "notes.md"]) is None


def test_select_supporting_files_excludes_primary(tmp_path: Path):
    root = _repo(tmp_path)
    (root / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")
    (root / "templates").mkdir()
    (root / "templates" / "base.html").write_text("<html><body>{{ x }}</body></html>", encoding="utf-8")
    (root / "static").mkdir()
    (root / "static" / "app.js").write_text("function main() {}\n", encoding="utf-8")
    files = [root / "app.py", root / "templates" / "base.html", root / "static" / "app.js"]
    supporting = select_supporting_files(root, files, primary_relative_path="app.py", max_files=2)
    assert supporting
    assert all(f["path"] != "app.py" for f in supporting)
    assert len(supporting) <= 2