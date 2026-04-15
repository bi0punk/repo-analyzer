from __future__ import annotations

import json
import re
from typing import Dict, Any, List

from .budgeting import estimate_tokens_from_text


def summarize_python_file(text: str, max_snippets: int = 10) -> Dict[str, Any]:
    lines = text.splitlines()
    imports: List[Dict[str, Any]] = []
    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    config_signals: List[Dict[str, Any]] = []
    snippets: List[Dict[str, Any]] = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append({"line": i, "code": stripped})
        if stripped.startswith("def "):
            functions.append({"line": i, "signature": stripped})
        if stripped.startswith("class "):
            classes.append({"line": i, "signature": stripped})
        if "@app.route" in stripped or "@bp.route" in stripped or "@router." in stripped:
            routes.append({"line": i, "code": stripped})
        if any(tok in stripped for tok in ["debug=True", "app.run(", "SECRET_KEY", "os.getenv(", "load_dotenv("]):
            config_signals.append({"line": i, "code": stripped})

    interesting_patterns = [
        r"@app\.route",
        r"@bp\.route",
        r"@router\.",
        r"def\s+\w+\(",
        r"class\s+\w+",
        r"render_template\(",
        r"app\.run\(",
        r"Flask\(",
    ]
    used_ranges = set()
    for i, line in enumerate(lines, start=1):
        if any(re.search(p, line) for p in interesting_patterns):
            start = max(0, i - 3)
            end = min(len(lines), i + 6)
            key = (start, end)
            if key in used_ranges:
                continue
            used_ranges.add(key)
            snippets.append({
                "start_line": start + 1,
                "end_line": end,
                "snippet": "\n".join(lines[start:end]),
            })
            if len(snippets) >= max_snippets:
                break

    return {
        "imports": imports[:50],
        "functions": functions[:80],
        "classes": classes[:40],
        "routes": routes[:50],
        "config_signals": config_signals[:30],
        "key_snippets": snippets,
    }


def summarize_javascript_file(text: str, max_snippets: int = 10) -> Dict[str, Any]:
    lines = text.splitlines()
    imports = []
    functions = []
    classes = []
    routes = []
    snippets = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("const ") or stripped.startswith("let "):
            imports.append({"line": i, "code": stripped})
        if re.match(r"(async\s+)?function\s+\w+", stripped) or re.match(r"const\s+\w+\s*=\s*\(.*\)\s*=>", stripped):
            functions.append({"line": i, "signature": stripped})
        if stripped.startswith("class "):
            classes.append({"line": i, "signature": stripped})
        if any(tok in stripped for tok in ["app.get(", "app.post(", "router.get(", "router.post("]):
            routes.append({"line": i, "code": stripped})

    patterns = [r"app\.get\(", r"app\.post\(", r"router\.get\(", r"router\.post\(", r"function\s+\w+", r"class\s+\w+"]
    for i, line in enumerate(lines, start=1):
        if any(re.search(p, line) for p in patterns):
            start = max(0, i - 3)
            end = min(len(lines), i + 6)
            snippets.append({
                "start_line": start + 1,
                "end_line": end,
                "snippet": "\n".join(lines[start:end]),
            })
            if len(snippets) >= max_snippets:
                break

    return {
        "imports": imports[:50],
        "functions": functions[:80],
        "classes": classes[:40],
        "routes": routes[:50],
        "key_snippets": snippets,
    }


def summarize_markup_or_style(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    preview = "\n".join(lines[:160])
    return {
        "line_count": len(lines),
        "preview": preview,
        "estimated_tokens_preview": estimate_tokens_from_text(preview),
    }


def build_file_payload(relative_path: str, content: str, budget_tokens: int) -> Dict[str, Any]:
    estimated_tokens = estimate_tokens_from_text(content)
    suffix = relative_path.lower().rsplit(".", 1)[-1] if "." in relative_path else ""

    if estimated_tokens <= budget_tokens:
        return {
            "path": relative_path,
            "included_mode": "full",
            "estimated_tokens": estimated_tokens,
            "budget_tokens": budget_tokens,
            "content": content,
        }

    if suffix == "py":
        summary = summarize_python_file(content)
    elif suffix in {"js", "ts", "tsx", "jsx"}:
        summary = summarize_javascript_file(content)
    else:
        summary = summarize_markup_or_style(content)

    return {
        "path": relative_path,
        "included_mode": "summary",
        "estimated_tokens": estimated_tokens,
        "budget_tokens": budget_tokens,
        "summary": summary,
    }


def build_selected_files_markdown(context_bundle: Dict[str, Any]) -> str:
    lines = ["# Archivos seleccionados para contexto LLM", ""]
    primary = context_bundle.get("primary_file")
    if primary:
        lines.append("## Archivo principal")
        lines.append(f"- Ruta: `{primary.get('path')}`")
        lines.append(f"- Modo incluido: {primary.get('included_mode')}")
        lines.append(f"- Tokens estimados: {primary.get('estimated_tokens')}")
        lines.append("")
        if primary.get("included_mode") == "summary":
            summary = primary.get("summary", {})
            if isinstance(summary, dict):
                lines.append("### Resumen estructurado")
                for key in ["imports", "functions", "classes", "routes", "config_signals", "key_snippets"]:
                    value = summary.get(key)
                    if value:
                        lines.append(f"- {key}: {len(value) if isinstance(value, list) else 'sí'}")
                lines.append("")

    secondary_files = context_bundle.get("secondary_files", [])
    if secondary_files:
        lines.append("## Archivos satélite")
        for item in secondary_files:
            lines.append(f"- `{item.get('path')}` | modo={item.get('included_mode')} | tokens={item.get('estimated_tokens')}")
        lines.append("")

    prompt = context_bundle.get("llm_context_prompt")
    if prompt:
        lines.extend([
            "## Prompt sugerido",
            "```text",
            str(prompt).strip(),
            "```",
        ])
    return "\n".join(lines).strip() + "\n"


def build_prompt_from_bundle(project_brief: Dict[str, Any], context_bundle: Dict[str, Any]) -> str:
    prompt_payload = {
        "project_brief": project_brief,
        "important_context": {
            "primary_file": context_bundle.get("primary_file"),
            "secondary_files": context_bundle.get("secondary_files", []),
            "budget": context_bundle.get("budget", {}),
        },
    }
    return (
        "Actúa como arquitecto y mantenedor técnico del proyecto.\n"
        "Usa el diagnóstico preliminar y el archivo principal seleccionado para inferir el objetivo del sistema, stack, riesgos técnicos, quick wins y próximos pasos realistas.\n"
        "No inventes hechos que no estén respaldados por el bundle.\n"
        "Si el archivo fue resumido, aclara explícitamente que trabajas sobre una representación parcial.\n\n"
        "Tareas sugeridas:\n"
        "1. Redactar antecedentes preliminares del proyecto.\n"
        "2. Proponer README inicial.\n"
        "3. Sugerir quick wins ordenados de bajo esfuerzo a mayor complejidad.\n"
        "4. Señalar posibles refactors graduales.\n\n"
        "Bundle estructurado:\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
    )
