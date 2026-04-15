from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .context_builder import build_selected_files_markdown
from .models import AgentState, Finding
from .prioritizer import assign_bucket


def findings_to_markdown(findings: List[Finding]) -> str:
    if not findings:
        return "No se detectaron hallazgos por heurísticas simples."

    lines = []
    for idx, finding in enumerate(findings, start=1):
        bucket = assign_bucket(finding.priority_score)
        lines.append(f"{idx}. **{finding.title}** — {bucket} | score={finding.priority_score}")
        lines.append(f"   - Categoría: {finding.category}")
        lines.append(f"   - Descripción: {finding.description}")
        if finding.evidence:
            lines.append(f"   - Evidencia: {' | '.join(finding.evidence[:4])}")
        if finding.affected_files:
            lines.append(f"   - Archivos: {', '.join(finding.affected_files[:6])}")
        lines.append(f"   - Acción sugerida: {finding.suggested_action}")
        lines.append(f"   - Patchable: {'sí' if finding.patchable else 'no'}")
        lines.append("")
    return "\n".join(lines).strip()



def brief_to_markdown(brief: Dict[str, object] | None) -> str:
    if not brief:
        return "No se generó contexto preliminar para LLM."

    lines = ["## Antecedentes preliminares para LLM", ""]
    for item in brief.get("preliminary_antecedents", []):
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## Prompt sugerido para LLM",
        "```text",
        str(brief.get("llm_prompt", "")).strip(),
        "```",
    ])
    return "\n".join(lines)



def important_context_to_markdown(context_bundle: Dict[str, object] | None) -> str:
    if not context_bundle:
        return "## Contexto adicional para LLM\n\nNo se seleccionaron archivos principales."

    lines = ["## Contexto adicional para LLM", ""]
    budget = context_bundle.get("budget", {})
    if budget:
        lines.append(f"- Presupuesto máximo de entrada: {budget.get('max_input_tokens', 'n/d')} tokens")
        lines.append(f"- Presupuesto archivo principal: {budget.get('primary_budget_tokens', 'n/d')} tokens")
        lines.append(f"- Presupuesto por archivo satélite: {budget.get('secondary_budget_tokens', 'n/d')} tokens")
        lines.append(f"- Máximo archivos satélite: {budget.get('max_secondary_files', 'n/d')}")
        lines.append("")

    primary = context_bundle.get("primary_file")
    if primary:
        lines.append("### Archivo principal seleccionado")
        lines.append(f"- Ruta: `{primary.get('path')}`")
        lines.append(f"- Modo: {primary.get('included_mode')}")
        lines.append(f"- Tokens estimados: {primary.get('estimated_tokens')}")
        lines.append(f"- Líneas aproximadas: {primary.get('line_count')}")
        lines.append(f"- Score de importancia: {primary.get('importance_score')}")
        lines.append("")

    secondary = context_bundle.get("secondary_files", [])
    if secondary:
        lines.append("### Archivos satélite seleccionados")
        for item in secondary:
            lines.append(
                f"- `{item.get('path')}` | modo={item.get('included_mode')} | tokens={item.get('estimated_tokens')} | score={item.get('importance_score')}"
            )
        lines.append("")

    lines.extend([
        "### Prompt ampliado para LLM",
        "```text",
        str(context_bundle.get("llm_context_prompt", "")).strip(),
        "```",
    ])
    return "\n".join(lines)



