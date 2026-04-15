from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .scanner import read_text_file

ENTRYPOINT_PRIORITY = [
    "app.py",
    "main.py",
    "server.py",
    "run.py",
    "wsgi.py",
    "manage.py",
    "src/app.py",
    "src/main.py",
    "src/server.py",
    "server.js",
    "server.ts",
    "app.js",
    "app.ts",
    "src/index.ts",
    "src/main.ts",
]


def _score_priority_name(rel: str, name: str) -> float:
    score = 0.0
    for idx, candidate in enumerate(ENTRYPOINT_PRIORITY):
        cand_name = Path(candidate).name.lower()
        if rel == candidate:
            return 120 - idx
        if name == cand_name:
            score = max(score, 90 - idx)
    return score


def score_file_importance(path: Path, repo_root: Path) -> float:
    rel = path.relative_to(repo_root).as_posix()
    name = path.name.lower()
    text = read_text_file(path, max_bytes=400_000)
    lowered = text.lower()

    score = _score_priority_name(rel, name)

    if path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx"}:
        score += 10

    if "from flask import" in lowered or "flask(" in lowered:
        score += 40
    if "render_template(" in lowered:
        score += 30
    if "@app.route" in lowered or "@bp.route" in lowered:
        score += 55
    if "if __name__ == \"__main__\"" in lowered or "if __name__ == '__main__'" in lowered:
        score += 20
    if "app.run(" in lowered or "uvicorn.run(" in lowered:
        score += 15
    if "from fastapi import" in lowered or "fastapi(" in lowered:
        score += 35
    if "express()" in lowered or "const app = express(" in lowered:
        score += 30
    if "router = apirouter(" in lowered:
        score += 20

    line_count = len(text.splitlines())
    if 80 <= line_count <= 1400:
        score += 15
    elif line_count < 20:
        score -= 10
    elif line_count > 2500:
        score -= 8

    if rel.startswith("src/"):
        score += 5
    if any(part in {"routes", "routers", "views"} for part in path.parts):
        score += 8

    return score


def score_supporting_file(path: Path, repo_root: Path) -> float:
    rel = path.relative_to(repo_root).as_posix()
    score = 0.0
    suffix = path.suffix.lower()
    text = read_text_file(path, max_bytes=200_000).lower()

    if suffix == ".html":
        score += 25
        if "base" in path.name.lower() or "index" in path.name.lower():
            score += 12
        if "bootstrap" in text or "navbar" in text or "container-fluid" in text:
            score += 6
    elif suffix in {".js", ".ts", ".tsx", ".jsx"}:
        score += 18
        if "main" in path.name.lower() or "app" in path.name.lower():
            score += 8
    elif suffix in {".css", ".scss"}:
        score += 12
        if "style" in path.name.lower() or "main" in path.name.lower():
            score += 6

    if rel.startswith("templates/"):
        score += 8
    if rel.startswith("static/js/"):
        score += 7
    if rel.startswith("static/css/"):
        score += 5

    return score


def select_primary_file(repo_root: Path, files: List[Path]) -> Dict[str, object] | None:
    candidates = []
    for path in files:
        if path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx"}:
            continue
        score = score_file_importance(path, repo_root)
        if score <= 0:
            continue
        text = read_text_file(path, max_bytes=400_000)
        candidates.append({
            "path": path,
            "relative_path": path.relative_to(repo_root).as_posix(),
            "score": round(score, 2),
            "line_count": len(text.splitlines()),
            "char_count": len(text),
            "content": text,
        })
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x["score"], x["line_count"]), reverse=True)
    best = candidates[0]
    return {
        "path": best["relative_path"],
        "score": best["score"],
        "line_count": best["line_count"],
        "char_count": best["char_count"],
        "content": best["content"],
    }


def select_supporting_files(repo_root: Path, files: List[Path], primary_relative_path: str | None, max_files: int = 2) -> List[Dict[str, object]]:
    candidates = []
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        if primary_relative_path and rel == primary_relative_path:
            continue
        if path.suffix.lower() not in {".html", ".css", ".scss", ".js", ".ts", ".tsx", ".jsx"}:
            continue
        score = score_supporting_file(path, repo_root)
        if score <= 0:
            continue
        text = read_text_file(path, max_bytes=250_000)
        candidates.append({
            "path": rel,
            "score": round(score, 2),
            "line_count": len(text.splitlines()),
            "char_count": len(text),
            "content": text,
        })
    candidates.sort(key=lambda x: (x["score"], x["line_count"]), reverse=True)
    return candidates[:max_files]
