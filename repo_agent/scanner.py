from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    "coverage",
    ".coverage",
    "target",
    ".readme_rebuilder",
    ".history",
    "output",
    ".output",
    ".tox",
}

EXCLUDED_FILE_NAMES = {
    "README.generated.md",
}

EXCLUDED_SUFFIXES = {
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".db",
    ".log",
}

TEST_DIR_HINTS = {"tests", "test", "spec", "specs", "__tests__"}


def is_test_file(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if lower_parts & TEST_DIR_HINTS:
        return True
    lower_name = path.name.lower()
    return (
        lower_name.startswith("test_")
        or lower_name.endswith("_test.py")
        or lower_name.endswith(".spec.ts")
        or lower_name.endswith(".spec.js")
    )


def _excluded_dirs(extra_excludes: set[str] | None = None) -> set[str]:
    return EXCLUDED_DIRS | (extra_excludes or set())


def should_exclude(path: Path, root: Path | None = None, extra_excludes: set[str] | None = None) -> bool:
    excluded = _excluded_dirs(extra_excludes)
    rel = path.relative_to(root) if root else path
    if any(part in excluded for part in rel.parts):
        return True
    if rel.name in EXCLUDED_FILE_NAMES:
        return True
    return rel.suffix.lower() in EXCLUDED_SUFFIXES


def iter_repo_files(root: Path, extra_excludes: set[str] | None = None) -> Iterable[Path]:
    excluded = _excluded_dirs(extra_excludes)
    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)
        dirs[:] = [d for d in dirs if d not in excluded]
        if should_exclude(current_path, root, extra_excludes):
            continue
        for name in files:
            file_path = current_path / name
            if should_exclude(file_path, root, extra_excludes):
                continue
            yield file_path


def count_dirs(root: Path, extra_excludes: set[str] | None = None) -> int:
    excluded = _excluded_dirs(extra_excludes)
    total = 0
    for current_root, dirs, _ in os.walk(root):
        current_path = Path(current_root)
        dirs[:] = [d for d in dirs if d not in excluded]
        if should_exclude(current_path, root, extra_excludes):
            continue
        total += len(dirs)
    return total


def count_excluded_files(root: Path, extra_excludes: set[str] | None = None) -> int:
    excluded = _excluded_dirs(extra_excludes)
    total = 0
    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)
        keep_dirs = []
        for d in dirs:
            if d in excluded:
                total += 1
            else:
                keep_dirs.append(d)
        dirs[:] = keep_dirs
        for name in files:
            file_path = current_path / name
            if should_exclude(file_path, root, extra_excludes):
                total += 1
    return total


def extension_counts(files: Iterable[Path]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for path in files:
        ext = path.suffix.lower() or "<no_ext>"
        counter[ext] += 1
    return dict(counter.most_common())


def largest_files(files: Iterable[Path], root: Path, limit: int = 10) -> list[dict[str, object]]:
    records: list[tuple[int, Path]] = []
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        records.append((size, path))
    records.sort(reverse=True, key=lambda x: x[0])
    return [
        {
            "path": str(path.relative_to(root)),
            "size_bytes": size,
            "size_kb": round(size / 1024.0, 2),
        }
        for size, path in records[:limit]
    ]


def build_tree_preview(
    root: Path,
    max_depth: int = 3,
    max_entries_per_dir: int = 12,
    extra_excludes: set[str] | None = None,
) -> str:
    lines: list[str] = [root.name + "/"]

    def walk(current: Path, prefix: str = "", depth: int = 0) -> None:
        if depth >= max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return

        entries = [e for e in entries if not should_exclude(e, root, extra_excludes)]
        display_entries = entries[:max_entries_per_dir]

        for index, entry in enumerate(display_entries):
            connector = "└── " if index == len(display_entries) - 1 else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")
            if entry.is_dir():
                child_prefix = prefix + ("    " if index == len(display_entries) - 1 else "│   ")
                walk(entry, child_prefix, depth + 1)

        if len(entries) > len(display_entries):
            omitted = len(entries) - len(display_entries)
            lines.append(f"{prefix}└── ... ({omitted} entradas omitidas)")

    walk(root)
    return "\n".join(lines)


def read_text_file(path: Path, max_bytes: int = 150_000) -> str:
    try:
        raw = path.read_bytes()[:max_bytes]
        return raw.decode("utf-8", errors="ignore")
    except OSError:
        return ""
