from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .models import Finding, RepoFacts
from .scanner import read_text_file


TEST_DIR_HINTS = {"tests", "test", "spec", "specs", "__tests__"}
README_NAMES = {"readme.md", "readme.txt", "readme", "readme.generated.md"}


class RepoAnalyzer:
    def __init__(self, root: Path, all_files: List[Path], facts: RepoFacts) -> None:
        self.root = root
        self.all_files = all_files
        self.facts = facts

    def analyze(self) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._readme_findings())
        findings.extend(self._project_shape_findings())
        findings.extend(self._test_findings())
        findings.extend(self._ci_findings())
        findings.extend(self._structure_findings())
        findings.extend(self._config_findings())
        findings.extend(self._large_files_findings())
        findings.extend(self._entrypoint_findings())
        findings.extend(self._artifact_findings())
        findings.extend(self._documentation_findings())

        deduped: List[Finding] = []
        seen_ids = set()
        for finding in findings:
            if finding.id not in seen_ids:
                finding.compute_score()
                deduped.append(finding)
                seen_ids.add(finding.id)
        deduped.sort(key=lambda f: f.priority_score, reverse=True)
        return deduped

    def _readme_path(self) -> Path | None:
        for file_path in self.all_files:
            if file_path.name.lower() in README_NAMES:
                return file_path
        return None

    def _readme_findings(self) -> List[Finding]:
        results: List[Finding] = []
        readme_path = self._readme_path()
        if self.facts.readme_status == "missing":
            results.append(Finding(
                id="docs-missing-readme",
                title="Falta README principal",
                category="documentation",
                description="El repositorio no tiene README principal, lo que dificulta onboarding, uso y despliegue.",
                urgency=5,
                impact=5,
                ease=5,
                risk=1,
                confidence=5,
                estimated_hours=1.0,
                patchable=True,
                suggested_action="Crear un README con instalación, ejecución, variables de entorno, estructura y comandos frecuentes.",
                validation_steps=["Verificar que los comandos del README funcionen en un entorno limpio."],
            ))
            return results

        if self.facts.readme_status == "generated_only":
            results.append(Finding(
                id="docs-generated-readme-only",
                title="Sólo existe README generado, no README principal estándar",
                category="documentation",
                description="Se detectó README.generated.md, pero no un README.md canónico en la raíz.",
                affected_files=[self.facts.readme_path] if self.facts.readme_path else [],
                urgency=4,
                impact=4,
                ease=5,
                risk=1,
                confidence=5,
                estimated_hours=0.5,
                patchable=True,
                suggested_action="Promover el README generado a README.md o consolidarlo en una versión principal mantenible.",
                validation_steps=["Revisar que la nueva versión describa correctamente la estructura y ejecución real."],
            ))

        if not readme_path:
            return results

        content = read_text_file(readme_path)
        lowered = content.lower()
        missing_sections = []
        for section in ["instal", "uso", "config", "test", "docker", "arquitect", "estructura"]:
            if section not in lowered:
                missing_sections.append(section)

        if len(content.strip()) < 500:
            results.append(Finding(
                id="docs-thin-readme",
                title="README muy básico",
                category="documentation",
                description="Existe README, pero es demasiado corto para explicar el proyecto con claridad.",
                evidence=[f"README detectado con {len(content.strip())} caracteres."],
                affected_files=[str(readme_path.relative_to(self.root))],
                urgency=4,
                impact=4,
                ease=5,
                risk=1,
                confidence=5,
                estimated_hours=1.0,
                patchable=True,
                suggested_action="Ampliar el README con instalación, uso, variables de entorno, estructura y troubleshooting.",
                validation_steps=["Revisar que los ejemplos de uso sean reales y ejecutables."],
            ))

        if missing_sections:
            results.append(Finding(
                id="docs-readme-missing-sections",
                title="README incompleto",
                category="documentation",
                description="El README existe, pero le faltan secciones operativas importantes.",
                evidence=[f"Secciones probablemente ausentes: {', '.join(missing_sections[:6])}"],
                affected_files=[str(readme_path.relative_to(self.root))],
                urgency=4,
                impact=4,
                ease=4,
                risk=1,
                confidence=4,
                estimated_hours=1.5,
                patchable=True,
                suggested_action="Agregar secciones de instalación, configuración, comandos, pruebas y arquitectura.",
                validation_steps=["Comparar README contra la estructura real del repo."],
            ))
        return results

    def _project_shape_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        if self.facts.project_type == "server_rendered_web_app" and not self.facts.frameworks:
            findings.append(Finding(
                id="shape-server-rendered-without-framework-clear",
                title="Proyecto web renderizado detectado, framework no confirmado",
                category="architecture",
                description="La estructura sugiere una app web renderizada en servidor, pero no hay suficientes señales para confirmar el framework exacto.",
                evidence=["Se detectaron carpetas templates/static y/o entrypoints Python."],
                urgency=2,
                impact=3,
                ease=2,
                risk=1,
                confidence=3,
                estimated_hours=1.0,
                patchable=False,
                suggested_action="Documentar el stack real en README y, si aplica, formalizar dependencias en requirements.txt o pyproject.toml.",
                validation_steps=["Confirmar imports y dependencias reales del proyecto."],
            ))

        if self.facts.has_templates_dir and self.facts.has_static_dir and self.facts.route_count == 0:
            findings.append(Finding(
                id="shape-web-ui-no-routes-detected",
                title="Estructura web presente, pero sin rutas detectadas en entrypoint principal",
                category="architecture",
                description="Hay templates y assets estáticos, pero no se detectaron decoradores de ruta en los entrypoints inspeccionados.",
                evidence=["Esto puede indicar rutas en otro módulo o un análisis aún superficial."],
                urgency=2,
                impact=3,
                ease=2,
                risk=1,
                confidence=3,
                estimated_hours=1.0,
                patchable=False,
                suggested_action="Extender la detección a blueprints, módulos secundarios o archivos de router dedicados.",
                validation_steps=["Buscar @app.route, Blueprint o registradores de rutas fuera de app.py."],
            ))
        return findings

    def _test_findings(self) -> List[Finding]:
        results: List[Finding] = []
        test_files = [p for p in self.all_files if self._looks_like_test(p)]
        if not test_files:
            results.append(Finding(
                id="quality-no-tests",
                title="No se detectaron tests",
                category="testing",
                description="No se encontraron directorios o archivos de test claros.",
                urgency=5,
                impact=5,
                ease=3,
                risk=2,
                confidence=4,
                estimated_hours=4.0,
                patchable=False,
                suggested_action="Agregar tests smoke o unitarios mínimos para los flujos críticos.",
                validation_steps=["Definir un comando estable de tests en CI."],
            ))
        elif len(test_files) < max(2, int(self.facts.total_files * 0.05)):
            results.append(Finding(
                id="quality-low-test-footprint",
                title="Cobertura de tests probablemente baja",
                category="testing",
                description="Se detectaron pocos tests respecto del tamaño general del repositorio.",
                evidence=[f"Tests detectados: {len(test_files)}", f"Archivos totales: {self.facts.total_files}"],
                affected_files=[str(p.relative_to(self.root)) for p in test_files[:10]],
                urgency=4,
                impact=4,
                ease=3,
                risk=2,
                confidence=3,
                estimated_hours=6.0,
                patchable=False,
                suggested_action="Aumentar tests en módulos críticos antes de refactors mayores.",
                validation_steps=["Agregar cobertura gradual por componentes críticos."],
            ))
        return results

    def _ci_findings(self) -> List[Finding]:
        if self.facts.ci_systems:
            return []
        return [Finding(
            id="ops-no-ci",
            title="No se detectó CI",
            category="quality",
            description="El repositorio no muestra integración continua visible.",
            urgency=5,
            impact=5,
            ease=4,
            risk=1,
            confidence=4,
            estimated_hours=2.0,
            patchable=True,
            suggested_action="Agregar pipeline mínimo para lint y tests en cada push o pull request.",
            validation_steps=["Ejecutar localmente los comandos que correrá CI."],
        )]

    def _structure_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        root_files = [p for p in self.all_files if p.parent == self.root]
        if len(root_files) > 18:
            findings.append(Finding(
                id="structure-crowded-root",
                title="Raíz del repositorio muy cargada",
                category="architecture",
                description="Hay demasiados archivos en la raíz, lo que suele dificultar mantenimiento y navegación.",
                evidence=[f"Archivos en raíz: {len(root_files)}"],
                affected_files=[str(p.relative_to(self.root)) for p in root_files[:12]],
                urgency=3,
                impact=4,
                ease=3,
                risk=2,
                confidence=4,
                estimated_hours=3.0,
                patchable=False,
                suggested_action="Agrupar scripts, docs y utilidades en carpetas con propósito claro.",
                validation_steps=["Verificar imports relativos y rutas al mover archivos."],
            ))
        return findings

    def _config_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        if not self.facts.has_gitignore:
            findings.append(Finding(
                id="repo-no-gitignore",
                title="Falta .gitignore",
                category="quality",
                description="No se detectó .gitignore en la raíz del repositorio.",
                urgency=4,
                impact=4,
                ease=5,
                risk=1,
                confidence=5,
                estimated_hours=0.5,
                patchable=True,
                suggested_action="Agregar .gitignore alineado con el stack detectado.",
                validation_steps=["Confirmar que no queden binarios, caches o secretos sin ignorar."],
            ))

        if not self.facts.has_env_example:
            findings.append(Finding(
                id="config-no-env-example",
                title="No hay plantilla de variables de entorno",
                category="documentation",
                description="No se encontró .env.example ni archivo similar para documentar configuración.",
                urgency=4,
                impact=4,
                ease=4,
                risk=1,
                confidence=4,
                estimated_hours=1.0,
                patchable=True,
                suggested_action="Crear .env.example con claves mínimas y valores ficticios seguros.",
                validation_steps=["Revisar que no se filtren secretos reales."],
            ))

        suspicious_hits = self._scan_for_secrets_like_patterns(limit=6)
        if suspicious_hits:
            findings.append(Finding(
                id="security-hardcoded-secrets-suspected",
                title="Posibles secretos o credenciales hardcodeadas",
                category="security",
                description="Se detectaron patrones que conviene revisar manualmente porque podrían ser configuración sensible hardcodeada.",
                evidence=suspicious_hits,
                urgency=4,
                impact=5,
                ease=2,
                risk=4,
                confidence=2,
                estimated_hours=1.0,
                patchable=False,
                suggested_action="Mover secretos a variables de entorno o gestor de secretos y dejar sólo placeholders seguros.",
                validation_steps=["Verificar manualmente cada coincidencia antes de actuar."],
            ))
        return findings

    def _large_files_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        likely_source_files = [p for p in self.all_files if p.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".html"}]
        giant_files = []
        for path in likely_source_files:
            text = read_text_file(path, max_bytes=500_000)
            if text and text.count("\n") > 500:
                giant_files.append((path, text.count("\n") + 1))

        if giant_files:
            path, lines = sorted(giant_files, key=lambda x: x[1], reverse=True)[0]
            findings.append(Finding(
                id="structure-large-module",
                title="Archivo grande candidato a división",
                category="architecture",
                description="Se detectó al menos un archivo fuente muy grande, con alto riesgo de mezcla de responsabilidades.",
                evidence=[f"{path.relative_to(self.root)} tiene aproximadamente {lines} líneas."],
                affected_files=[str(path.relative_to(self.root))],
                urgency=3,
                impact=4,
                ease=2,
                risk=3,
                confidence=4,
                estimated_hours=5.0,
                patchable=False,
                suggested_action="Separar lógica por capas o dominios antes de seguir agregando funcionalidades.",
                validation_steps=["Agregar tests previos al refactor del archivo grande."],
            ))
        return findings

    def _entrypoint_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        app_py = self.root / "app.py"
        if not app_py.exists():
            return findings

        text = read_text_file(app_py, max_bytes=500_000)
        line_count = text.count("\n") + 1 if text else 0
        route_count = text.count("@app.route") + text.count("@bp.route")
        render_calls = text.count("render_template(")

        if line_count > 400:
            findings.append(Finding(
                id="entrypoint-app-py-large",
                title="app.py concentra mucha lógica",
                category="architecture",
                description="El punto de entrada principal es grande y probablemente mezcla rutas, render, configuración y lógica de negocio.",
                evidence=[f"app.py tiene aproximadamente {line_count} líneas."],
                affected_files=["app.py"],
                urgency=3,
                impact=4,
                ease=2,
                risk=3,
                confidence=4,
                estimated_hours=5.0,
                patchable=False,
                suggested_action="Separar rutas, servicios y utilidades en módulos dedicados o blueprints.",
                validation_steps=["Agregar tests o smoke checks antes de dividir el archivo."],
            ))

        if route_count >= 8:
            findings.append(Finding(
                id="entrypoint-many-routes-one-file",
                title="Múltiples rutas centralizadas en un solo archivo",
                category="architecture",
                description="Se detectaron varias rutas en app.py, lo que suele anticipar acoplamiento y escalabilidad limitada.",
                evidence=[f"Rutas detectadas aproximadamente: {route_count}", f"Render templates detectados: {render_calls}"],
                affected_files=["app.py"],
                urgency=3,
                impact=4,
                ease=2,
                risk=3,
                confidence=4,
                estimated_hours=4.0,
                patchable=False,
                suggested_action="Extraer blueprints o módulos por dominio funcional antes de sumar nuevas vistas o endpoints.",
                validation_steps=["Verificar registro correcto de rutas tras modularizar."],
            ))

        if "debug=True" in text.replace(" ", ""):
            findings.append(Finding(
                id="entrypoint-debug-true",
                title="Modo debug explícito en código",
                category="security",
                description="Se detectó debug=True directamente en el código del entrypoint.",
                affected_files=["app.py"],
                urgency=4,
                impact=4,
                ease=4,
                risk=3,
                confidence=5,
                estimated_hours=0.5,
                patchable=True,
                suggested_action="Mover el modo debug a variable de entorno o configuración por entorno.",
                validation_steps=["Confirmar que el arranque siga funcionando en local y producción."],
            ))

        return findings

    def _artifact_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        zip_files = [p for p in self.root.iterdir() if p.is_file() and p.suffix.lower() == ".zip"] if self.root.exists() else []
        if zip_files:
            findings.append(Finding(
                id="repo-zip-artifacts-in-root",
                title="Hay artefactos comprimidos dentro del repositorio",
                category="quality",
                description="Se detectaron archivos .zip en la raíz; suelen ser artefactos de entrega o backup y agregan ruido al análisis y al control de versiones.",
                evidence=[f"Archivos detectados: {', '.join(p.name for p in zip_files[:5])}"],
                affected_files=[p.name for p in zip_files[:5]],
                urgency=2,
                impact=3,
                ease=4,
                risk=1,
                confidence=5,
                estimated_hours=0.5,
                patchable=False,
                suggested_action="Mover backups/entregables fuera del repo o ignorarlos explícitamente si deben coexistir temporalmente.",
                validation_steps=["Verificar que esos archivos no sean parte deliberada de la distribución del proyecto."],
            ))
        return findings

    def _documentation_findings(self) -> List[Finding]:
        findings: List[Finding] = []
        md_files = [p for p in self.all_files if p.suffix.lower() == ".md"]
        if not md_files:
            findings.append(Finding(
                id="docs-no-markdown-docs",
                title="Documentación complementaria ausente",
                category="documentation",
                description="No se detectaron documentos Markdown adicionales además del README principal o equivalente.",
                urgency=2,
                impact=3,
                ease=3,
                risk=1,
                confidence=3,
                estimated_hours=1.0,
                patchable=True,
                suggested_action="Agregar notas de arquitectura, despliegue o troubleshooting según el tipo de proyecto.",
                validation_steps=["Mantener la documentación alineada con el comportamiento real del repo."],
            ))
        return findings

    def _looks_like_test(self, path: Path) -> bool:
        lower_parts = {part.lower() for part in path.parts}
        if lower_parts & TEST_DIR_HINTS:
            return True
        lower_name = path.name.lower()
        return lower_name.startswith("test_") or lower_name.endswith("_test.py") or lower_name.endswith(".spec.ts") or lower_name.endswith(".spec.js")

    def _scan_for_secrets_like_patterns(self, limit: int = 6) -> List[str]:
        patterns = [
            re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
            re.compile(r"AKIA[0-9A-Z]{16}"),
        ]
        matches: List[str] = []
        candidate_files = [p for p in self.all_files if p.suffix.lower() in {".py", ".js", ".ts", ".env", ".json", ".yaml", ".yml", ".ini", ".cfg"}]
        for path in candidate_files:
            text = read_text_file(path, max_bytes=80_000)
            if not text:
                continue
            for pattern in patterns:
                for hit in pattern.finditer(text):
                    snippet = hit.group(0)
                    matches.append(f"{path.relative_to(self.root)} → {snippet[:120]}")
                    if len(matches) >= limit:
                        return matches
        return matches
