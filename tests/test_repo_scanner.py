from pathlib import Path

from repo_agent.scanner import (
    build_tree_preview,
    count_excluded_files,
    extension_counts,
    iter_repo_files,
    largest_files,
    should_exclude,
)


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "node_modules").mkdir()
    (root / "__pycache__").mkdir()
    (root / "src" / "app.py").write_text("print('hola')\n", encoding="utf-8")
    (root / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / "README.md").write_text("# Proyecto\n", encoding="utf-8")
    (root / "node_modules" / "lib.js").write_text("console.log(1)\n", encoding="utf-8")
    (root / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"\x00")
    (root / "data.db").write_bytes(b"\x00")
    return root


def test_should_exclude_known_dirs(tmp_path: Path):
    root = _make_repo(tmp_path)
    assert should_exclude(root / "node_modules", root)
    assert should_exclude(root / "__pycache__", root)
    assert not should_exclude(root / "src" / "app.py", root)


def test_should_exclude_suffixes(tmp_path: Path):
    root = _make_repo(tmp_path)
    assert should_exclude(root / "data.db", root)


def test_iter_repo_files_excludes_noise(tmp_path: Path):
    root = _make_repo(tmp_path)
    files = sorted(p.relative_to(root).as_posix() for p in iter_repo_files(root))
    assert "src/app.py" in files
    assert "src/mod.py" in files
    assert "README.md" in files
    assert "node_modules/lib.js" not in files
    assert "__pycache__/app.cpython-312.pyc" not in files
    assert "data.db" not in files


def test_extension_counts(tmp_path: Path):
    root = _make_repo(tmp_path)
    files = list(iter_repo_files(root))
    counts = extension_counts(files)
    assert counts[".py"] == 2
    assert counts[".md"] == 1


def test_largest_files(tmp_path: Path):
    root = _make_repo(tmp_path)
    (root / "src" / "big.py").write_text("a" * 10_000, encoding="utf-8")
    files = list(iter_repo_files(root))
    top = largest_files(files, root, limit=1)
    assert top[0]["path"] == "src/big.py"
    assert top[0]["size_bytes"] == 10_000


def test_build_tree_preview_limits(tmp_path: Path):
    root = _make_repo(tmp_path)
    for i in range(20):
        (root / f"f{i}.txt").write_text("x", encoding="utf-8")
    tree = build_tree_preview(root, max_depth=2, max_entries_per_dir=12)
    assert "omitidas" in tree


def test_count_excluded_files(tmp_path: Path):
    root = _make_repo(tmp_path)
    assert count_excluded_files(root) >= 2