def build_markdown_report(state: AgentState) -> str:
    facts = state.repo_facts
    if not facts:
        return "# Reporte\n\nNo hay datos del repositorio."

    lines = [
        "# Repo Agent MVP v3 - Diagnóstico",
        "",
        f"**Ruta analizada:** `{facts.root_path}`",
        f"**Archivos analizados:** {facts.total_files}",
        f"**Directorios:** {facts.total_dirs}",
        f"**Archivos en raíz:** {facts.root_files_count}",
        f"**Ruido/artefactos excluidos del escaneo:** {facts.noise_files_excluded}",
        f"**Tipo de proyecto sugerido:** {facts.project_type}",
        f"**Resumen técnico:** {facts.project_summary or 'No consolidado'}",
        f"**Tecnologías detectadas:** {', '.join(facts.technologies) if facts.technologies else 'No detectadas'}",
        f"**Frameworks detectados:** {', '.join(facts.frameworks) if facts.frameworks else 'No detectados'}",
        f"**Lenguajes principales:** {', '.join(facts.main_languages) if facts.main_languages else 'No detectados'}",
        f"**CI detectado:** {', '.join(facts.ci_systems) if facts.ci_systems else 'No'}",
        f"**README status:** {facts.readme_status}",
        f"**README path:** {facts.readme_path or 'No detectado'}",
        f"**Tests:** {'sí' if facts.has_tests else 'no'}",
        f"**.gitignore:** {'sí' if facts.has_gitignore else 'no'}",
        f"**.env.example:** {'sí' if facts.has_env_example else 'no'}",
        f"**Docker:** {'sí' if facts.has_docker else 'no'}",
        f"**templates/:** {'sí' if facts.has_templates_dir else 'no'}",
        f"**static/:** {'sí' if facts.has_static_dir else 'no'}",
        f"**Rutas decoradas detectadas:** {facts.route_count}",
        f"**Entrypoints notables:** {', '.join(facts.notable_entrypoints) if facts.notable_entrypoints else 'No detectados'}",
        "",
        "## Vista rápida de estructura",
        "```",
        facts.directory_tree_preview,
        "```",
        "",
        "## Extensiones más frecuentes",
    ]

    for ext, count in list(facts.file_extension_counts.items())[:12]:
        lines.append(f"- `{ext}`: {count}")

    lines.extend([
        "",
        "## Archivos más grandes considerados",
    ])
    for item in facts.largest_files[:8]:
        lines.append(f"- `{item['path']}` — {item['size_kb']} KB")

    if facts.scan_notes:
        lines.extend([
            "",
            "## Notas de detección",
        ])
        for note in facts.scan_notes:
            lines.append(f"- {note}")

    if state.llm_summary:
        lines.extend([
            "",
            "## Resumen LLM opcional",
            state.llm_summary,
        ])

    lines.extend([
        "",
        "## Hallazgos priorizados",
        findings_to_markdown(state.findings),
        "",
        brief_to_markdown(state.llm_project_brief),
        "",
        important_context_to_markdown(state.llm_context_bundle),
        "",
        "## Siguientes pasos recomendados",
        "1. Atacar primero los hallazgos patchable de tipo P0/P1.",
        "2. Luego asegurar tests y CI antes de refactors grandes.",
        "3. Usar `llm_context_bundle.json` o `llm_context_prompt.txt` para pedir al LLM README, overview técnico, quick wins o plan de refactor.",
    ])
    return "\n".join(lines)



def write_outputs(state: AgentState, output_dir: Path, write_json: bool = True) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "repo_diagnostic.md"
    md_path.write_text(state.final_report_markdown, encoding="utf-8")

    if write_json:
        json_path = output_dir / "repo_diagnostic.json"
        json_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    if state.llm_project_brief:
        brief_json = output_dir / "llm_project_brief.json"
        brief_json.write_text(json.dumps(state.llm_project_brief, ensure_ascii=False, indent=2), encoding="utf-8")

        prompt_txt = output_dir / "llm_prompt.txt"
        prompt_txt.write_text(str(state.llm_project_brief.get("llm_prompt", "")), encoding="utf-8")

        antecedents_md = output_dir / "llm_antecedents.md"
        antecedents_md.write_text(brief_to_markdown(state.llm_project_brief), encoding="utf-8")

    if state.llm_context_bundle:
        bundle_json = output_dir / "llm_context_bundle.json"
        bundle_json.write_text(json.dumps(state.llm_context_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

        context_prompt = output_dir / "llm_context_prompt.txt"
        context_prompt.write_text(str(state.llm_context_bundle.get("llm_context_prompt", "")), encoding="utf-8")

        selected_files_md = output_dir / "important_file_summary.md"
        selected_files_md.write_text(build_selected_files_markdown(state.llm_context_bundle), encoding="utf-8")
