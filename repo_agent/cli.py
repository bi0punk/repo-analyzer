from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzers import RepoAnalyzer
from .detectors import detect_languages_from_extensions, detect_stack
from .llm import build_llm_context_bundle, build_llm_project_brief, maybe_generate_llm_summary
from .models import AgentState, RepoFacts, ToolResult
from .reporter import build_markdown_report, write_outputs
from .scanner import (
    build_tree_preview,
    count_dirs,
    count_excluded_files,
    extension_counts,
    iter_repo_files,
    largest_files,
)


def build_repo_facts(root: Path) -> tuple[RepoFacts, list[Path]]:
    all_files = list(iter_repo_files(root))
    ext_counts = extension_counts(all_files)
    stack = detect_stack(root, all_files)
    root_files_count = sum(1 for p in all_files if p.parent == root)

    facts = RepoFacts(
        root_path=str(root.resolve()),
        total_files=len(all_files),
        total_dirs=count_dirs(root),
        root_files_count=root_files_count,
        technologies=stack["technologies"],
        frameworks=stack["frameworks"],
        package_managers=stack["package_managers"],
        ci_systems=stack["ci_systems"],
        project_type=str(stack["project_type"]),
        project_summary=str(stack["project_summary"]),
        has_readme=stack["readme_status"] in {"standard", "generated_only"},
        readme_status=str(stack["readme_status"]),
        readme_path=stack["readme_path"],
        has_tests=any(any(part.lower() in {"tests", "test", "spec", "specs", "__tests__"} for part in p.parts) for p in all_files),
        has_gitignore=(root / ".gitignore").exists(),
        has_docker=(root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists(),
        has_env_example=(root / ".env.example").exists() or (root / "env.example").exists() or (root / ".env.sample").exists(),
        has_templates_dir=bool(stack["has_templates_dir"]),
        has_static_dir=bool(stack["has_static_dir"]),
        route_count=int(stack["route_count"]),
        main_languages=detect_languages_from_extensions(ext_counts),
        file_extension_counts=ext_counts,
        largest_files=largest_files(all_files, root, limit=10),
        directory_tree_preview=build_tree_preview(root, max_depth=3, max_entries_per_dir=12),
        notable_entrypoints=list(stack["notable_entrypoints"]),
        noise_files_excluded=count_excluded_files(root),
        scan_notes=list(stack["scan_notes"]),
    )
    return facts, all_files



def main() -> int:
    parser = argparse.ArgumentParser(description="Repo Agent MVP v3 - diagnóstico heurístico con bundle contextual para LLM")
    parser.add_argument("repo_path", help="Ruta del repositorio a analizar")
    parser.add_argument("--output-dir", default="./repo_agent_output", help="Directorio donde dejar los reportes")
    parser.add_argument("--no-json", action="store_true", help="No generar salida JSON")
    parser.add_argument("--print-report", action="store_true", help="Imprimir el reporte Markdown en consola")
    parser.add_argument("--llm-max-input-tokens", type=int, default=24000, help="Presupuesto máximo total estimado para el contexto del LLM")
    parser.add_argument("--important-file-budget-ratio", type=float, default=0.35, help="Fracción del presupuesto total reservada para el archivo principal")
    parser.add_argument("--secondary-file-budget-ratio", type=float, default=0.10, help="Fracción del presupuesto total reservada por archivo satélite")
    parser.add_argument("--max-secondary-files", type=int, default=2, help="Máximo de archivos satélite para el bundle de contexto")
    args = parser.parse_args()

    root = Path(args.repo_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Ruta inválida: {root}", file=sys.stderr)
        return 1

    state = AgentState()

    facts, all_files = build_repo_facts(root)
    state.repo_facts = facts
    state.tool_results.append(ToolResult(
        tool_name="fingerprint",
        success=True,
        summary="Fingerprint del repositorio generado correctamente.",
        details={
            "total_files": facts.total_files,
            "technologies": facts.technologies,
            "frameworks": facts.frameworks,
            "ci_systems": facts.ci_systems,
            "project_type": facts.project_type,
            "excluded_noise": facts.noise_files_excluded,
        },
    ))

    analyzer = RepoAnalyzer(root=root, all_files=all_files, facts=facts)
    findings = analyzer.analyze()
    state.findings = findings
    state.tool_results.append(ToolResult(
        tool_name="heuristic_diagnosis",
        success=True,
        summary=f"Se generaron {len(findings)} hallazgos por heurísticas.",
        details={"findings_count": len(findings)},
    ))

    state.llm_project_brief = build_llm_project_brief(facts, findings)
    state.llm_context_bundle = build_llm_context_bundle(
        repo_facts=facts,
        findings=findings,
        files=all_files,
        root=root,
        max_input_tokens=args.llm_max_input_tokens,
        primary_budget_ratio=args.important_file_budget_ratio,
        secondary_budget_ratio=args.secondary_file_budget_ratio,
        max_secondary_files=args.max_secondary_files,
    )
    state.tool_results.append(ToolResult(
        tool_name="llm_context_bundle",
        success=True,
        summary="Bundle contextual para LLM generado correctamente.",
        details={
            "max_input_tokens": args.llm_max_input_tokens,
            "primary_file": (state.llm_context_bundle or {}).get("primary_file", {}).get("path"),
            "secondary_files": [f.get("path") for f in (state.llm_context_bundle or {}).get("secondary_files", [])],
        },
    ))

    state.llm_summary = maybe_generate_llm_summary(facts, findings, state.llm_context_bundle)
    state.final_report_markdown = build_markdown_report(state)

    output_dir = Path(args.output_dir).expanduser().resolve()
    write_outputs(state, output_dir, write_json=not args.no_json)

    primary_path = None
    primary_mode = None
    if state.llm_context_bundle and state.llm_context_bundle.get("primary_file"):
        primary_path = state.llm_context_bundle["primary_file"].get("path")
        primary_mode = state.llm_context_bundle["primary_file"].get("included_mode")

    print(f"[OK] Reporte generado en: {output_dir}")
    print(f"[INFO] Archivos analizados: {facts.total_files}")
    print(f"[INFO] Ruido excluido: {facts.noise_files_excluded}")
    print(f"[INFO] Tipo sugerido: {facts.project_type}")
    print(f"[INFO] Tecnologías detectadas: {', '.join(facts.technologies) if facts.technologies else 'ninguna clara'}")
    print(f"[INFO] Hallazgos: {len(findings)}")
    if primary_path:
        print(f"[INFO] Archivo principal para LLM: {primary_path} | modo={primary_mode}")
    if state.llm_context_bundle:
        print(f"[INFO] Archivos satélite para LLM: {len(state.llm_context_bundle.get('secondary_files', []))}")

    if findings:
        print("[TOP] Hallazgos principales:")
        for finding in findings[:5]:
            print(f"  - {finding.title} | score={finding.priority_score} | patchable={'sí' if finding.patchable else 'no'}")

    if args.print_report:
        print("\n" + state.final_report_markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
