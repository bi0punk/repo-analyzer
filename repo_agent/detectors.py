from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Set

from .scanner import read_text_file


README_CANDIDATES = {"readme.md", "readme.txt", "readme", "readme.generated.md"}


def _contains_any(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def detect_stack(root: Path, files: Iterable[Path]) -> Dict[str, object]:
    file_list = list(files)
    file_set: Set[str] = {str(p.relative_to(root)).replace("\\", "/") for p in file_list}
    names = {Path(f).name for f in file_set}

    technologies = set()
    frameworks = set()
    package_managers = set()
    ci_systems = set()
    notable_entrypoints = []
    scan_notes = []

    def has(name: str) -> bool:
        return name in names or name in file_set

    ext_set = {p.suffix.lower() for p in file_list}
    if ".py" in ext_set:
        technologies.add("Python")
    if ".html" in ext_set:
        technologies.add("HTML")
    if ".css" in ext_set or ".scss" in ext_set:
        technologies.add("CSS")
    if ".js" in ext_set or ".ts" in ext_set or ".tsx" in ext_set or ".jsx" in ext_set:
        technologies.add("JavaScript/TypeScript")
    if has("requirements.txt") or has("pyproject.toml") or has("setup.py"):
        technologies.add("Python")
    if has("package.json"):
        technologies.add("JavaScript/TypeScript")
        package_managers.add("npm/yarn/pnpm")
    if has("go.mod"):
        technologies.add("Go")
    if has("Cargo.toml"):
        technologies.add("Rust")
    if has("pom.xml") or has("build.gradle") or has("build.gradle.kts"):
        technologies.add("Java/Kotlin")
    if has("composer.json"):
        technologies.add("PHP")
    if has("Gemfile"):
        technologies.add("Ruby")
    if has("Dockerfile") or any(f.endswith("docker-compose.yml") or f.endswith("docker-compose.yaml") for f in file_set):
        technologies.add("Docker")

    has_templates = (root / "templates").is_dir()
    has_static = (root / "static").is_dir()
    if has_templates:
        technologies.add("Server-side templates")
    if has_static:
        technologies.add("Static assets")

    project_type = "unknown"
    if has_templates and has_static:
        project_type = "server_rendered_web_app"
        technologies.add("Web App")
    elif has("package.json") and has("src"):
        project_type = "frontend_or_fullstack_app"
    elif has("Dockerfile"):
        project_type = "service_or_containerized_app"

    app_entry_candidates = [
        root / "app.py",
        root / "main.py",
        root / "manage.py",
        root / "server.py",
    ]
    entry_text = ""
    for candidate in app_entry_candidates:
        if candidate.exists():
            notable_entrypoints.append(str(candidate.relative_to(root)))
            entry_text += "\n" + read_text_file(candidate)

    if has("manage.py"):
        frameworks.add("Django")
    if _contains_any(entry_text, ["from flask import", "flask(", "@app.route", "render_template("]):
        frameworks.add("Flask")
        technologies.add("Jinja2" if "render_template(" in entry_text else "Python Web")
        if project_type == "unknown":
            project_type = "server_rendered_web_app"
    elif any((root / path).exists() for path in ["app.py", "main.py"]) and has_templates:
        frameworks.add("Flask-like")
        if project_type == "unknown":
            project_type = "server_rendered_web_app"
        scan_notes.append("Se detectó estructura app.py + templates, compatible con Flask/Jinja o app similar renderizada en servidor.")

    if _contains_any(entry_text, ["fastapi", "uvicorn", "from fastapi import"]):
        frameworks.add("FastAPI")
        if project_type == "unknown":
            project_type = "api_service"

    if has("package.json"):
        package_json = root / "package.json"
        if package_json.exists():
            content = package_json.read_text(encoding="utf-8", errors="ignore").lower()
            if '"react"' in content:
                frameworks.add("React")
            if '"next"' in content or '"next.js"' in content:
                frameworks.add("Next.js")
            if '"vue"' in content:
                frameworks.add("Vue")
            if '"express"' in content:
                frameworks.add("Express")
            if '"nestjs"' in content:
                frameworks.add("NestJS")
            if '"typescript"' in content:
                technologies.add("TypeScript")

    if has("pyproject.toml"):
        content = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore").lower()
        if "fastapi" in content:
            frameworks.add("FastAPI")
        if "flask" in content:
            frameworks.add("Flask")
        if "django" in content:
            frameworks.add("Django")
        if "poetry" in content:
            package_managers.add("Poetry")
        if "hatch" in content:
            package_managers.add("Hatch")
        if "pdm" in content:
            package_managers.add("PDM")

    if has("requirements.txt"):
        req = (root / "requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
        if "flask" in req:
            frameworks.add("Flask")
        if "fastapi" in req:
            frameworks.add("FastAPI")
        if "django" in req:
            frameworks.add("Django")

    if has(".github/workflows") or any(f.startswith(".github/workflows/") for f in file_set):
        ci_systems.add("GitHub Actions")
    if has(".gitlab-ci.yml"):
        ci_systems.add("GitLab CI")
    if has("Jenkinsfile"):
        ci_systems.add("Jenkins")

    has_readme_md = (root / "README.md").exists() or (root / "readme.md").exists()
    has_readme_generated = (root / "README.generated.md").exists()
    if has_readme_md:
        readme_status = "standard"
        readme_path = "README.md"
    elif has_readme_generated:
        readme_status = "generated_only"
        readme_path = "README.generated.md"
        scan_notes.append("Se encontró README generado, pero no README.md principal estándar.")
    else:
        readme_status = "missing"
        readme_path = None

    route_count = entry_text.count("@app.route") + entry_text.count("@bp.route")
    if route_count:
        scan_notes.append(f"Se detectaron aproximadamente {route_count} rutas decoradas en entrypoints Python.")

    if any(_contains_any(read_text_file(p), ["bootstrap", "btn-", "container-fluid", "navbar"]) for p in file_list if p.suffix.lower() in {".html", ".css", ".js"}):
        technologies.add("Bootstrap")

    summary_parts = []
    if frameworks:
        summary_parts.append(f"Stack principal sugerido: {', '.join(sorted(frameworks))}")
    if project_type != "unknown":
        summary_parts.append(f"Tipo de proyecto: {project_type}")
    if has_templates or has_static:
        summary_parts.append(f"Estructura web detectada: templates={'sí' if has_templates else 'no'}, static={'sí' if has_static else 'no'}")

    return {
        "technologies": sorted(technologies),
        "frameworks": sorted(frameworks),
        "package_managers": sorted(package_managers),
        "ci_systems": sorted(ci_systems),
        "project_type": project_type,
        "project_summary": "; ".join(summary_parts),
        "readme_status": readme_status,
        "readme_path": readme_path,
        "route_count": route_count,
        "has_templates_dir": has_templates,
        "has_static_dir": has_static,
        "notable_entrypoints": notable_entrypoints,
        "scan_notes": scan_notes,
    }



def detect_languages_from_extensions(extension_count_map: Dict[str, int]) -> List[str]:
    mapping = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".jsx": "JavaScript/React",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".php": "PHP",
        ".rb": "Ruby",
        ".cs": "C#",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
        ".hpp": "C++ Header",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sql": "SQL",
        ".sh": "Shell",
    }
    ranked = sorted(extension_count_map.items(), key=lambda x: x[1], reverse=True)
    languages = []
    for ext, _ in ranked:
        lang = mapping.get(ext)
        if lang and lang not in languages:
            languages.append(lang)
    return languages[:6]
