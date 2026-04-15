from __future__ import annotations

import json
import os
import urllib.request
from typing import Dict, List, Optional

from .context_builder import build_file_payload, build_prompt_from_bundle
from .budgeting import compute_budget
from .importance import select_primary_file, select_supporting_files
from .models import Finding, RepoFacts


def build_llm_project_brief(repo_facts: RepoFacts, findings: List[Finding]) -> Dict[str, object]:
    top_findings = [f.to_dict() for f in findings[:8]]
    antecedents_lines = [
        f"Proyecto analizado: {repo_facts.root_path}",
        f"Tipo sugerido: {repo_facts.project_type}",
        f"Resumen técnico: {repo_facts.project_summary or 'No consolidado'}",
        f"Tecnologías detectadas: {', '.join(repo_facts.technologies) if repo_facts.technologies else 'No detectadas'}",
        f"Frameworks detectados: {', '.join(repo_facts.frameworks) if repo_facts.frameworks else 'No detectados'}",
        f"Lenguajes principales: {', '.join(repo_facts.main_languages) if repo_facts.main_languages else 'No detectados'}",
        f"Entrypoints notables: {', '.join(repo_facts.notable_entrypoints) if repo_facts.notable_entrypoints else 'No detectados'}",
        f"README status: {repo_facts.readme_status}",
        f"CI detectado: {', '.join(repo_facts.ci_systems) if repo_facts.ci_systems else 'No'}",
        f"Tests detectados: {'sí' if repo_facts.has_tests else 'no'}",
        f"Plantilla de env: {'sí' if repo_facts.has_env_example else 'no'}",
        f"Rutas decoradas aproximadas: {repo_facts.route_count}",
        f"Notas de escaneo: {' | '.join(repo_facts.scan_notes) if repo_facts.scan_notes else 'Sin notas adicionales'}",
    ]

    prompt = (
        "Usa estos antecedentes del repositorio para redactar una versión preliminar del proyecto. "
        "Describe objetivo probable, stack, estructura, riesgos técnicos, quick wins y próximos pasos. "
        "No inventes información que no esté respaldada por el diagnóstico.\n\n"
        + "\n".join(f"- {line}" for line in antecedents_lines)
        + "\n\nHallazgos priorizados:\n"
        + "\n".join(f"- {f.title}: {f.description}" for f in findings[:8])
    )

    return {
        "repo": {
            "root_path": repo_facts.root_path,
            "project_type": repo_facts.project_type,
            "project_summary": repo_facts.project_summary,
            "technologies": repo_facts.technologies,
            "frameworks": repo_facts.frameworks,
            "package_managers": repo_facts.package_managers,
            "ci_systems": repo_facts.ci_systems,
            "has_readme": repo_facts.has_readme,
            "readme_status": repo_facts.readme_status,
            "has_tests": repo_facts.has_tests,
            "has_gitignore": repo_facts.has_gitignore,
            "has_env_example": repo_facts.has_env_example,
            "main_languages": repo_facts.main_languages,
            "notable_entrypoints": repo_facts.notable_entrypoints,
            "route_count": repo_facts.route_count,
            "scan_notes": repo_facts.scan_notes,
        },
        "top_findings": top_findings,
        "preliminary_antecedents": antecedents_lines,
        "llm_prompt": prompt,
    }


def build_llm_context_bundle(
    repo_facts: RepoFacts,
    findings: List[Finding],
    files: List,
    root,
    max_input_tokens: int = 24000,
    primary_budget_ratio: float = 0.35,
    secondary_budget_ratio: float = 0.10,
    max_secondary_files: int = 2,
) -> Dict[str, object]:
    project_brief = build_llm_project_brief(repo_facts, findings)
    primary_budget = compute_budget(max_input_tokens=max_input_tokens, ratio=primary_budget_ratio)
    secondary_budget = compute_budget(max_input_tokens=max_input_tokens, ratio=secondary_budget_ratio)

    primary_candidate = select_primary_file(root, files)
    primary_file = None
    if primary_candidate:
        primary_file = build_file_payload(
            relative_path=primary_candidate["path"],
            content=primary_candidate["content"],
            budget_tokens=primary_budget,
        )
        primary_file["importance_score"] = primary_candidate["score"]
        primary_file["line_count"] = primary_candidate["line_count"]
        primary_file["char_count"] = primary_candidate["char_count"]

    secondary_files = []
    secondary_candidates = select_supporting_files(
        root,
        files,
        primary_relative_path=primary_candidate["path"] if primary_candidate else None,
        max_files=max_secondary_files,
    )
    for candidate in secondary_candidates:
        payload = build_file_payload(
            relative_path=candidate["path"],
            content=candidate["content"],
            budget_tokens=secondary_budget,
        )
        payload["importance_score"] = candidate["score"]
        payload["line_count"] = candidate["line_count"]
        payload["char_count"] = candidate["char_count"]
        secondary_files.append(payload)

    bundle = {
        "repo": project_brief["repo"],
        "top_findings": project_brief["top_findings"],
        "preliminary_antecedents": project_brief["preliminary_antecedents"],
        "budget": {
            "max_input_tokens": max_input_tokens,
            "primary_budget_tokens": primary_budget,
            "secondary_budget_tokens": secondary_budget,
            "max_secondary_files": max_secondary_files,
        },
        "primary_file": primary_file,
        "secondary_files": secondary_files,
    }
    bundle["llm_context_prompt"] = build_prompt_from_bundle(project_brief, bundle)
    return bundle


def maybe_generate_llm_summary(repo_facts: RepoFacts, findings: List[Finding], context_bundle: Dict[str, object] | None = None) -> Optional[str]:
    endpoint = os.getenv("REPO_AGENT_LLM_ENDPOINT")
    model = os.getenv("REPO_AGENT_LLM_MODEL")
    if not endpoint or not model:
        return None

    brief = context_bundle or build_llm_project_brief(repo_facts, findings)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un arquitecto de software. Resume el diagnóstico del repo en español técnico, "
                    "priorizando quick wins y luego mejoras estructurales. Sé concreto y no inventes hechos."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(brief, ensure_ascii=False),
            },
        ],
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # pragma: no cover
        return f"[LLM no disponible] No se pudo generar resumen: {exc}"
