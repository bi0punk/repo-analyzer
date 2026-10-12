from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .budgeting import compute_budget
from .context_builder import build_file_payload, build_prompt_from_bundle
from .importance import select_primary_file, select_supporting_files
from .models import Finding, RepoFacts


def build_llm_project_brief(repo_facts: RepoFacts, findings: list[Finding]) -> dict[str, Any]:
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


def _file_payload(candidate: dict[str, Any], budget_tokens: int) -> dict[str, Any]:
    payload = build_file_payload(
        relative_path=candidate["path"],
        content=candidate["content"],
        budget_tokens=budget_tokens,
    )
    payload["importance_score"] = candidate["score"]
    payload["line_count"] = candidate["line_count"]
    payload["char_count"] = candidate["char_count"]
    return payload


def build_llm_context_bundle(
    repo_facts: RepoFacts,
    findings: list[Finding],
    files: list[Path],
    root: Path,
    max_input_tokens: int = 24000,
    primary_budget_ratio: float = 0.35,
    secondary_budget_ratio: float = 0.10,
    max_secondary_files: int = 2,
) -> dict[str, Any]:
    project_brief = build_llm_project_brief(repo_facts, findings)
    primary_budget = compute_budget(max_input_tokens=max_input_tokens, ratio=primary_budget_ratio)
    secondary_budget = compute_budget(max_input_tokens=max_input_tokens, ratio=secondary_budget_ratio)

    primary_candidate = select_primary_file(root, files)
    primary_file = _file_payload(primary_candidate, primary_budget) if primary_candidate else None

    secondary_files = []
    secondary_candidates = select_supporting_files(
        root,
        files,
        primary_relative_path=primary_candidate["path"] if primary_candidate else None,
        max_files=max_secondary_files,
    )
    for candidate in secondary_candidates:
        secondary_files.append(_file_payload(candidate, secondary_budget))

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


ALLOWED_LLM_SCHEMES = {"http", "https"}


class LLMError(RuntimeError):
    """Error de configuración o comunicación con el endpoint LLM."""


def get_base_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in ALLOWED_LLM_SCHEMES or not parsed.hostname:
        raise LLMError(f"Endpoint LLM no permitido: {endpoint!r} (solo http/https)")
    return endpoint.rstrip("/")


def validate_chat_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_LLM_SCHEMES or not parsed.hostname:
        raise LLMError(f"URL de chat LLM no permitida: {url!r} (solo http/https)")
    return url


def chat_completion(
    url: str,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str = "",
    temperature: float = 0.2,
    max_tokens: int | None = None,
    timeout: float = 60.0,
) -> str:
    """Llama a un endpoint OpenAI-compatible (chat/completions) y devuelve el contenido."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        validate_chat_url(url),
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def maybe_generate_llm_summary(
    repo_facts: RepoFacts, findings: list[Finding], context_bundle: dict[str, Any] | None = None
) -> str | None:
    endpoint = os.getenv("REPO_AGENT_LLM_ENDPOINT")
    model = os.getenv("REPO_AGENT_LLM_MODEL")
    if not endpoint or not model:
        return None

    brief = context_bundle or build_llm_project_brief(repo_facts, findings)
    messages = [
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
    ]

    try:
        return chat_completion(
            url=f"{get_base_endpoint(endpoint)}/v1/chat/completions",
            model=model,
            messages=messages,
            api_key=os.getenv("REPO_AGENT_LLM_API_KEY", ""),
            temperature=0.2,
            timeout=60.0,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] No se pudo generar resumen LLM: {exc}", file=sys.stderr)
        return None
